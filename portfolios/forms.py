from django import forms

from stocks.models import Stock

from .models import Portfolio, PortfolioStock, add_portfolio_stock


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Long-term investments",
                }
            ),
        }


class PortfolioStockForm(forms.ModelForm):
    class Meta:
        model = PortfolioStock
        fields = ["stock", "amount"]
        widgets = {
            "stock": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.0001",
                    "min": "0.0001",
                }
            ),
        }

    def __init__(self, *args, portfolio, **kwargs):
        super().__init__(*args, **kwargs)
        self.portfolio = portfolio
        queryset = Stock.objects.filter(watchlists__user=portfolio.user)
        if self.instance.pk:
            existing_stock_ids = portfolio.portfolio_stocks.exclude(
                pk=self.instance.pk
            ).values_list("stock_id", flat=True)
            queryset = queryset.exclude(pk__in=existing_stock_ids)
        self.fields["stock"].queryset = queryset.distinct()

    def save(self, commit=True):
        portfolio_stock = super().save(commit=False)
        portfolio_stock.portfolio = self.portfolio
        if commit:
            if self.instance.pk:
                portfolio_stock.save()
            else:
                portfolio_stock = add_portfolio_stock(
                    self.portfolio,
                    portfolio_stock.stock,
                    portfolio_stock.amount,
                )
        return portfolio_stock
