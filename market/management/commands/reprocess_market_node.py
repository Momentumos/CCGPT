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
                # Use the linked MessageRequest from the node
                if node.message_request:
                    message_request = node.message_request
                    self.stdout.write(f"Using linked MessageRequest: {message_request.id} (Status: {message_request.status})")
                else:
                    self.stdout.write(self.style.ERROR(
                        f"Node '{node.title}' has no linked MessageRequest. Use --request-id to specify one."
                    ))
                    return
            
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
            original_response = message_request.response
            analysis_data, cleaned_json = service._parse_llm_response(message_request.response, return_cleaned_json=True)
            
            if not analysis_data:
                self.stdout.write(self.style.ERROR("Failed to parse response!"))
                self.stdout.write("Check the console output above for parsing errors.")
                return
            
            # Save cleaned JSON back to MessageRequest if it changed
            if cleaned_json and cleaned_json != original_response:
                message_request.response = cleaned_json
                message_request.save(update_fields=['response'])
                self.stdout.write(self.style.SUCCESS("✓ Saved cleaned JSON back to MessageRequest"))
            
            self.stdout.write(self.style.SUCCESS("✓ Successfully parsed response"))
            self.stdout.write(f"  Value Added: ${analysis_data.get('value_added_usd', 0):,}")
            self.stdout.write(f"  Employment: {analysis_data.get('employment_count', 0):,}")
            self.stdout.write(f"  Sub-markets: {len(analysis_data.get('sub_markets', []))}")
            
            # Add metadata
            from django.utils import timezone
            analysis_data['metadata'] = {
                'analysis_date': timezone.now().isoformat(),
                'llm_response': original_response,
                'chat_id': message_request.chat.chat_id if message_request.chat else None,
                'request_id': str(message_request.id),
                'manually_reprocessed': True
            }
            
            # Update the node
            self.stdout.write("\nUpdating node...")
            
            # If using a different MessageRequest, update the link first
            if request_id and (not node.message_request or str(node.message_request.id) != request_id):
                message_request_obj = MessageRequest.objects.get(id=request_id)
                node.message_request = message_request_obj
                node.save(update_fields=['message_request'])
                self.stdout.write(f"✓ Updated node's MessageRequest link to {request_id}")
            
            try:
                node.mark_completed(analysis_data)
                self.stdout.write(self.style.SUCCESS(f"✓ Node '{node.title}' marked as completed"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to mark node completed: {e}"))
                return
            
            # Create child nodes if not at max depth
            if node.level < 3:
                self.stdout.write("\nCreating child nodes...")
                
                # Check if children already exist
                existing_children = node.children.count()
                if existing_children > 0:
                    self.stdout.write(self.style.WARNING(f"Node already has {existing_children} child nodes. Skipping creation."))
                else:
                    try:
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
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Failed to create child nodes: {e}"))
            
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
            self.stdout.write(self.style.ERROR(f"Error: {type(e).__name__}: {e}"))
            import traceback
            traceback.print_exc()
