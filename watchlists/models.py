from django.db import models
from django.contrib.auth.models import User
from stocks.models import Stock

class Watchlist(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="watchlists"
    )
    name = models.CharField(max_length=100)
    stocks = models.ManyToManyField(Stock, blank=True, related_name="watchlists")

    def __str__(self):
        return self.name