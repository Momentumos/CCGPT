from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from market.models import MarketNode


class Command(BaseCommand):
    help = 'Set all level-3 market nodes to COMPLETED'

    def add_arguments(self, parser):
        parser.add_argument(
            '--account-id',
            type=int,
            help='Optional: only update nodes belonging to this account id',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many nodes would be updated without changing anything',
        )

    def handle(self, *args, **options):
        account_id = options.get('account_id')
        dry_run = options.get('dry_run', False)

        qs = MarketNode.objects.filter(level=3)
        if account_id is not None:
            qs = qs.filter(account_id=account_id)

        to_update = qs.filter(
            Q(status__in=[MarketNode.Status.PENDING, MarketNode.Status.ANALYZING, MarketNode.Status.FAILED])
            | Q(analyzed_at__isnull=True)
        )

        count = to_update.count()
        self.stdout.write(f"Level-3 nodes matched for update: {count}")

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run mode: no changes applied.'))
            return

        now = timezone.now()
        updated = to_update.update(status=MarketNode.Status.COMPLETED, analyzed_at=now)
        self.stdout.write(self.style.SUCCESS(f"Updated level-3 nodes: {updated}"))
