from django import forms

from watchlists.models import Watchlist


class StockSearchForm(forms.Form):
    symbol = forms.CharField(
        max_length=10,
        label="Stock symbol",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. AAPL",
            "autocapitalize": "characters",
        }),
    )

    watchlist = forms.ModelChoiceField(
        queryset=Watchlist.objects.none(),
        label="Add to watchlist",
        empty_label="Choose a watchlist",
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["watchlist"].queryset = (
            Watchlist.objects.filter(user=user)
        )

    def clean_symbol(self):
        return self.cleaned_data["symbol"].strip().upper()