from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from stocks.models import Stock
from base.api.exceptions import APIError
from ..models import Portfolio, add_portfolio_stock
from .serializers import AddStockSerializer, PortfolioSerializer


class PortfolioListView(generics.ListCreateAPIView):
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PortfolioDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)


class PortfolioAddStockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            portfolio = Portfolio.objects.get(pk=pk, user=request.user)
        except Portfolio.DoesNotExist:
            raise APIError(
                "Portfolio not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="not_found",
            )

        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        symbol = serializer.validated_data["symbol"]
        amount = serializer.validated_data["amount"]

        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            raise APIError(
                "Stock not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="not_found",
            )

        if not request.user.watchlists.filter(stocks=stock).exists():
            raise APIError(
                "Stock must be in one of your watchlists.",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="invalid_stock_membership",
            )

        try:
            portfolio_stock = add_portfolio_stock(portfolio, stock, amount)
        except ValidationError as exc:
            raise APIError(
                "Stock must be in one of your watchlists.",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="invalid_stock_membership",
            ) from exc

        return Response(
            {
                "detail": f"{symbol} added to portfolio.",
                "stock": {
                    "symbol": stock.symbol,
                    "company_name": stock.company_name,
                    "exchange": stock.exchange,
                    "amount": str(portfolio_stock.amount),
                },
            },
            status=status.HTTP_200_OK,
        )


class PortfolioRemoveStockView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, symbol):
        try:
            portfolio = Portfolio.objects.get(pk=pk, user=request.user)
        except Portfolio.DoesNotExist:
            raise APIError(
                "Portfolio not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="not_found",
            )

        symbol = symbol.upper()
        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            raise APIError(
                "Stock not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="not_found",
            )

        if not portfolio.stocks.filter(pk=stock.pk).exists():
            raise APIError(
                "Stock is not in this portfolio.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="not_found",
            )

        portfolio.stocks.remove(stock)
        return Response(status=status.HTTP_204_NO_CONTENT)