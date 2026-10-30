import logging
import math
from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from base.api.main import FinnhubService
from .forms import StockSearchForm
from .models import Stock

logger = logging.getLogger(__name__)


@login_required
def stock_search(request):
    if request.method == "POST":
        form = StockSearchForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            symbol = form.cleaned_data["symbol"]
            watchlist = form.cleaned_data["watchlist"]

            try:
                stock, created = Stock.objects.get_or_create(
                    symbol=symbol,
                    defaults={
                        "company_name": "Pending validation",
                        "exchange": "",
                    },
                )

            except ValidationError as exc:
                for field_errors in exc.message_dict.values():
                    for error in field_errors:
                        messages.error(request, error)

            except Exception:
                messages.error(
                    request,
                    "Unable to verify this stock right now. "
                    "Please try again later.",
                )

            else:
                if watchlist.stocks.filter(pk=stock.pk).exists():
                    messages.info(
                        request,
                        f"{stock.symbol} is already in "
                        f"'{watchlist.name}'.",
                    )
                else:
                    watchlist.stocks.add(stock)

                    messages.success(
                        request,
                        f"{stock.symbol} was added to "
                        f"'{watchlist.name}'.",
                    )

                return redirect("stock_search")

    else:
        form = StockSearchForm(user=request.user)

    return render(
        request,
        "stocks/search.html",
        {"form": form},
    )


@login_required
def stock_detail(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    profile = {}
    quote = {}
    chart_data = {"labels": [], "prices": [], "trend": []}

    try:
        finnhub = FinnhubService()
    except Exception:
        logger.exception("Failed to initialize Finnhub for %s", stock.symbol)
    else:
        try:
            profile = finnhub.get_stock_profile(stock.symbol) or {}
        except Exception:
            logger.exception("Failed to retrieve profile for %s", stock.symbol)

        try:
            quote = finnhub.get_stock_quote(stock.symbol) or {}
        except Exception:
            logger.exception("Failed to retrieve quote for %s", stock.symbol)

        try:
            candles = finnhub.get_stock_candles(stock.symbol) or {}
        except Exception:
            logger.exception("Failed to retrieve price history for %s", stock.symbol)
        else:
            if isinstance(candles, dict) and candles.get("s") == "ok":
                timestamps = candles.get("t", [])
                prices = candles.get("c", [])
                observations = []

                for timestamp, price in zip(timestamps, prices):
                    try:
                        timestamp = int(timestamp)
                        price = float(price)
                    except (TypeError, ValueError, OverflowError):
                        continue

                    if not math.isfinite(price):
                        continue

                    observations.append((timestamp, price))

                observations.sort()
                chart_data["labels"] = [
                    datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(
                        "%Y-%m-%d"
                    )
                    for timestamp, _ in observations
                ]
                chart_data["prices"] = [
                    price for _, price in observations
                ]
                chart_data["trend"] = [
                    (
                        sum(
                            chart_data["prices"][index - 19:index + 1]
                        ) / 20
                        if index >= 19
                        else None
                    )
                    for index in range(len(chart_data["prices"]))
                ]

    return render(
        request,
        "stocks/detail.html",
        {
            "stock": stock,
            "profile": profile,
            "quote": quote,
            "chart_data": chart_data,
        },
    )