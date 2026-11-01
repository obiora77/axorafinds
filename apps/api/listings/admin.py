from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from config.emails import last_email_error, send_listing_published_email, send_listing_rejected_email

from .models import Property, PropertyPhoto, Status


class PropertyPhotoInline(admin.TabularInline):
    model = PropertyPhoto
    extra = 0
    fields = ('image', 'external_url', 'position')


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'city', 'state', 'price', 'status', 'owner', 'created_at')
    list_filter = ('status', 'state', 'property_type')
    search_fields = ('title', 'city', 'owner__email')
    ordering = ('-created_at',)
    raw_id_fields = ('owner',)
    readonly_fields = ('slug', 'status', 'created_at', 'published_at', 'reviewed_by', 'reviewed_at')
    inlines = [PropertyPhotoInline]
    actions = ['publish_listings', 'reject_listings', 'resend_emails']

    @admin.action(description='Publish selected listings')
    def publish_listings(self, request, queryset):
        # Status is read-only in the form so a listing can only go live through
        # Property.publish(), which refuses a listing with no photo.
        done = 0
        for prop in queryset.exclude(status=Status.PUBLISHED):
            try:
                prop.publish(request.user)
                send_listing_published_email(prop)
                done += 1
            except ValidationError as exc:
                self.message_user(request, f'{prop.title}: {"; ".join(exc.messages)}', messages.WARNING)
        if done:
            self.message_user(request, f'{done} listing(s) published.', messages.SUCCESS)

    @admin.action(description='Reject selected listings')
    def reject_listings(self, request, queryset):
        done = 0
        for prop in queryset.exclude(status=Status.REJECTED):
            prop.reject(request.user)
            send_listing_rejected_email(prop)
            done += 1
        if done:
            self.message_user(request, f'{done} listing(s) rejected.', messages.SUCCESS)

    @admin.action(description='Resend the latest decision email')
    def resend_emails(self, request, queryset):
        # The status is untouched; this only retries delivery after a mail outage.
        sent = 0
        for prop in queryset:
            if prop.status == Status.PUBLISHED:
                sender = send_listing_published_email
            elif prop.status == Status.REJECTED:
                sender = send_listing_rejected_email
            else:
                self.message_user(
                    request,
                    f'{prop.title}: no decision email to resend yet.',
                    messages.WARNING,
                )
                continue
            if sender(prop):
                sent += 1
            else:
                self.message_user(
                    request,
                    f'{prop.title}: {last_email_error() or "The email was not sent."}',
                    messages.ERROR,
                )
        if sent:
            self.message_user(request, f'{sent} email(s) sent again.', messages.SUCCESS)
