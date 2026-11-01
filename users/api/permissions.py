from rest_framework.permissions import BasePermission


class AnonymousOnly(BasePermission):
    message = "This endpoint is only available to anonymous users."
    code = "not_anonymous"

    def has_permission(self, request, view):
        return not request.user.is_authenticated
