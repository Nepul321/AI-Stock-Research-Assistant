from django.urls import path

from .views import (
    PortfolioAddStockView,
    PortfolioDetailView,
    PortfolioListView,
    PortfolioRemoveStockView,
)

urlpatterns = [
    path("", PortfolioListView.as_view(), name="portfolio-list"),
    path("<int:pk>/", PortfolioDetailView.as_view(), name="portfolio-detail"),
    path("<int:pk>/add/", PortfolioAddStockView.as_view(), name="portfolio-add-stock"),
    path(
        "<int:pk>/<str:symbol>/",
        PortfolioRemoveStockView.as_view(),
        name="portfolio-remove-stock",
    ),
]