from django.urls import path, include
from .views import AdviceListView

urlpatterns = [
  path('', AdviceListView, name="advice-list"),
]