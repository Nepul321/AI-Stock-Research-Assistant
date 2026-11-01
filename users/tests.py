from django.test import TestCase
from django.core import mail
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.test import Client, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from urllib.parse import urlsplit
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken


class PasswordResetConfirmTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username="reset-test-user",
			email="reset-test@example.com",
			password="Original-password-42!",
		)
		uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
		token = default_token_generator.make_token(self.user)
		self.reset_url = reverse(
			"password_reset_confirm",
			kwargs={"uidb64": uidb64, "token": token},
		)

	def test_valid_link_works_without_a_redirect_session(self):
		response = self.client.get(self.reset_url)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context["validlink"])
		self.assertContains(response, "Set a new password")
		self.assertEqual(
			response.context["form"].fields["new_password1"].widget.attrs["class"],
			"form-control",
		)
		self.assertEqual(
			response.context["form"].fields["new_password2"].widget.attrs["class"],
			"form-control",
		)
		self.assertEqual(response.headers["Referrer-Policy"], "origin")

	def test_password_reset_request_form_uses_bootstrap_class(self):
		response = self.client.get(reverse("password_reset"))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			response.context["form"].fields["email"].widget.attrs["class"],
			"form-control",
		)

	def test_previous_token_free_link_works_with_its_session(self):
		token_free_url = reverse(
			"password_reset_confirm",
			kwargs={
				"uidb64": urlsafe_base64_encode(force_bytes(self.user.pk)),
				"token": auth_views.PasswordResetConfirmView.reset_url_token,
			},
		)
		session = self.client.session
		session[auth_views.INTERNAL_RESET_SESSION_TOKEN] = self.reset_url.rsplit("/", 2)[-2]
		session.save()

		response = self.client.get(token_free_url)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context["validlink"])

	def test_successful_reset_invalidates_the_link(self):
		response = self.client.post(
			self.reset_url,
			{
				"new_password1": "A-new-stock-password-93!",
				"new_password2": "A-new-stock-password-93!",
			},
		)

		self.assertRedirects(response, reverse("password_reset_complete"))
		self.user.refresh_from_db()
		self.assertTrue(self.user.check_password("A-new-stock-password-93!"))

		response = self.client.get(self.reset_url)
		self.assertFalse(response.context["validlink"])

	@override_settings(
		EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
		ALLOWED_HOSTS=["testserver", "127.0.0.1"],
	)
	def test_generated_email_link_works_in_a_fresh_client(self):
		response = self.client.post(
			reverse("password_reset"),
			{"email": self.user.email},
			HTTP_HOST="127.0.0.1:8000",
		)

		self.assertRedirects(response, reverse("password_reset_done"))
		self.assertEqual(len(mail.outbox), 1)
		reset_link = next(
			line.strip()
			for line in mail.outbox[0].body.splitlines()
			if "/reset/" in line
		)
		self.assertLess(len(reset_link), 76)

		response = Client().get(urlsplit(reset_link).path)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Set a new password")


