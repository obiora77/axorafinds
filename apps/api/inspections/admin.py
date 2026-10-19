from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import Inspection


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    """
    Staff queue: 1) Mark payment verified, 2) Confirm or Reject the inspection.
    Status and payment fields are read-only here so they can only change through these actions.
    """

    list_display = (
        'reference', 'property', 'name', 'phone', 'preferred_date',
        'fee_amount', 'payment_choice', 'payment_status', 'status', 'created_at',
    )
    list_filter = ('status', 'payment_status', 'payment_choice', 'preferred_date')
    search_fields = ('reference', 'name', 'email', 'phone', 'property__title')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    actions = ['mark_payment_verified', 'confirm_inspections', 'reject_inspections']
    readonly_fields = (
        'reference', 'property', 'user', 'name', 'phone', 'email', 'preferred_date', 'note',
        'payment_choice', 'fee_amount', 'payment_status', 'status',
        'payment_verified_by', 'payment_verified_at', 'decided_by', 'decided_at', 'created_at',
    )
    fieldsets = (
        ('Request', {'fields': ('reference', 'property', 'user', 'name', 'phone', 'email', 'preferred_date', 'note', 'created_at')}),
        ('Payment', {'fields': ('payment_choice', 'fee_amount', 'payment_status', 'payment_verified_by', 'payment_verified_at')}),
        ('Decision', {'fields': ('status', 'decided_by', 'decided_at', 'staff_note')}),
    )

    def has_add_permission(self, request):
        return False  # requests come from the website

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def _run(self, request, queryset, method, done_message):
        done = 0
        for inspection in queryset:
            try:
                getattr(inspection, method)(request.user)
                done += 1
            except ValidationError as exc:
                self.message_user(request, f'{inspection.reference}: {"; ".join(exc.messages)}', messages.WARNING)
        if done:
            self.message_user(request, f'{done} inspection(s) {done_message}.', messages.SUCCESS)

    @admin.action(description='1. Mark payment verified')
    def mark_payment_verified(self, request, queryset):
        self._run(request, queryset, 'verify_payment', 'marked as paid and verified')

    @admin.action(description='2. Confirm inspection (needs verified payment or no fee)')
    def confirm_inspections(self, request, queryset):
        self._run(request, queryset, 'confirm', 'confirmed')

    @admin.action(description='Reject inspection')
    def reject_inspections(self, request, queryset):
        self._run(request, queryset, 'reject', 'rejected')
