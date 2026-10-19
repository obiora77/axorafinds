from rest_framework.permissions import BasePermission

from .models import Role


class IsOwnerRole(BasePermission):
    message = 'Only owner accounts can list properties.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.OWNER)


class IsSeekerRole(BasePermission):
    message = 'Only seeker accounts can save favorites.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.SEEKER)
