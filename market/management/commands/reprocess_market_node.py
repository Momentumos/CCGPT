"""
Management command to reprocess a market node with a manually-fixed MessageRequest
"""
from django.core.management.base import BaseCommand
from market.models import MarketNode
from chat.models import MessageRequest
from market.services import MarketAnalysisService


class Command(BaseCommand):
    help = 'Reprocess a market node with a manually-fixed MessageRequest response'

    def add_arguments(self, parser):
        parser.add_argument(
            'node_id',
            type=str,
            help='The ID of the MarketNode to reprocess'
        )
        parser.add_argument(
            '--request-id',
            type=str,
            help='Optional: Specific MessageRequest ID to use (if multiple exist)'
        )

    def handle(self, *args, **options):
        node_id = options['node_id']
        request_id = options.get('request_id')
        
        try:
            # Get the node
            node = MarketNode.objects.get(id=node_id)
            self.stdout.write(f"Found node: {node.title} (Level {node.level}, Status: {node.status})")
            
            # Find the MessageRequest
            if request_id:
                message_request = MessageRequest.objects.get(id=request_id)
                self.stdout.write(f"Using specified MessageRequest: {message_request.id}")
            else:
                # Find the most recent DONE request for this node's chat
                # We'll look for requests with the node title in the message
                message_requests = MessageRequest.objects.filter(
                    status=MessageRequest.Status.DONE,
                    message__icontains=node.title
                ).order_by('-completed_at')
                
                if not message_requests.exists():
                    self.stdout.write(self.style.ERROR(
                        f"No DONE MessageRequest found for node '{node.title}'"
                    ))
                    return
                
                message_request = message_requests.first()
                self.stdout.write(f"Found MessageRequest: {message_request.id}")
            
            # Check if response exists
            if not message_request.response:
                self.stdout.write(self.style.ERROR("MessageRequest has no response!"))
                return
            
            self.stdout.write(f"Response length: {len(message_request.response)} chars")
            self.stdout.write(f"Response preview: {message_request.response[:200]}...")
            
            # Get the service
            service = MarketAnalysisService(message_request.account)
            
            # Parse the response
            self.stdout.write("\nParsing response...")
            analysis_data = service._parse_llm_response(message_request.response)
            
            if not analysis_data:
                self.stdout.write(self.style.ERROR("Failed to parse response!"))
                self.stdout.write("Check the console output above for parsing errors.")
                return
            
            self.stdout.write(self.style.SUCCESS("✓ Successfully parsed response"))
            self.stdout.write(f"  Value Added: ${analysis_data.get('value_added_usd', 0):,}")
            self.stdout.write(f"  Employment: {analysis_data.get('employment_count', 0):,}")
            self.stdout.write(f"  Sub-markets: {len(analysis_data.get('sub_markets', []))}")
            
            # Add metadata
            from django.utils import timezone
            analysis_data['metadata'] = {
                'analysis_date': timezone.now().isoformat(),
                'llm_response': message_request.response,
                'chat_id': message_request.chat.chat_id if message_request.chat else None,
                'request_id': str(message_request.id),
                'manually_reprocessed': True
            }
            
            # Update the node
            self.stdout.write("\nUpdating node...")
            node.mark_completed(analysis_data)
            self.stdout.write(self.style.SUCCESS(f"✓ Node '{node.title}' marked as completed"))
            
            # Create child nodes if not at max depth
            if node.level < 3:
                self.stdout.write("\nCreating child nodes...")
                children = node.create_child_nodes()
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(children)} child nodes"))
                
                for child in children:
                    self.stdout.write(f"  - {child.title}")
                
                # Update job total_nodes count
                job = node.jobs.first() or (node.parent.jobs.first() if node.parent else None)
                if job:
                    job.total_nodes += len(children)
                    job.save()
                    self.stdout.write(f"✓ Updated job total_nodes to {job.total_nodes}")
            
            # Update job completed count
            job = node.jobs.first() or (node.parent.jobs.first() if node.parent else None)
            if job:
                job.completed_nodes += 1
                job.save()
                self.stdout.write(f"✓ Updated job completed_nodes to {job.completed_nodes}")
            
            self.stdout.write(self.style.SUCCESS("\n✓ Reprocessing complete!"))
            
        except MarketNode.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"MarketNode with ID '{node_id}' not found"))
        except MessageRequest.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"MessageRequest with ID '{request_id}' not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            traceback.print_exc()