class AuthenticationAPITests(APITestCase):
	@classmethod
	def setUpTestData(cls):
		cls.user = User.objects.create_user(
			username="api-auth-user",
			email="api-auth@example.com",
			password="Original-long-password-91!",
		)

	def test_registration_validates_password_and_uses_standard_error_shape(self):
		response = self.client.post(
			reverse("api-register"),
			{
				"username": "new-api-user",
				"email": "new-api@example.com",
				"password": "short",
				"confirm_password": "different",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.data["error"]["code"], "validation_error")
		self.assertEqual(
			response.data["error"]["message"],
			"Request validation failed.",
		)
		self.assertIn(
			"confirm_password",
			response.data["error"]["details"],
		)
		self.assertFalse(User.objects.filter(username="new-api-user").exists())

		weak_password_response = self.client.post(
			reverse("api-register"),
			{
				"username": "new-api-user",
				"email": "new-api@example.com",
				"password": "short",
				"confirm_password": "short",
			},
			format="json",
		)
		self.assertEqual(weak_password_response.status_code, 400)
		self.assertIn(
			"password",
			weak_password_response.data["error"]["details"],
		)

	def test_registration_and_token_login_are_anonymous_only(self):
		self.client.force_login(self.user)

		register_response = self.client.post(
			reverse("api-register"),
			{
				"username": "another-api-user",
				"email": "another-api@example.com",
				"password": "Another-long-password-91!",
				"confirm_password": "Another-long-password-91!",
			},
			format="json",
		)
		token_response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": self.user.username,
				"password": "Original-long-password-91!",
			},
			format="json",
		)

		for response in (register_response, token_response):
			self.assertEqual(response.status_code, 403)
			self.assertEqual(
				response.data["error"]["code"],
				"not_anonymous",
			)

	def test_jwt_login_rotates_refresh_token_and_logout_revokes_it(self):
		login_response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": self.user.username,
				"password": "Original-long-password-91!",
			},
			format="json",
		)
		self.assertEqual(login_response.status_code, 200)

		old_refresh = login_response.data["refresh"]
		refresh_response = self.client.post(
			reverse("token_refresh"),
			{"refresh": old_refresh},
			format="json",
		)
		self.assertEqual(refresh_response.status_code, 200)
		new_refresh = refresh_response.data["refresh"]
		self.assertNotEqual(old_refresh, new_refresh)

		self.client.credentials(
			HTTP_AUTHORIZATION=f"Bearer {refresh_response.data['access']}"
		)
		logout_response = self.client.post(
			reverse("token_logout"),
			{"refresh": new_refresh},
			format="json",
		)
		self.assertEqual(logout_response.status_code, 204)

		revoked_response = self.client.post(
			reverse("token_refresh"),
			{"refresh": new_refresh},
			format="json",
		)
		self.assertEqual(revoked_response.status_code, 401)
		self.assertEqual(
			revoked_response.data["error"]["code"],
			"token_not_valid",
		)

	@override_settings(
		EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
		ALLOWED_HOSTS=["testserver"],
	)
	def test_password_reset_email_and_confirmation_complete_auth_cycle(self):
		old_refresh_token = RefreshToken.for_user(self.user)
		old_refresh = str(old_refresh_token)
		old_access = str(old_refresh_token.access_token)
		request_response = self.client.post(
			reverse("api_password_reset"),
			{"email": self.user.email},
			format="json",
		)
		self.assertEqual(request_response.status_code, 200)
		self.assertEqual(len(mail.outbox), 1)

		reset_link = next(
			line.strip()
			for line in mail.outbox[0].body.splitlines()
			if "/reset/" in line
		)
		_, uidb64, token = urlsplit(reset_link).path.strip("/").split("/")
		reset_response = self.client.post(
			reverse("api_password_reset_confirm"),
			{
				"uidb64": uidb64,
				"token": token,
				"new_password": "Brand-new-secure-password-91!",
				"confirm_password": "Brand-new-secure-password-91!",
			},
			format="json",
		)

		self.assertEqual(reset_response.status_code, 200)
		self.user.refresh_from_db()
		self.assertTrue(
			self.user.check_password("Brand-new-secure-password-91!")
		)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
		old_access_response = self.client.get(reverse("watchlist-list"))
		self.assertEqual(old_access_response.status_code, 403)
		self.assertEqual(
			old_access_response.data["error"]["code"],
			"authentication_failed",
			old_access_response.data,
		)
		revoked_refresh_response = self.client.post(
			reverse("token_refresh"),
			{"refresh": old_refresh},
			format="json",
		)
		self.assertEqual(revoked_refresh_response.status_code, 401)
		self.assertEqual(
			revoked_refresh_response.data["error"]["code"],
			"token_not_valid",
		)

	def test_password_reset_request_does_not_disclose_unknown_email(self):
		response = self.client.post(
			reverse("api_password_reset"),
			{"email": "unknown@example.com"},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(mail.outbox), 0)
		self.assertIn("If an account exists", response.data["detail"])

	def test_password_change_requires_authentication_and_validates_password(self):
		anonymous_response = self.client.post(
			reverse("api-change-password"),
			{
				"old_password": "Original-long-password-91!",
				"new_password": "Another-secure-password-93!",
				"confirm_password": "Another-secure-password-93!",
			},
			format="json",
		)
		self.assertEqual(anonymous_response.status_code, 403)
		self.assertEqual(
			anonymous_response.data["error"]["code"],
			"not_authenticated",
		)

		self.client.force_authenticate(user=self.user)
		change_response = self.client.post(
			reverse("api-change-password"),
			{
				"old_password": "incorrect",
				"new_password": "Another-secure-password-93!",
				"confirm_password": "Another-secure-password-93!",
			},
			format="json",
		)
		self.assertEqual(change_response.status_code, 400)
		self.assertEqual(
			change_response.data["error"]["code"],
			"validation_error",
		)
		self.assertIn(
			"old_password",
			change_response.data["error"]["details"],
		)

	def test_web_password_change_keeps_session_available_for_logout(self):
		self.client.force_login(self.user)

		change_response = self.client.post(
			reverse("password_change"),
			{
				"old_password": "Original-long-password-91!",
				"new_password1": "Another-secure-password-93!",
				"new_password2": "Another-secure-password-93!",
			},
		)
		self.assertRedirects(
			change_response,
			reverse("password_change_done"),
		)

		logout_response = self.client.post(reverse("logout"))

		self.assertRedirects(logout_response, reverse("login"))
		self.assertNotIn("_auth_user_id", self.client.session)

	def test_api_password_change_revokes_tokens_before_logout(self):
		login_response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": self.user.username,
				"password": "Original-long-password-91!",
			},
			format="json",
		)
		self.assertEqual(login_response.status_code, 200)
		access = login_response.data["access"]
		refresh = login_response.data["refresh"]
		self.client.credentials(
			HTTP_AUTHORIZATION=f"Bearer {access}"
		)

		change_response = self.client.post(
			reverse("api-change-password"),
			{
				"old_password": "Original-long-password-91!",
				"new_password": "Another-secure-password-93!",
				"confirm_password": "Another-secure-password-93!",
			},
			format="json",
		)
		self.assertEqual(change_response.status_code, 200)

		logout_response = self.client.post(
			reverse("token_logout"),
			{"refresh": refresh},
			format="json",
		)
		self.assertEqual(logout_response.status_code, 403)
		self.assertEqual(
			logout_response.data["error"]["code"],
			"authentication_failed",
		)

		self.client.credentials(
			HTTP_AUTHORIZATION=f"Bearer {refresh}"
		)
		refresh_logout_response = self.client.post(
			reverse("token_logout"),
			{"refresh": refresh},
			format="json",
		)
		self.assertEqual(refresh_logout_response.status_code, 403)
		self.assertEqual(
			refresh_logout_response.data["error"]["code"],
			"token_not_valid",
		)

		refresh_response = self.client.post(
			reverse("token_refresh"),
			{"refresh": refresh},
			format="json",
		)
		self.assertEqual(refresh_response.status_code, 401)
		self.assertEqual(
			refresh_response.data["error"]["code"],
			"token_not_valid",
		)

		self.client.credentials()
		new_login_response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": self.user.username,
				"password": "Another-secure-password-93!",
			},
			format="json",
		)
		self.assertEqual(new_login_response.status_code, 200)
