from django.urls import path
from django.contrib.auth import views as auth_views

from .views import RegisterView, CustomPasswordChangeView, AccountEditView
from .forms import LoginForm

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),

    path(
        "password-change/",
        CustomPasswordChangeView.as_view(
             template_name="accounts/password_change.html"
        ),
        name="password_change",
    ),

    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html"
        ),
        name="password_change_done",
    ),

    path(
        "edit/",
        AccountEditView.as_view(),
        name="account_edit",
    ),
]