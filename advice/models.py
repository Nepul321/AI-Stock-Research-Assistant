from django.db import models
from django.contrib.auth.models import User
from portfolios.models import Portfolio

class Advice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt = models.TextField()
    portfolios = models.ManyToManyField(Portfolio, blank=True, related_name="advice_portfolios")
    response = models.TextField(blank=True)

