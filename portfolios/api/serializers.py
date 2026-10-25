from decimal import Decimal

from rest_framework import serializers

from ..models import Portfolio, PortfolioStock


class PortfolioStockSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="stock.id", read_only=True)
    symbol = serializers.CharField(source="stock.symbol", read_only=True)
    company_name = serializers.CharField(source="stock.company_name", read_only=True)
    exchange = serializers.CharField(source="stock.exchange", read_only=True)

    class Meta:
        model = PortfolioStock
        fields = ["id", "symbol", "company_name", "exchange", "amount"]


class PortfolioSerializer(serializers.ModelSerializer):
    stocks = PortfolioStockSerializer(
        source="portfolio_stocks",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Portfolio
        fields = ["id", "name", "stocks"]


class AddStockSerializer(serializers.Serializer):
    symbol = serializers.CharField(max_length=10)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        min_value=Decimal("0.0001"),
    )

    def validate_symbol(self, value):
        return value.upper().strip()