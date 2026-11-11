"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from users.views import CustomPasswordResetConfirmView
from users.api.views import (
    LogoutAPIView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    TokenObtainPairAPIView,
    TokenRefreshAPIView,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        "reset/<uidb64>/<token>/",
        CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm_email",
    ),
    path('', include('base.urls')),
    path('api/stocks/', include('stocks.urls')),
    path('api/watchlists/', include('watchlists.urls')),
    path('api/portfolios/', include('portfolios.api.urls')),
    path(
        "api/token/",
        TokenObtainPairAPIView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/token/refresh/",
        TokenRefreshAPIView.as_view(),
        name="token_refresh",
    ),
    path(
        "api/token/logout/",
        LogoutAPIView.as_view(),
        name="token_logout",
    ),
    path(
        "api/users/password-reset/",
        PasswordResetRequestView.as_view(),
        name="api_password_reset",
    ),
    path(
        "api/users/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="api_password_reset_confirm",
    ),
    path('api/users/', include('users.api.urls')),
    path('api/advice/', include('advice.api.urls')),
    path('accounts/', include('users.urls')),
    path('stocks/', include('stocks.urls_frontend')),
    path('watchlists/', include('watchlists.urls_frontend')),
    path('portfolios/', include('portfolios.urls')),
    path('advice/', include('advice.urls')),
]
