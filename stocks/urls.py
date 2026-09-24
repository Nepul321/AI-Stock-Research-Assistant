from django.urls import path
from .api.views import StockListView, StockDetailView

urlpatterns = [
    path("", StockListView.as_view()),
    path("<int:pk>/", StockDetailView.as_view()),
]