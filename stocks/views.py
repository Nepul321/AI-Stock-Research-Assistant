from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from .forms import StockSearchForm
from .models import Stock


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