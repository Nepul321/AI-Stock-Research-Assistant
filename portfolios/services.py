import logging
from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation

from finnhub.exceptions import FinnhubAPIException
from django.db import transaction
from django.utils import timezone

from base.api.main import FinnhubService

from .models import Portfolio, PortfolioValueSnapshot

logger = logging.getLogger(__name__)

SNAPSHOT_PRICE_LOOKBACK_DAYS = 30


class PortfolioSnapshotUnavailable(Exception):
    pass


def _daily_closes_by_date(symbol, candles):
    if not isinstance(candles, dict) or candles.get('s') != 'ok':
        raise PortfolioSnapshotUnavailable(
            f'Historical closing prices are unavailable for {symbol}.'
        )

    timestamps = candles.get('t')
    closes = candles.get('c')
    if (
        not isinstance(timestamps, (list, tuple))
        or not isinstance(closes, (list, tuple))
        or not timestamps
        or len(timestamps) != len(closes)
    ):
        raise PortfolioSnapshotUnavailable(
            f'Historical closing prices are incomplete for {symbol}.'
        )

    daily_closes = {}
    try:
        for timestamp, close in zip(timestamps, closes):
            date = datetime.fromtimestamp(
                int(timestamp),
                tz=datetime_timezone.utc,
            ).date()
            price = Decimal(str(close))
            if not price.is_finite() or price < 0:
                raise InvalidOperation
            daily_closes[date] = price
    except (InvalidOperation, TypeError, ValueError, OverflowError, OSError) as exc:
        raise PortfolioSnapshotUnavailable(
            f'Historical closing prices are invalid for {symbol}.'
        ) from exc

    return daily_closes


def _current_price(symbol, quote):
    try:
        price = Decimal(str(quote.get('c')))
        if not price.is_finite() or price < 0:
            raise InvalidOperation
    except (AttributeError, InvalidOperation, TypeError, ValueError) as exc:
        raise PortfolioSnapshotUnavailable(
            f'A current price is unavailable for {symbol}.'
        ) from exc

    return price


def capture_daily_portfolio_snapshots():
    portfolios = list(
        Portfolio.objects.prefetch_related('portfolio_stocks__stock')
    )
    if not portfolios:
        return 0

    holdings_by_portfolio = {
        portfolio.pk: list(portfolio.portfolio_stocks.all())
        for portfolio in portfolios
    }
    stocks = {
        holding.stock_id: holding.stock
        for holdings in holdings_by_portfolio.values()
        for holding in holdings
    }

    closes_by_stock = {}
    use_current_quotes = False
    if stocks:
        try:
            finnhub = FinnhubService()
        except Exception as exc:
            logger.exception(
                'Failed to initialize Finnhub for portfolio snapshots'
            )
            raise PortfolioSnapshotUnavailable(
                'Market prices are unavailable. Please try again later.'
            ) from exc

        for stock_id, stock in stocks.items():
            try:
                candles = finnhub.get_stock_candles(
                    stock.symbol,
                    days=SNAPSHOT_PRICE_LOOKBACK_DAYS,
                )
                closes_by_stock[stock_id] = _daily_closes_by_date(
                    stock.symbol,
                    candles,
                )
            except FinnhubAPIException as exc:
                if exc.status_code != 403:
                    logger.exception(
                        'Finnhub rejected historical prices for %s',
                        stock.symbol,
                    )
                    raise PortfolioSnapshotUnavailable(
                        f'Historical prices are unavailable for {stock.symbol}.'
                    ) from exc

                logger.warning(
                    'Finnhub denied historical candles for %s; '
                    'using current quotes for this snapshot',
                    stock.symbol,
                )
                use_current_quotes = True
                break
            except PortfolioSnapshotUnavailable:
                raise
            except Exception as exc:
                logger.exception(
                    'Failed to retrieve historical prices for %s',
                    stock.symbol,
                )
                raise PortfolioSnapshotUnavailable(
                    f'Historical prices are unavailable for {stock.symbol}.'
                ) from exc

        prices_by_stock = {}
        if use_current_quotes:
            for stock_id, stock in stocks.items():
                try:
                    quote = finnhub.get_stock_quote(stock.symbol) or {}
                    prices_by_stock[stock_id] = _current_price(
                        stock.symbol,
                        quote,
                    )
                except PortfolioSnapshotUnavailable:
                    raise
                except Exception as exc:
                    logger.exception(
                        'Failed to retrieve current quote for %s',
                        stock.symbol,
                    )
                    raise PortfolioSnapshotUnavailable(
                        f'A current price is unavailable for {stock.symbol}.'
                    ) from exc

    snapshots = []
    today = timezone.localdate()
    for portfolio in portfolios:
        holdings = holdings_by_portfolio[portfolio.pk]
        if not holdings:
            snapshot_date = today
            total = Decimal('0')
        elif use_current_quotes:
            snapshot_date = today
            total = sum(
                (
                    holding.amount * prices_by_stock[holding.stock_id]
                    for holding in holdings
                ),
                Decimal('0'),
            )
        else:
            common_dates = set(closes_by_stock[holdings[0].stock_id])
            for holding in holdings[1:]:
                common_dates.intersection_update(
                    closes_by_stock[holding.stock_id]
                )
            if not common_dates:
                raise PortfolioSnapshotUnavailable(
                    'No common trading date has complete prices for '
                    f'portfolio "{portfolio.name}".'
                )

            snapshot_date = max(common_dates)
            total = sum(
                (
                    holding.amount
                    * closes_by_stock[holding.stock_id][snapshot_date]
                    for holding in holdings
                ),
                Decimal('0'),
            )

        snapshots.append(
            PortfolioValueSnapshot(
                portfolio=portfolio,
                date=snapshot_date,
                value=total,
                currency='USD',
            )
        )

    with transaction.atomic():
        for snapshot in snapshots:
            PortfolioValueSnapshot.objects.update_or_create(
                portfolio=snapshot.portfolio,
                date=snapshot.date,
                defaults={
                    'value': snapshot.value,
                    'currency': snapshot.currency,
                },
            )

    return len(snapshots)
