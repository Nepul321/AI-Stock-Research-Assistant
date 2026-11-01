from django.urls import path
from .api.views import StockListView, StockDetailView

urlpatterns = [
    path("", StockListView.as_view(), name="stock-list"),
    path("<int:pk>/", StockDetailView.as_view(), name="stock-detail"),
]