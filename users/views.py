from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy

from .forms import RegisterForm, BootstrapPasswordChangeForm, AccountEditForm


class RegisterView(UserPassesTestMixin, CreateView):
    form_class = RegisterForm
    template_name = "registration/register.html"
    success_url = "/accounts/login/"

    def test_func(self):
        return not self.request.user.is_authenticated

    def form_valid(self, form):
        response = super().form_valid(form)

        login(self.request, self.object)

        return response

class CustomPasswordChangeView(
    LoginRequiredMixin,
    auth_views.PasswordChangeView,
):
    form_class = BootstrapPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = "/accounts/password-change/done/"


class AccountEditView(LoginRequiredMixin, UpdateView):
    form_class = AccountEditForm
    template_name = "accounts/edit.html"
    success_url = reverse_lazy("account_edit")

    def get_object(self, queryset=None):
        return self.request.user