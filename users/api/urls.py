from django.urls import path
from .views import AccountView, ChangePasswordView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="api-register"),
    path("account/", AccountView.as_view(), name="api-account"),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="api-change-password",
    ),
]