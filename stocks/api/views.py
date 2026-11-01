from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from ..models import Stock
from .serializers import StockSerializer


class StockListView(generics.ListCreateAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]

class StockDetailView(generics.RetrieveAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]