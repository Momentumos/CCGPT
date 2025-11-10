"""
Management command to list stuck or failed market nodes
"""
from django.core.management.base import BaseCommand
from market.models import MarketNode
from chat.models import MessageRequest


class Command(BaseCommand):
    help = 'List market nodes that are stuck or failed'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("STUCK/FAILED MARKET NODES")
        self.stdout.write("=" * 80)
        self.stdout.write()
        
        # Find analyzing nodes
        analyzing_nodes = MarketNode.objects.filter(status=MarketNode.Status.ANALYZING)
        if analyzing_nodes.exists():
            self.stdout.write(self.style.WARNING(f"ANALYZING nodes ({analyzing_nodes.count()}):"))
            for node in analyzing_nodes:
                self.stdout.write(f"  ID: {node.id}")
                self.stdout.write(f"  Title: {node.title}")
                self.stdout.write(f"  Level: {node.level}")
                self.stdout.write(f"  Updated: {node.updated_at}")
                
                # Try to find associated MessageRequest
                requests = MessageRequest.objects.filter(
                    message__icontains=node.title
                ).order_by('-queued_at')[:3]
                
                if requests.exists():
                    self.stdout.write(f"  Recent MessageRequests:")
                    for req in requests:
                        self.stdout.write(f"    - {req.id}: {req.status} (queued: {req.queued_at})")
                        if req.status == MessageRequest.Status.DONE and req.response:
                            self.stdout.write(f"      ✓ Has response ({len(req.response)} chars)")
                            self.stdout.write(self.style.SUCCESS(
                                f"      → Can reprocess with: python manage.py reprocess_market_node {node.id} --request-id {req.id}"
                            ))
                
                self.stdout.write()
        
        # Find failed nodes
        failed_nodes = MarketNode.objects.filter(status=MarketNode.Status.FAILED)
        if failed_nodes.exists():
            self.stdout.write(self.style.ERROR(f"FAILED nodes ({failed_nodes.count()}):"))
            for node in failed_nodes:
                self.stdout.write(f"  ID: {node.id}")
                self.stdout.write(f"  Title: {node.title}")
                self.stdout.write(f"  Level: {node.level}")
                self.stdout.write(f"  Updated: {node.updated_at}")
                
                # Try to find associated MessageRequest
                requests = MessageRequest.objects.filter(
                    message__icontains=node.title
                ).order_by('-queued_at')[:3]
                
                if requests.exists():
                    self.stdout.write(f"  Recent MessageRequests:")
                    for req in requests:
                        self.stdout.write(f"    - {req.id}: {req.status}")
                        if req.status == MessageRequest.Status.DONE and req.response:
                            self.stdout.write(f"      ✓ Has response ({len(req.response)} chars)")
                            self.stdout.write(self.style.SUCCESS(
                                f"      → Can reprocess with: python manage.py reprocess_market_node {node.id} --request-id {req.id}"
                            ))
                        elif req.status == MessageRequest.Status.FAILED:
                            self.stdout.write(f"      ✗ Failed: {req.error_message}")
                
                self.stdout.write()
        
        # Find pending nodes (might be stuck)
        pending_nodes = MarketNode.objects.filter(status=MarketNode.Status.PENDING)
        if pending_nodes.exists():
            self.stdout.write(f"PENDING nodes ({pending_nodes.count()}):")
            self.stdout.write("  (These are waiting to be processed)")
            for node in pending_nodes[:10]:  # Show first 10
                self.stdout.write(f"  - {node.title} (Level {node.level})")
            if pending_nodes.count() > 10:
                self.stdout.write(f"  ... and {pending_nodes.count() - 10} more")
            self.stdout.write()
        
        if not analyzing_nodes.exists() and not failed_nodes.exists():
            self.stdout.write(self.style.SUCCESS("✓ No stuck or failed nodes found!"))
