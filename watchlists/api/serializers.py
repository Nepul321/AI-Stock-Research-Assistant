from rest_framework import serializers
from ..models import Watchlist
from stocks.api.serializers import StockSerializer


class WatchlistSerializer(serializers.ModelSerializer):
    stocks = StockSerializer(many=True, read_only=True)
    class Meta:
        model = Watchlist
        fields = [
            "id",
            "name",
            "stocks",
        ]