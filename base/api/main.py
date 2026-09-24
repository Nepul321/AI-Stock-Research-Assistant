import finnhub
from django.conf import settings

finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)

# Stock candles

def test_api(stock):
    res = finnhub_client.symbol_lookup(stock)
    return res