from rest_framework import serializers
from ..models import Watchlist
from stocks.api.serializers import StockSerializer
from stocks.models import Stock


class WatchlistSerializer(serializers.ModelSerializer):
    stocks = StockSerializer(many=True, read_only=True)
    class Meta:
        model = Watchlist
        fields = [
            "id",
            "name",
            "stocks",
        ]

class AddStockSerializer(serializers.Serializer):
    symbol = serializers.CharField(max_length=10)

    def validate_symbol(self, value):
        return value.upper().strip()