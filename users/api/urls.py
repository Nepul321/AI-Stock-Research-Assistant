from django.urls import path
from .views import ChangePasswordView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="api-register"),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="api-change-password",
    ),
]