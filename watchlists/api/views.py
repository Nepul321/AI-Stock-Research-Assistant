from rest_framework import generics
from ..models import Watchlist
from rest_framework.permissions import IsAuthenticated
from .serializers import WatchlistSerializer, AddStockSerializer
from stocks.models import Stock
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from base.api.main import FinnhubService
from base.api.exceptions import APIError


class WatchlistListView(generics.ListCreateAPIView):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WatchlistDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user)


class WatchlistAddStockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            watchlist = Watchlist.objects.get(
                pk=pk,
                user=request.user
            )
        except Watchlist.DoesNotExist:
            raise APIError(
                "Watchlist not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="not_found",
            )

        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        symbol = serializer.validated_data["symbol"]

        stock = Stock.objects.filter(
            symbol=symbol
        ).first()

        if stock is None:
            finnhub_service = FinnhubService()

            try:
                profile = finnhub_service.get_stock_profile(symbol)
            except Exception:
                raise APIError(
                    "Unable to verify stock with Finnhub.",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    code="stock_provider_unavailable",
                )

            if not profile:
                raise APIError(
                    f"Stock '{symbol}' was not found.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code="invalid_stock",
                )

            stock = Stock.objects.create(
                symbol=symbol,
                company_name=profile.get("name", ""),
                exchange=profile.get("exchange", ""),
            )
        watchlist.stocks.add(stock)

        return Response(
            {
                "detail": f"{symbol} added to watchlist.",
                "stock": {
                    "symbol": stock.symbol,
                    "company_name": stock.company_name,
                    "exchange": stock.exchange,
                },
            },
            status=status.HTTP_200_OK
        )


class WatchlistRemoveStockView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, symbol):
        try:
            watchlist = Watchlist.objects.get(
                pk=pk,
                user=request.user
            )
        except Watchlist.DoesNotExist:
            raise APIError(
                "Watchlist not found.",
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

        if not watchlist.stocks.filter(pk=stock.pk).exists():
            raise APIError(
                "Stock is not in this watchlist.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="not_found",
            )

        watchlist.stocks.remove(stock)

        return Response(status=status.HTTP_204_NO_CONTENT)