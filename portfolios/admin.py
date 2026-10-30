from django.contrib import admin
from .models import Portfolio, PortfolioStock, PortfolioValueSnapshot

admin.site.register(Portfolio)
admin.site.register(PortfolioStock)
admin.site.register(PortfolioValueSnapshot)