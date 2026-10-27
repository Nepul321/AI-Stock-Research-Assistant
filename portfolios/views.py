import logging
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.shortcuts import get_object_or_404, redirect, render

from base.api.main import FinnhubService

from .forms import PortfolioForm, PortfolioStockForm
from .models import Portfolio

logger = logging.getLogger(__name__)


class PortfolioValueUnavailable(Exception):
    pass


def calculate_portfolio_value(portfolio):
    holdings = list(portfolio.portfolio_stocks.all())
    total = Decimal("0")

    if not holdings:
        return total

    try:
        finnhub = FinnhubService()
    except Exception as exc:
        logger.exception(
            "Failed to initialize Finnhub for portfolio %s",
            portfolio.pk,
        )
        raise PortfolioValueUnavailable(
            "Current prices are unavailable. Please try again later."
        ) from exc

    for holding in holdings:
        try:
            quote = finnhub.get_stock_quote(holding.stock.symbol) or {}
            price = Decimal(str(quote.get("c")))
            if not price.is_finite() or price < 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError) as exc:
            logger.warning(
                "Invalid quote returned for %s",
                holding.stock.symbol,
            )
            raise PortfolioValueUnavailable(
                "A current price is unavailable for "
                f"{holding.stock.symbol}. Please try again later."
            ) from exc
        except Exception as exc:
            logger.exception(
                "Failed to retrieve quote for %s",
                holding.stock.symbol,
            )
            raise PortfolioValueUnavailable(
                "A current price is unavailable for "
                f"{holding.stock.symbol}. Please try again later."
            ) from exc

        total += holding.amount * price

    return total


@login_required
def portfolio_list(request):
    portfolios = (
        Portfolio.objects.filter(user=request.user)
        .prefetch_related("portfolio_stocks__stock")
    )
    return render(
        request,
        "portfolios/portfolios.html",
        {"portfolios": portfolios, "form": PortfolioForm()},
    )


@login_required
@require_GET
def portfolio_value(request, pk):
    portfolio = get_object_or_404(
        Portfolio.objects.prefetch_related("portfolio_stocks__stock"),
        pk=pk,
        user=request.user,
    )
    try:
        total = calculate_portfolio_value(portfolio)
    except PortfolioValueUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)

    return JsonResponse({"total": str(total), "currency": "USD"})


@login_required
def portfolio_create(request):
    if request.method == "POST":
        form = PortfolioForm(request.POST)
        if form.is_valid():
            portfolio = form.save(commit=False)
            portfolio.user = request.user
            portfolio.save()
            return redirect("portfolios")
    else:
        form = PortfolioForm()

    portfolios = (
        Portfolio.objects.filter(user=request.user)
        .prefetch_related("portfolio_stocks__stock")
    )
    return render(
        request,
        "portfolios/portfolios.html",
        {"portfolios": portfolios, "form": form},
    )


@login_required
def portfolio_update(request, pk):
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    form = PortfolioForm(
        request.POST if request.method == "POST" else None,
        instance=portfolio,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("portfolio_detail_delete", pk=portfolio.pk)

    return render(
        request,
        "portfolios/portfolio_update.html",
        {"form": form, "portfolio": portfolio},
    )


@login_required
def portfolio_detail_delete(request, pk):
    portfolio = get_object_or_404(
        Portfolio.objects.prefetch_related("portfolio_stocks__stock"),
        pk=pk,
        user=request.user,
    )
    if request.method == "POST":
        portfolio.delete()
        return redirect("portfolios")

    try:
        portfolio_value = calculate_portfolio_value(portfolio)
        portfolio_value_error = None
    except PortfolioValueUnavailable as exc:
        portfolio_value = None
        portfolio_value_error = str(exc)

    return render(
        request,
        "portfolios/portfolio_detail_delete.html",
        {
            "portfolio": portfolio,
            "form": PortfolioStockForm(portfolio=portfolio),
            "portfolio_value": portfolio_value,
            "portfolio_value_error": portfolio_value_error,
        },
    )


@login_required
@require_POST
def portfolio_add_stock(request, pk):
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    form = PortfolioStockForm(
        request.POST,
        portfolio=portfolio,
    )
    if form.is_valid():
        form.save()
        return redirect("portfolio_detail_delete", pk=portfolio.pk)

    portfolio = get_object_or_404(
        Portfolio.objects.prefetch_related("portfolio_stocks__stock"),
        pk=portfolio.pk,
        user=request.user,
    )
    return render(
        request,
        "portfolios/portfolio_detail_delete.html",
        {"portfolio": portfolio, "form": form},
    )


@login_required
@require_http_methods(["POST"])
def portfolio_delete_stock(request, pk, stock_id):
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)

    portfolio_stocks = portfolio.portfolio_stocks.filter(stock_id=stock_id)
    if portfolio_stocks.exists():
        portfolio_stocks.delete()


    return redirect("portfolio_detail_delete", pk=portfolio.pk)


@login_required
def portfolio_stock_update(request, pk, stock_id):
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    portfolio_stock = get_object_or_404(
        portfolio.portfolio_stocks.select_related("stock"),
        stock_id=stock_id,
    )

    if request.method == "POST":
        form = PortfolioStockForm(
            request.POST,
            instance=portfolio_stock,
            portfolio=portfolio,
        )
        if form.is_valid():
            form.save()
            return redirect("portfolio_detail_delete", pk=portfolio.pk)
    else:
        form = PortfolioStockForm(
            instance=portfolio_stock,
            portfolio=portfolio,
        )

    return render(
        request,
        "portfolios/portfolio_stock_update.html",
        {"form": form, "portfolio": portfolio, "portfolio_stock": portfolio_stock},
    )