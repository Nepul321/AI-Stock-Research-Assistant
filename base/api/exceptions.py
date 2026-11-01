from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import APIException
from rest_framework.exceptions import ErrorDetail
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler as default_exception_handler


class APIError(APIException):
    def __init__(self, detail, *, status_code, code):
        self.status_code = status_code
        super().__init__(detail=detail, code=code)


def _normalize(value):
    if isinstance(value, ErrorDetail):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        exc = DRFValidationError(detail)

    response = default_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, DRFValidationError):
        error = {
            "code": "validation_error",
            "message": "Request validation failed.",
            "details": _normalize(response.data),
        }
    else:
        if isinstance(response.data, dict) and "detail" in response.data:
            detail = response.data["detail"]
            message = _normalize(detail)
            code = getattr(
                getattr(exc, "detail", detail),
                "code",
                getattr(
                    detail,
                    "code",
                    getattr(exc, "default_code", "api_error"),
                ),
            )
            details = {}
        else:
            message = "Request failed."
            code = getattr(exc, "default_code", "api_error")
            details = _normalize(response.data)
        error = {
            "code": str(code),
            "message": message,
            "details": details,
        }

    response.data = {"error": error}
    return response
