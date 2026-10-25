from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PortfolioForm, PortfolioStockForm
from .models import Portfolio


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

    return render(
        request,
        "portfolios/portfolio_detail_delete.html",
        {
            "portfolio": portfolio,
            "form": PortfolioStockForm(portfolio=portfolio),
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