from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm as DjangoUserChangeForm

from .models import Role, User


class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role')


class UserChangeForm(DjangoUserChangeForm):
    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('first_name', 'last_name', 'phone', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2')}),
    )

    def save_related(self, request, form, formsets, change):
        # Runs after the change form's user_permissions widget has been saved, so a
        # staff account keeps the model permissions its queues need.
        super().save_related(request, form, formsets, change)
        if form.instance.role == Role.STAFF and not form.instance.is_superuser:
            form.instance._grant_staff_permissions()
