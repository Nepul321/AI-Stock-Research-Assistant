from django.urls import path

from . import views

urlpatterns = [
    path("", views.portfolio_list, name="portfolios"),
    path("create/", views.portfolio_create, name="portfolio_create"),
    path("<int:pk>/add-stock/", views.portfolio_add_stock, name="portfolio_add_stock"),
    path("<int:pk>/value/", views.portfolio_value, name="portfolio_value"),
    path("<int:pk>/", views.portfolio_detail_delete, name="portfolio_detail_delete"),
    path("<int:pk>/update/", views.portfolio_update, name="portfolio_update"),
    path("<int:pk>/delete/<int:stock_id>/", views.portfolio_delete_stock, name="portfolio_delete_stock"),
    path("<int:pk>/update/<int:stock_id>/", views.portfolio_stock_update, name="portfolio_update_stock")
]