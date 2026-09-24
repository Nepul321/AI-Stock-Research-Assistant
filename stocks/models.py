from django.db import models
from base.api.main import FinnhubService

# Create your models here.

class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    company_name = models.CharField(max_length=255, blank=True)
    exchange = models.CharField(max_length=50, blank=True)


    def clean(self):
        finnhub_service = FinnhubService()

        try:
            stock_data = finnhub_service.validate_stock(self.symbol)
        except Exception:
            raise ValidationError(
                "Unable to verify stock with Finnhub."
            )

        if stock_data is None:
            raise ValidationError(
                {"symbol": f"Stock '{self.symbol}' was not found on Finnhub."}
            )

        self.symbol = stock_data["symbol"]
        self.company_name = stock_data["company_name"]
        self.exchange = stock_data["exchange"]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.symbol} - {self.company_name}"