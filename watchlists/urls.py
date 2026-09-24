from django.urls import path
from .api.views import WatchlistListView, WatchlistDetailView

urlpatterns = [
    path("", WatchlistListView.as_view()),
    path("<int:pk>/", WatchlistDetailView.as_view()),
]