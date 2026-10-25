from django import forms

from stocks.models import Stock

from .models import Portfolio, PortfolioStock


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
        self.fields["stock"].queryset = (
            Stock.objects.filter(watchlists__user=portfolio.user)
            .exclude(portfolio_stocks__portfolio=portfolio)
            .distinct()
        )

    def save(self, commit=True):
        portfolio_stock = super().save(commit=False)
        portfolio_stock.portfolio = self.portfolio
        if commit:
            portfolio_stock.save()
        return portfolio_stock
