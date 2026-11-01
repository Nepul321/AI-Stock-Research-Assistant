from django.urls import path
from .api.views import *

urlpatterns = [
    path("", WatchlistListView.as_view(), name="watchlist-list"),
    path("<int:pk>/", WatchlistDetailView.as_view(), name="watchlist-detail"),
    path(
        "<int:pk>/add/",
        WatchlistAddStockView.as_view(),
        name="watchlist-add-stock",
    ),
    path(
        "<int:pk>/<str:symbol>/",
        WatchlistRemoveStockView.as_view(),
        name="watchlist-remove-stock",
    ),
]