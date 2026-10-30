from django.core.management.base import BaseCommand, CommandError

from portfolios.services import (
    PortfolioSnapshotUnavailable,
    capture_daily_portfolio_snapshots,
)


class Command(BaseCommand):
    help = 'Capture the latest daily value for every portfolio.'

    def handle(self, *args, **options):
        try:
            count = capture_daily_portfolio_snapshots()
        except PortfolioSnapshotUnavailable as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(f'Captured values for {count} portfolios.')
        )
