from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.edit import FormView
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


class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    success_url = reverse_lazy("password_reset_done")


class CustomPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


@method_decorator(
    [login_not_required, sensitive_post_parameters(), csrf_protect, never_cache],
    name="dispatch",
)
class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")

    def dispatch(self, request, *args, **kwargs):
        self.user = self.get_user(kwargs["uidb64"])
        token = kwargs["token"]
        if token == self.reset_url_token:
            token = request.session.get(auth_views.INTERNAL_RESET_SESSION_TOKEN)
        self.validlink = bool(
            self.user and self.token_generator.check_token(self.user, token)
        )

        if not self.validlink:
            response = self.render_to_response(self.get_context_data())
        else:
            response = FormView.dispatch(self, request, *args, **kwargs)

        response.headers["Referrer-Policy"] = "origin"
        return response

    def form_valid(self, form):
        form.save()
        self.request.session.pop(auth_views.INTERNAL_RESET_SESSION_TOKEN, None)
        return HttpResponseRedirect(self.get_success_url())


class CustomPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"


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