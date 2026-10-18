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
		self.assertEqual(response.headers["Referrer-Policy"], "origin")

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
