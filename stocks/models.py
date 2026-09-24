from django.db import models

# Create your models here.

class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    company_name = models.CharField(max_length=255)
    exchange = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.symbol} - {self.company_name}"