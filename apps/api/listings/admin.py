from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils import timezone

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
    readonly_fields = ('slug', 'created_at', 'published_at', 'reviewed_by', 'reviewed_at')
    inlines = [PropertyPhotoInline]
    actions = ['publish_listings', 'reject_listings']

    def save_model(self, request, obj, form, change):
        # Changing the status by hand in the form is also a staff review decision.
        if change and 'status' in form.changed_data:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

    @admin.action(description='Publish selected listings')
    def publish_listings(self, request, queryset):
        done = 0
        for prop in queryset.exclude(status=Status.PUBLISHED):
            try:
                prop.publish(request.user)
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
            done += 1
        if done:
            self.message_user(request, f'{done} listing(s) rejected.', messages.SUCCESS)
