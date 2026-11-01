from django import forms
from django.contrib import admin, messages
from django.template.response import TemplateResponse
from django.urls import path

from config.emails import (
    email_status,
    last_email_error,
    send_review_published_email,
    send_test_email,
)

from .models import ContactMessage, NewsletterSubscriber, Review, SiteSettings


class EmailTestForm(forms.Form):
    to = forms.EmailField(label='Send to', max_length=254)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Official bank account for inspection fees', {
            'fields': ('bank_name', 'account_name', 'account_number', 'transfer_note', 'is_live'),
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        custom = [
            path(
                'email-test/',
                self.admin_site.admin_view(self.email_test_view),
                name='pages_sitesettings_email_test',
            ),
        ]
        return custom + super().get_urls()

    def email_test_view(self, request):
        """Send a real message through the configured backend and show the exact result."""
        sent = None
        error = None
        if request.method == 'POST':
            form = EmailTestForm(request.POST)
            if form.is_valid():
                to = form.cleaned_data['to']
                try:
                    sent = send_test_email(to, raise_errors=True)
                    if not sent:
                        error = last_email_error() or 'The message was not sent.'
                except Exception as exc:  # noqa: BLE001 - show the SMTP failure instead of a 500
                    sent = False
                    error = f'{type(exc).__name__}: {exc}'
            else:
                sent = False
        else:
            form = EmailTestForm(initial={'to': request.user.email})

        context = {
            **self.admin_site.each_context(request),
            'title': 'Send a test email',
            'form': form,
            'sent': sent,
            'error': error,
            'status': email_status(),
        }
        return TemplateResponse(request, 'admin/email_test.html', context)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')
    search_fields = ('email',)
    readonly_fields = ('created_at',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('name', 'email', 'message', 'created_at')

    def has_add_permission(self, request):
        return False


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating', 'location', 'is_published', 'created_at')
    list_filter = ('is_published', 'rating')
    search_fields = ('name', 'location', 'text')
    readonly_fields = ('user', 'is_published', 'created_at')
    actions = ['publish_reviews', 'unpublish_reviews', 'resend_emails']

    @admin.action(description='Publish selected reviews on the home page')
    def publish_reviews(self, request, queryset):
        done = 0
        for review in queryset.filter(is_published=False):
            review.is_published = True
            review.save(update_fields=['is_published'])
            send_review_published_email(review)
            done += 1
        self.message_user(request, f'{done} review(s) published.', messages.SUCCESS)

    @admin.action(description='Hide selected reviews from the home page')
    def unpublish_reviews(self, request, queryset):
        done = queryset.update(is_published=False)
        self.message_user(request, f'{done} review(s) hidden.', messages.SUCCESS)

    @admin.action(description='Resend the published email to review authors')
    def resend_emails(self, request, queryset):
        # The review stays published; this only retries delivery after a mail outage.
        sent = 0
        for review in queryset.filter(is_published=True).select_related('user'):
            if not review.user_id:
                self.message_user(
                    request,
                    f'{review.name}: no linked account, so there is no address to email.',
                    messages.WARNING,
                )
                continue
            if send_review_published_email(review):
                sent += 1
            else:
                self.message_user(
                    request,
                    f'{review.name}: {last_email_error() or "The email was not sent."}',
                    messages.ERROR,
                )
        if sent:
            self.message_user(request, f'{sent} email(s) sent again.', messages.SUCCESS)
