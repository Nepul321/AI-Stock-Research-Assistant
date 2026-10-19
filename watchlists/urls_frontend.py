from django.urls import path
from .views import create_watchlist, watchlist_detail_delete, watchlist_update, remove_stock_from_watchlist

urlpatterns = [
    path('create/', create_watchlist, name='create_watchlist'),
    path('<int:pk>/', watchlist_detail_delete, name='watchlist_detail_delete'),
    path('<int:pk>/update/', watchlist_update, name='watchlist_update'),
    path('<int:watchlist_id>/remove_stock/<int:stock_id>/', remove_stock_from_watchlist, name='remove_stock_from_watchlist'),
]