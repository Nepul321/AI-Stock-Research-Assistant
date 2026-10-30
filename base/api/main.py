import finnhub
from django.conf import settings
from datetime import datetime, timedelta, timezone

# Stock candles
class FinnhubService:
    def __init__(self):
        self.client = finnhub.Client(
            api_key=settings.FINNHUB_API_KEY
        )

    def get_stock_profile(self, symbol):
        return self.client.company_profile2(
            symbol=symbol
        )

    def get_stock_quote(self, symbol):
        symbol = symbol.upper().strip()
        return self.client.quote(symbol=symbol)

    def get_stock_candles(self, symbol, days=180):
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        return self.client.stock_candles(
            symbol.upper().strip(),
            "D",
            int(start.timestamp()),
            int(end.timestamp()),
        )


    def validate_stock(self, symbol):

        symbol = symbol.upper().strip()
        profile = self.get_stock_profile(symbol)

        if not profile:
            return None

        return {
            "symbol": symbol,
            "company_name": profile.get("name", ""),
            "exchange": profile.get("exchange", ""),
        }