import binascii

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import get_md5_hash_password


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "confirm_password"]

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "The passwords do not match."}
            )

        candidate = User(
            username=attrs["username"],
            email=attrs["email"],
        )
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"password": exc.messages}
            ) from exc

        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "The passwords do not match."}
            )

        try:
            validate_password(
                attrs["new_password"],
                self.context["request"].user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"new_password": exc.messages}
            ) from exc

        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    confirm_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "The passwords do not match."}
            )

        user_model = get_user_model()
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uidb64"]))
            user = user_model._default_manager.get(pk=user_id)
        except (
            binascii.Error,
            DjangoValidationError,
            TypeError,
            ValueError,
            OverflowError,
            user_model.DoesNotExist,
        ) as exc:
            raise serializers.ValidationError(
                {"token": "This password reset link is invalid or expired."}
            ) from exc

        if (
            not user.is_active
            or not default_token_generator.check_token(user, attrs["token"])
        ):
            raise serializers.ValidationError(
                {"token": "This password reset link is invalid or expired."}
            )

        try:
            validate_password(attrs["new_password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"new_password": exc.messages}
            ) from exc

        attrs["user"] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate_refresh(self, value):
        try:
            RefreshToken(value)
        except TokenError as exc:
            raise serializers.ValidationError(
                "The refresh token is invalid or expired."
            ) from exc
        return value


class PasswordAwareTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            refresh = self.token_class(attrs["refresh"])
        except TokenError as exc:
            raise AuthenticationFailed(
                "The refresh token is invalid or expired.",
                code="token_not_valid",
            ) from exc

        user_model = get_user_model()
        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        try:
            user = user_model._default_manager.get(
                **{api_settings.USER_ID_FIELD: user_id}
            )
        except user_model.DoesNotExist as exc:
            raise AuthenticationFailed(
                "The refresh token is invalid or expired.",
                code="token_not_valid",
            ) from exc

        if not api_settings.USER_AUTHENTICATION_RULE(user):
            raise AuthenticationFailed(
                "No active account found for the given token.",
                code="no_active_account",
            )

        if api_settings.CHECK_REVOKE_TOKEN and (
            refresh.payload.get(api_settings.REVOKE_TOKEN_CLAIM)
            != get_md5_hash_password(user.password)
        ):
            raise AuthenticationFailed(
                "The refresh token is invalid or expired.",
                code="token_not_valid",
            )

        return super().validate(attrs)
