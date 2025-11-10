"""
Management command to resume a market analysis job
"""
from django.core.management.base import BaseCommand
from market.models import MarketAnalysisJob, MarketNode
from market.services import MarketAnalysisService


class Command(BaseCommand):
    help = 'Resume a market analysis job that was interrupted'

    def add_arguments(self, parser):
        parser.add_argument(
            'job_id',
            type=str,
            help='The ID of the MarketAnalysisJob to resume'
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Also retry failed nodes (reset them to pending)'
        )

    def handle(self, *args, **options):
        job_id = options['job_id']
        retry_failed = options.get('retry_failed', False)
        
        try:
            # Get the job
            job = MarketAnalysisJob.objects.get(id=job_id)
            self.stdout.write(f"Found job: {job.id}")
            self.stdout.write(f"  Root node: {job.root_node.title}")
            self.stdout.write(f"  Status: {job.status}")
            self.stdout.write(f"  Progress: {job.completed_nodes}/{job.total_nodes} nodes")
            if retry_failed:
                self.stdout.write(f"  Mode: Retry failed nodes")
            self.stdout.write()
            
            # Check current state
            pending_count = MarketNode.objects.filter(
                id__in=self._get_descendant_ids(job.root_node),
                status=MarketNode.Status.PENDING
            ).count()
            
            analyzing_count = MarketNode.objects.filter(
                id__in=self._get_descendant_ids(job.root_node),
                status=MarketNode.Status.ANALYZING
            ).count()
            
            completed_count = MarketNode.objects.filter(
                id__in=self._get_descendant_ids(job.root_node),
                status=MarketNode.Status.COMPLETED
            ).count()
            
            failed_count = MarketNode.objects.filter(
                id__in=self._get_descendant_ids(job.root_node),
                status=MarketNode.Status.FAILED
            ).count()
            
            self.stdout.write("Current state:")
            self.stdout.write(f"  ✓ Completed: {completed_count}")
            self.stdout.write(f"  ⏳ Analyzing: {analyzing_count}")
            self.stdout.write(f"  ⏸ Pending: {pending_count}")
            self.stdout.write(f"  ✗ Failed: {failed_count}")
            self.stdout.write()
            
            if analyzing_count > 0:
                self.stdout.write(self.style.WARNING(
                    f"Warning: {analyzing_count} nodes are currently analyzing."
                ))
                self.stdout.write("These may be stuck. Run 'python manage.py list_stuck_nodes' to check.")
                self.stdout.write()
            
            # Reset failed nodes to pending if requested
            if retry_failed and failed_count > 0:
                self.stdout.write(self.style.WARNING(f"Resetting {failed_count} failed nodes to pending..."))
                failed_nodes = MarketNode.objects.filter(
                    id__in=self._get_descendant_ids(job.root_node),
                    status=MarketNode.Status.FAILED
                )
                for node in failed_nodes:
                    node.status = MarketNode.Status.PENDING
                    node.save()
                    self.stdout.write(f"  ↻ Reset: {node.title}")
                
                # Update counts
                pending_count += failed_count
                failed_count = 0
                self.stdout.write(self.style.SUCCESS(f"✓ Reset complete. Now {pending_count} pending nodes."))
                self.stdout.write()
            
            if pending_count == 0:
                self.stdout.write(self.style.SUCCESS("✓ No pending nodes. Job is complete or all nodes are processing."))
                
                if job.status != MarketAnalysisJob.Status.COMPLETED:
                    job.status = MarketAnalysisJob.Status.COMPLETED
                    from django.utils import timezone
                    job.completed_at = timezone.now()
                    job.save()
                    self.stdout.write(self.style.SUCCESS("✓ Marked job as completed"))
                
                return
            
            # Resume processing
            self.stdout.write(self.style.SUCCESS(f"Resuming job with {pending_count} pending nodes..."))
            self.stdout.write()
            
            # Get the service
            service = MarketAnalysisService(job.root_node.account)
            
            # Set job to running if not already
            if job.status != MarketAnalysisJob.Status.RUNNING:
                job.status = MarketAnalysisJob.Status.RUNNING
                from django.utils import timezone
                if not job.started_at:
                    job.started_at = timezone.now()
                job.save()
            
            # Process remaining levels
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            for level in range(1, 4):  # Levels 1, 2, 3
                # Collect all pending nodes at this level
                nodes_at_level = MarketNode.objects.filter(
                    level=level,
                    status=MarketNode.Status.PENDING,
                    id__in=service._get_descendant_ids(job.root_node)
                )
                
                node_count = nodes_at_level.count()
                if node_count == 0:
                    # Check if level is fully completed
                    all_nodes_at_level = MarketNode.objects.filter(
                        level=level,
                        id__in=service._get_descendant_ids(job.root_node)
                    )
                    
                    if all_nodes_at_level.exists():
                        incomplete = all_nodes_at_level.exclude(status=MarketNode.Status.COMPLETED).count()
                        if incomplete > 0:
                            self.stdout.write(self.style.ERROR(
                                f"Level {level} has {incomplete} incomplete nodes. Cannot proceed to next level."
                            ))
                            self.stdout.write("Run 'python manage.py list_stuck_nodes' to investigate.")
                            break
                        self.stdout.write(self.style.SUCCESS(f"Level {level} fully completed, moving to next level"))
                    continue
                
                self.stdout.write(f"Processing {node_count} nodes at level {level} in parallel...")
                
                # Process all nodes at this level in parallel
                with ThreadPoolExecutor(max_workers=min(node_count, 10)) as executor:
                    # Submit all tasks
                    future_to_node = {
                        executor.submit(service._analyze_node, node): node 
                        for node in nodes_at_level
                    }
                    
                    # Wait for all to complete
                    completed = 0
                    failed = 0
                    for future in as_completed(future_to_node):
                        node = future_to_node[future]
                        try:
                            future.result()
                            completed += 1
                            self.stdout.write(f"  Level {level}: {completed}/{node_count} completed")
                        except Exception as e:
                            failed += 1
                            self.stdout.write(self.style.ERROR(f"  Error analyzing {node.title}: {e}"))
                
                self.stdout.write(f"Level {level} batch complete: {completed} successful, {failed} failed")
                
                # Verify ALL nodes at this level are completed before moving to next level
                all_nodes_at_level = MarketNode.objects.filter(
                    level=level,
                    id__in=service._get_descendant_ids(job.root_node)
                )
                
                total_at_level = all_nodes_at_level.count()
                completed_at_level = all_nodes_at_level.filter(status=MarketNode.Status.COMPLETED).count()
                failed_at_level = all_nodes_at_level.filter(status=MarketNode.Status.FAILED).count()
                analyzing_at_level = all_nodes_at_level.filter(status=MarketNode.Status.ANALYZING).count()
                pending_at_level = all_nodes_at_level.filter(status=MarketNode.Status.PENDING).count()
                
                self.stdout.write(f"Level {level} final status:")
                self.stdout.write(f"  Total: {total_at_level}")
                self.stdout.write(f"  ✓ Completed: {completed_at_level}")
                self.stdout.write(f"  ✗ Failed: {failed_at_level}")
                self.stdout.write(f"  ⏳ Analyzing: {analyzing_at_level}")
                self.stdout.write(f"  ⏸ Pending: {pending_at_level}")
                
                if completed_at_level < total_at_level:
                    incomplete_count = total_at_level - completed_at_level
                    self.stdout.write(self.style.ERROR(
                        f"Level {level} is NOT fully completed ({incomplete_count} incomplete nodes)"
                    ))
                    self.stdout.write("Stopping job. Fix incomplete nodes and resume with:")
                    self.stdout.write(f"  python manage.py resume_job {job.id}")
                    if failed_at_level > 0:
                        self.stdout.write(f"  python manage.py resume_job {job.id} --retry-failed")
                    job.status = MarketAnalysisJob.Status.RUNNING  # Keep as running
                    job.save()
                    return  # Stop, don't move to next level
                
                self.stdout.write(self.style.SUCCESS(f"Level {level} fully completed, proceeding to next level"))
                self.stdout.write()
            
            # Update job status
            job.status = MarketAnalysisJob.Status.COMPLETED
            from django.utils import timezone
            job.completed_at = timezone.now()
            job.save()
            
            self.stdout.write(self.style.SUCCESS("✓ Job completed successfully!"))
            
        except MarketAnalysisJob.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"MarketAnalysisJob with ID '{job_id}' not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            traceback.print_exc()
    
    def _get_descendant_ids(self, node):
        """Get all descendant node IDs recursively"""
        ids = [node.id]
        for child in node.children.all():
            ids.extend(self._get_descendant_ids(child))
        return ids
