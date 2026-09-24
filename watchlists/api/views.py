from rest_framework import generics
from ..models import Watchlist
from rest_framework.permissions import IsAuthenticated
from .serializers import WatchlistSerializer, AddStockSerializer
from stocks.models import Stock
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from base.api.main import FinnhubService



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
            return Response(
                {"detail": "Watchlist not found."},
                status=status.HTTP_404_NOT_FOUND
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
                return Response(
                    {
                        "detail": "Unable to verify stock with Finnhub."
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            if not profile:
                return Response(
                    {
                        "detail": f"Stock '{symbol}' was not found."
                    },
                    status=status.HTTP_400_BAD_REQUEST
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
            return Response(
                {"detail": "Watchlist not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        symbol = symbol.upper()

        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            return Response(
                {"detail": "Stock not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not watchlist.stocks.filter(pk=stock.pk).exists():
            return Response(
                {"detail": "Stock is not in this watchlist."},
                status=status.HTTP_404_NOT_FOUND
            )

        watchlist.stocks.remove(stock)

        return Response(
            {"detail": f"{symbol} removed from watchlist."},
            status=status.HTTP_204_NO_CONTENT
        )