"""
Management command to list all market analysis jobs
"""
from django.core.management.base import BaseCommand
from market.models import MarketAnalysisJob, MarketNode


class Command(BaseCommand):
    help = 'List all market analysis jobs and their status'

    def handle(self, *args, **options):
        jobs = MarketAnalysisJob.objects.all().order_by('-created_at')
        
        if not jobs.exists():
            self.stdout.write("No jobs found.")
            return
        
        self.stdout.write("=" * 80)
        self.stdout.write("MARKET ANALYSIS JOBS")
        self.stdout.write("=" * 80)
        self.stdout.write()
        
        for job in jobs:
            # Get descendant IDs
            descendant_ids = self._get_descendant_ids(job.root_node)
            
            # Count nodes by status
            pending = MarketNode.objects.filter(
                id__in=descendant_ids,
                status=MarketNode.Status.PENDING
            ).count()
            
            analyzing = MarketNode.objects.filter(
                id__in=descendant_ids,
                status=MarketNode.Status.ANALYZING
            ).count()
            
            completed = MarketNode.objects.filter(
                id__in=descendant_ids,
                status=MarketNode.Status.COMPLETED
            ).count()
            
            failed = MarketNode.objects.filter(
                id__in=descendant_ids,
                status=MarketNode.Status.FAILED
            ).count()
            
            total = pending + analyzing + completed + failed
            
            # Display job info
            status_style = {
                'pending': self.style.WARNING,
                'running': self.style.HTTP_INFO,
                'completed': self.style.SUCCESS,
                'failed': self.style.ERROR,
            }
            
            style_func = status_style.get(job.status, lambda x: x)
            
            self.stdout.write(f"Job ID: {job.id}")
            self.stdout.write(f"  Root: {job.root_node.title}")
            self.stdout.write(f"  Status: {style_func(job.status.upper())}")
            self.stdout.write(f"  Created: {job.created_at}")
            if job.started_at:
                self.stdout.write(f"  Started: {job.started_at}")
            if job.completed_at:
                self.stdout.write(f"  Completed: {job.completed_at}")
            
            self.stdout.write(f"  Progress: {completed}/{total} nodes completed")
            self.stdout.write(f"    ✓ Completed: {completed}")
            self.stdout.write(f"    ⏳ Analyzing: {analyzing}")
            self.stdout.write(f"    ⏸ Pending: {pending}")
            self.stdout.write(f"    ✗ Failed: {failed}")
            
            # Suggest actions
            if job.status == 'running' and pending > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"  → Resume with: python manage.py resume_job {job.id}"
                ))
            elif analyzing > 0:
                self.stdout.write(self.style.WARNING(
                    f"  → Check stuck nodes: python manage.py list_stuck_nodes"
                ))
            elif job.status != 'completed' and pending == 0 and analyzing == 0:
                self.stdout.write(self.style.SUCCESS(
                    f"  → Mark as complete: python manage.py resume_job {job.id}"
                ))
            
            self.stdout.write()
    
    def _get_descendant_ids(self, node):
        """Get all descendant node IDs recursively"""
        ids = [node.id]
        for child in node.children.all():
            ids.extend(self._get_descendant_ids(child))
        return ids
