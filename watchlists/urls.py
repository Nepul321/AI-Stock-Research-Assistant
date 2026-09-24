from django.urls import path
from .api.views import *

urlpatterns = [
    path("", WatchlistListView.as_view()),
    path("<int:pk>/", WatchlistDetailView.as_view()),
    path("<int:pk>/add/", WatchlistAddStockView.as_view()),
    path("<int:pk>/<str:symbol>/", WatchlistRemoveStockView.as_view()),
]