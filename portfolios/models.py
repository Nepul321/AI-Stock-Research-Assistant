from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F
from django.db.models.signals import m2m_changed
from django.db.models.signals import post_delete, pre_delete
from watchlists.models import Watchlist

class Portfolio(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portfolios')
    stocks = models.ManyToManyField('stocks.Stock', through='PortfolioStock', related_name='portfolios')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PortfolioStock(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='portfolio_stocks')
    stock = models.ForeignKey('stocks.Stock', on_delete=models.CASCADE, related_name='portfolio_stocks')
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('1'),
        validators=[MinValueValidator(Decimal('0.0001'))],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('portfolio', 'stock'), name='unique_portfolio_stock'),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='positive_portfolio_stock_amount',
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.portfolio_id
            and self.stock_id
            and not self.portfolio.user.watchlists.filter(stocks__id=self.stock_id).exists()
        ):
            raise ValidationError({
                'stock': "The stock must be in one of this user's watchlists."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


def add_portfolio_stock(portfolio, stock, amount):
    portfolio_stock, created = PortfolioStock.objects.get_or_create(
        portfolio=portfolio,
        stock=stock,
        defaults={"amount": amount},
    )
    if not created:
        PortfolioStock.objects.filter(pk=portfolio_stock.pk).update(
            amount=F("amount") + amount
        )
        portfolio_stock.refresh_from_db()
    return portfolio_stock


def validate_portfolio_stock_add(sender, instance, reverse, pk_set, **kwargs):
    if not pk_set:
        return

    if reverse:
        valid_portfolio_ids = set(
            Portfolio.objects.filter(
                pk__in=pk_set,
                user__watchlists__stocks__id=instance.pk,
            ).values_list('pk', flat=True).distinct()
        )
        invalid_ids = set(pk_set) - valid_portfolio_ids
        if invalid_ids:
            raise ValidationError(
                'The stock must be in each portfolio owner’s watchlist.'
            )
        return

    valid_stock_ids = set(
        instance.user.watchlists.filter(
            stocks__id__in=pk_set,
        ).values_list('stocks__id', flat=True).distinct()
    )
    if set(pk_set) - valid_stock_ids:
        raise ValidationError(
            "Every stock in a portfolio must be in one of its owner's watchlists."
        )


m2m_changed.connect(
    validate_portfolio_stock_add,
    sender=Portfolio.stocks.through,
    dispatch_uid='validate_portfolio_stock_add',
)


def prune_unwatched_portfolio_stocks(user_id, stock_ids):
    if not stock_ids:
        return

    PortfolioStock.objects.filter(
        portfolio__user_id=user_id,
        stock_id__in=stock_ids,
    ).exclude(
        stock__watchlists__user_id=user_id,
    ).delete()


def clean_portfolio_stocks_after_watchlist_change(
    sender, instance, action, reverse, pk_set, **kwargs
):
    if action == 'pre_clear':
        if reverse:
            instance._portfolio_watchlists_before_clear = list(
                instance.watchlists.values_list('user_id', flat=True).distinct()
            )
        else:
            instance._portfolio_stocks_before_clear = set(
                instance.stocks.values_list('pk', flat=True)
            )
        return

    if action == 'post_remove':
        if reverse:
            user_ids = Watchlist.objects.filter(
                pk__in=pk_set or (),
            ).values_list('user_id', flat=True).distinct()
            for user_id in user_ids:
                prune_unwatched_portfolio_stocks(user_id, [instance.pk])
        else:
            prune_unwatched_portfolio_stocks(instance.user_id, pk_set)
        return

    if action != 'post_clear':
        return

    if reverse:
        user_ids = getattr(instance, '_portfolio_watchlists_before_clear', ())
        for user_id in user_ids:
            prune_unwatched_portfolio_stocks(user_id, [instance.pk])
        del instance._portfolio_watchlists_before_clear
    else:
        stock_ids = getattr(instance, '_portfolio_stocks_before_clear', ())
        prune_unwatched_portfolio_stocks(instance.user_id, stock_ids)
        del instance._portfolio_stocks_before_clear


def capture_watchlist_stocks_before_delete(sender, instance, **kwargs):
    instance._portfolio_stocks_before_delete = set(
        instance.stocks.values_list('pk', flat=True)
    )


def prune_portfolio_stocks_after_watchlist_delete(sender, instance, **kwargs):
    stock_ids = getattr(instance, '_portfolio_stocks_before_delete', ())
    prune_unwatched_portfolio_stocks(instance.user_id, stock_ids)


m2m_changed.connect(
    clean_portfolio_stocks_after_watchlist_change,
    sender=Watchlist.stocks.through,
    dispatch_uid='clean_portfolio_stocks_after_watchlist_change',
)
pre_delete.connect(
    capture_watchlist_stocks_before_delete,
    sender=Watchlist,
    dispatch_uid='capture_watchlist_stocks_before_delete',
)
post_delete.connect(
    prune_portfolio_stocks_after_watchlist_delete,
    sender=Watchlist,
    dispatch_uid='prune_portfolio_stocks_after_watchlist_delete',
)