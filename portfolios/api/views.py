from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from stocks.models import Stock
from ..models import Portfolio, PortfolioStock
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
            return Response(
                {"detail": "Portfolio not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        symbol = serializer.validated_data["symbol"]
        amount = serializer.validated_data["amount"]

        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            return Response(
                {"detail": "Stock not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not request.user.watchlists.filter(stocks=stock).exists():
            return Response(
                {"detail": "Stock must be in one of your watchlists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            portfolio_stock, _ = PortfolioStock.objects.update_or_create(
                portfolio=portfolio,
                stock=stock,
                defaults={"amount": amount},
            )
        except ValidationError:
            return Response(
                {"detail": "Stock must be in one of your watchlists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
            return Response(
                {"detail": "Portfolio not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        symbol = symbol.upper()
        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            return Response(
                {"detail": "Stock not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not portfolio.stocks.filter(pk=stock.pk).exists():
            return Response(
                {"detail": "Stock is not in this portfolio."},
                status=status.HTTP_404_NOT_FOUND,
            )

        portfolio.stocks.remove(stock)
        return Response(status=status.HTTP_204_NO_CONTENT)