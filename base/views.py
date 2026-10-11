import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .api.main import FinnhubService
from watchlists.models import Watchlist

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "base/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        watchlists = (
            Watchlist.objects
            .filter(user=self.request.user)
            .prefetch_related("stocks")
        )

        stocks_by_symbol = {}

        for watchlist in watchlists:
            for stock in watchlist.stocks.all():
                stocks_by_symbol[stock.symbol] = stock

        stock_quotes = []
        finnhub = FinnhubService()

        for stock in list(stocks_by_symbol.values())[:10]:
            try:
                quote = finnhub.get_stock_quote(stock.symbol)

                stock_quotes.append({
                    "stock": stock,
                    "price": quote.get("c"),
                    "change": quote.get("d"),
                    "change_percent": quote.get("dp"),
                })

            except Exception:
                logger.exception(
                    "Failed to retrieve quote for %s",
                    stock.symbol,
                )

                stock_quotes.append({
                    "stock": stock,
                    "price": None,
                    "change": None,
                    "change_percent": None,
                })

        context.update({
            "watchlists": watchlists,
            "watchlist_count": watchlists.count(),
            "tracked_stock_count": len(stocks_by_symbol),
            "stock_quotes": stock_quotes,
        })

        return context