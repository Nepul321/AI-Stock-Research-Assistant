from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from base.api.exceptions import APIError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from .permissions import AnonymousOnly
from .serializers import (
    AccountSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordAwareTokenRefreshSerializer,
    RegisterSerializer,
)

def revoke_user_refresh_tokens(user):
    for token in OutstandingToken.objects.filter(user=user).iterator():
        BlacklistedToken.objects.get_or_create(token=token)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AnonymousOnly]


class AccountView(generics.RetrieveUpdateAPIView):
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class TokenObtainPairAPIView(TokenObtainPairView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [AnonymousOnly]


class TokenRefreshAPIView(TokenRefreshView):
    authentication_classes = []
    permission_classes = [AllowAny]
    _serializer_class = (
        "users.api.serializers.PasswordAwareTokenRefreshSerializer"
    )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        with transaction.atomic():
            user.set_password(serializer.validated_data["new_password"])
            user.save(update_fields=["password"])
            revoke_user_refresh_tokens(user)

        update_session_auth_hash(request, user)
        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        form = PasswordResetForm(data=serializer.validated_data)
        if not form.is_valid():
            raise DRFValidationError(form.errors)
        try:
            form.save(
                request=request,
                domain_override=request.get_host(),
                use_https=request.is_secure(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                email_template_name="registration/password_reset_email.html",
            )
        except (SMTPException, OSError) as exc:
            raise APIError(
                "The password reset email could not be sent. Please try again.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="email_unavailable",
            ) from exc

        return Response(
            {
                "detail": (
                    "If an account exists for the submitted email, "
                    "a password reset email has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        with transaction.atomic():
            user.set_password(serializer.validated_data["new_password"])
            user.save(update_fields=["password"])
            revoke_user_refresh_tokens(user)

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = RefreshToken(serializer.validated_data["refresh"])
        user_id = token.get(api_settings.USER_ID_CLAIM)
        authenticated_user_id = getattr(
            request.user,
            api_settings.USER_ID_FIELD,
        )
        if str(user_id) != str(authenticated_user_id):
            raise APIError(
                "The refresh token does not belong to the authenticated user.",
                status_code=status.HTTP_403_FORBIDDEN,
                code="token_user_mismatch",
            )

        token.blacklist()
        return Response(status=status.HTTP_204_NO_CONTENT)
