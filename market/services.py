"""
Market Analysis Service
Handles recursive market segmentation using the existing chat/LLM system
"""
import json
import time
import os
from pathlib import Path
from django.utils import timezone
from chat.models import MessageRequest, Chat
from .models import MarketNode, MarketAnalysisJob


def load_market_prompt():
    """Load the market segmentation prompt from file"""
    prompt_path = Path(__file__).parent / 'prompts' / 'market_segmentation_prompt.md'
    with open(prompt_path, 'r') as f:
        content = f.read()
    # Extract the actual prompt (skip the markdown header)
    if content.startswith('# Instruction prompt'):
        content = content.split('\n', 2)[2]  # Skip first two lines
    return content.strip()


# Load the prompt template once at module level
MARKET_ANALYSIS_PROMPT_TEMPLATE = load_market_prompt()


class MarketAnalysisService:
    """Service for managing recursive market analysis"""
    
    def __init__(self, account):
        self.account = account
    
    def start_analysis(self, market_titles, max_depth=2):
        """
        Start analysis for multiple root markets
        Returns list of created jobs
        """
        jobs = []
        
        for title in market_titles:
            # Create root node
            root_node = MarketNode.objects.create(
                account=self.account,
                title=title,
                level=0,
                status=MarketNode.Status.PENDING,
                data={
                    'value_added_usd': 0,  # Will be filled by LLM
                    'employment_count': 0,  # Will be filled by LLM
                }
            )
            
            # Create job
            job = MarketAnalysisJob.objects.create(
                account=self.account,
                root_node=root_node,
                status=MarketAnalysisJob.Status.PENDING,
                total_nodes=1  # Will be updated as we discover more nodes
            )
            
            jobs.append(job)
        
        return jobs
    
    def process_job(self, job):
        """
        Process a market analysis job recursively with parallel processing per level
        This should be called asynchronously or in a background task
        """
        from django.utils import timezone
        from django.conf import settings
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        job.status = MarketAnalysisJob.Status.RUNNING
        job.started_at = timezone.now()
        job.save()
        
        try:
            # Process root node (level 0)
            print(f"[Job {job.id}] Starting root node analysis...")
            self._analyze_node(job.root_node, is_root=True)
            
            # Process each level in parallel
            for level in range(1, 4):  # Levels 1, 2, 3
                # Collect all nodes at this level
                nodes_at_level = MarketNode.objects.filter(
                    level=level,
                    status=MarketNode.Status.PENDING
                ).filter(
                    # Only nodes that belong to this job's tree
                    id__in=self._get_descendant_ids(job.root_node)
                )
                
                node_count = nodes_at_level.count()
                if node_count == 0:
                    print(f"[Job {job.id}] No pending nodes at level {level}, checking completion...")
                    
                    # Verify all nodes at this level are completed
                    all_nodes_at_level = MarketNode.objects.filter(
                        level=level,
                        id__in=self._get_descendant_ids(job.root_node)
                    )
                    
                    incomplete = all_nodes_at_level.exclude(status=MarketNode.Status.COMPLETED).count()
                    if incomplete > 0:
                        print(f"[Job {job.id}] ✗ Level {level} has {incomplete} incomplete nodes. Cannot proceed to next level.")
                        print(f"[Job {job.id}] Run 'python manage.py list_stuck_nodes' to investigate.")
                        break
                    
                    print(f"[Job {job.id}] ✓ Level {level} fully completed, moving to next level")
                    continue
                
                print(f"[Job {job.id}] Processing {node_count} nodes at level {level} in parallel...")
                
                # Process all nodes at this level in parallel
                max_workers = min(node_count, max(1, getattr(settings, 'MARKET_ANALYSIS_MAX_WORKERS', 3)))
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all tasks
                    future_to_node = {
                        executor.submit(self._analyze_node, node): node 
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
                            print(f"[Job {job.id}] Level {level}: {completed}/{node_count} completed")
                        except Exception as e:
                            failed += 1
                            print(f"[Job {job.id}] ✗ Error analyzing {node.title}: {e}")
                
                print(f"[Job {job.id}] Level {level} batch complete: {completed} successful, {failed} failed")
                
                # Verify ALL nodes at this level are now completed before moving to next level
                all_nodes_at_level = MarketNode.objects.filter(
                    level=level,
                    id__in=self._get_descendant_ids(job.root_node)
                )
                
                total_at_level = all_nodes_at_level.count()
                completed_at_level = all_nodes_at_level.filter(status=MarketNode.Status.COMPLETED).count()
                failed_at_level = all_nodes_at_level.filter(status=MarketNode.Status.FAILED).count()
                analyzing_at_level = all_nodes_at_level.filter(status=MarketNode.Status.ANALYZING).count()
                pending_at_level = all_nodes_at_level.filter(status=MarketNode.Status.PENDING).count()
                
                print(f"[Job {job.id}] Level {level} final status:")
                print(f"  Total: {total_at_level}")
                print(f"  ✓ Completed: {completed_at_level}")
                print(f"  ✗ Failed: {failed_at_level}")
                print(f"  ⏳ Analyzing: {analyzing_at_level}")
                print(f"  ⏸ Pending: {pending_at_level}")
                
                if completed_at_level < total_at_level:
                    incomplete_count = total_at_level - completed_at_level
                    print(f"[Job {job.id}] ✗ Level {level} is NOT fully completed ({incomplete_count} incomplete nodes)")
                    print(f"[Job {job.id}] Stopping job. Fix incomplete nodes and resume with:")
                    print(f"[Job {job.id}]   python manage.py resume_job {job.id}")
                    if failed_at_level > 0:
                        print(f"[Job {job.id}]   python manage.py resume_job {job.id} --retry-failed")
                    job.status = MarketAnalysisJob.Status.RUNNING  # Keep as running, not failed
                    job.save()
                    return  # Stop processing, don't move to next level
                
                print(f"[Job {job.id}] ✓ Level {level} fully completed, proceeding to next level")
            
            # Update job status
            job.status = MarketAnalysisJob.Status.COMPLETED
            job.completed_at = timezone.now()
            job.save()
            print(f"[Job {job.id}] ✓ Job completed successfully")
            
        except Exception as e:
            job.status = MarketAnalysisJob.Status.FAILED
            job.completed_at = timezone.now()
            job.save()
            print(f"[Job {job.id}] ✗ Job failed: {e}")
            raise e
    
    def _get_descendant_ids(self, node):
        """
        Get all descendant node IDs recursively
        """
        ids = [node.id]
        for child in node.children.all():
            ids.extend(self._get_descendant_ids(child))
        return ids
    
    def _analyze_node(self, node, is_root=False, max_retries=3):
        """
        Analyze a single node by creating a chat request and waiting for response
        Includes retry logic with exponential backoff
        """
        node.mark_analyzing()
        
        # Build hierarchy context
        lineage = []
        current = node.parent
        while current:
            lineage.insert(0, current.title)
            current = current.parent
        
        # Get siblings if not root
        siblings = []
        if node.parent:
            siblings = [s.title for s in node.parent.children.exclude(id=node.id)]
        
        # Prepare input JSON for the prompt
        if is_root:
            # For root nodes, ask LLM to determine total market size first
            # Add lineage with the node itself
            lineage_with_self = lineage + [node.title]
            
            input_json = {
                "hierarchy_context": {
                    "lineage": lineage_with_self,
                    "siblings": siblings,
                    "level_index": node.level
                },
                "node": {
                    "name": node.title,
                    "definition": f"The {node.title} encompasses all economic activity related to this market segment.",
                    "value_added_usd": 0,  # LLM will determine
                    "employment": 0,  # LLM will determine
                    "year": timezone.now().year,
                    "units": "USD_current_value_added"
                },
                "constraints": {
                    "min_children": 10,
                    "max_children": 18,
                    "min_child_share_of_parent": 0.03,
                    "allow_other_bucket": True,
                    "max_other_share": 0.05,
                    "rounding": {
                        "value_round_to_nearest": 1000000,
                        "employment_round_to_nearest": 10
                    }
                }
            }
            
            prompt = f"""{MARKET_ANALYSIS_PROMPT_TEMPLATE}

INPUT
You are given a JSON input describing the current node and constraints:

{json.dumps(input_json, indent=2)}

IMPORTANT FOR ROOT NODE:
Since this is a root-level market node (value_added_usd and employment are currently 0), you MUST:
1. First estimate the TOTAL market size for "{node.title}" in current USD (VALUE ADDED, not revenue) for year {timezone.now().year}
2. Estimate the TOTAL employment for this market
3. Then partition it into {input_json['constraints']['min_children']}-{input_json['constraints']['max_children']} sub-markets
4. Ensure the parent.value_added_usd and parent.employment in your output reflect your estimates (NOT zero)
5. Ensure all children sum exactly to these parent totals"""
        else:
            # For child nodes, use parent's allocated values
            parent_value = node.data.get('value_added_usd', 0)
            parent_employment = node.data.get('employment_count', 0)
            
            # Get definition from parent's sub_markets if available
            node_definition = f"A sub-segment of {node.parent.title if node.parent else 'the parent market'}."
            if node.parent and 'sub_markets' in node.parent.data:
                for sm in node.parent.data['sub_markets']:
                    if sm.get('name') == node.title:
                        if 'definition' in sm:
                            if isinstance(sm['definition'], dict):
                                node_definition = sm['definition'].get('includes', node_definition)
                            else:
                                node_definition = sm['definition']
                        break
            
            # Add lineage with the node itself
            lineage_with_self = lineage + [node.title]
            
            input_json = {
                "hierarchy_context": {
                    "lineage": lineage_with_self,
                    "siblings": siblings,
                    "level_index": node.level
                },
                "node": {
                    "name": node.title,
                    "definition": node_definition,
                    "value_added_usd": parent_value,
                    "employment": parent_employment,
                    "year": timezone.now().year,
                    "units": "USD_current_value_added"
                },
                "constraints": {
                    "min_children": 10,
                    "max_children": 18,
                    "min_child_share_of_parent": 0.03,
                    "allow_other_bucket": True,
                    "max_other_share": 0.05,
                    "rounding": {
                        "value_round_to_nearest": 1000000,
                        "employment_round_to_nearest": 10
                    }
                }
            }
            
            prompt = f"""{MARKET_ANALYSIS_PROMPT_TEMPLATE}

INPUT
You are given a JSON input describing the current node and constraints:

{json.dumps(input_json, indent=2)}"""
        
        # Check if node already has a MessageRequest (retry scenario)
        if node.message_request:
            message_request = node.message_request
            chat = message_request.chat
            
            # If the existing request is FAILED or stuck, we can retry
            if message_request.status in [MessageRequest.Status.FAILED, MessageRequest.Status.IDLE]:
                print(f"[Market Analysis] Retrying node '{node.title}' (Level {node.level}) - Retry #{node.retry_count + 1}")
                node.retry_count += 1
                node.save(update_fields=['retry_count'])
                
                # Check if we've exceeded max retries
                if node.retry_count > max_retries:
                    print(f"[Market Analysis] ✗ Max retries ({max_retries}) exceeded for '{node.title}'")
                    node.mark_failed()
                    return False
                
                # Reset the message request to IDLE so it can be picked up again
                message_request.status = MessageRequest.Status.IDLE
                message_request.error_message = None
                message_request.save(update_fields=['status', 'error_message'])
            elif message_request.status == MessageRequest.Status.DONE:
                print(f"[Market Analysis] Node '{node.title}' already has completed MessageRequest, skipping")
                return True
            else:
                print(f"[Market Analysis] Resuming existing request for '{node.title}' (Status: {message_request.status})")
        else:
            # Create new chat and submit message
            chat = Chat.objects.create(account=self.account)
            
            message_request = MessageRequest.objects.create(
                account=self.account,
                chat=chat,
                message=prompt,
                response_type=MessageRequest.ResponseType.THINKING,
                thinking_time=MessageRequest.ThinkingTime.EXTENDED
            )
            
            # Link the MessageRequest to the node
            node.message_request = message_request
            node.save(update_fields=['message_request'])
            
            print(f"[Market Analysis] Started analysis for '{node.title}' (Level {node.level}) - Request ID: {message_request.id}")
        
        # Broadcast to browser extension via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"account_{self.account.id}",
            {
                "type": "new_message_request",
                "request_id": str(message_request.id),
                "message": message_request.message,
                "response_type": message_request.response_type,
                "thinking_time": message_request.thinking_time,
                "chat_id": chat.chat_id if chat else None,
                "chat_db_id": chat.id if chat else None,
            }
        )
        print(f"[Market Analysis] Broadcasted request to WebSocket for account {self.account.id}")
        
        # Wait for response (poll until done)
        # No timeout - extended thinking can take a very long time
        # We rely on the MessageRequest status to determine completion
        
        poll_count = 0
        while True:
            message_request.refresh_from_db()
            poll_count += 1
            
            # Log every 12 polls (1 minute at 5-second intervals)
            if poll_count % 12 == 0:
                elapsed_minutes = (poll_count * 5) / 60
                print(f"[Market Analysis] Still waiting for {node.title} (Level {node.level}) - {elapsed_minutes:.1f} minutes elapsed, status: {message_request.status}")
            
            if message_request.status == MessageRequest.Status.DONE:
                elapsed_time = (poll_count * 5) / 60
                print(f"[Market Analysis] ✓ Completed '{node.title}' (Level {node.level}) in {elapsed_time:.1f} minutes")
                
                # Parse response
                response_text = message_request.response
                analysis_data, cleaned_json = self._parse_llm_response(response_text, return_cleaned_json=True)
                
                if analysis_data:
                    # Save cleaned JSON back to MessageRequest
                    if cleaned_json and cleaned_json != response_text:
                        message_request.response = cleaned_json
                        message_request.save(update_fields=['response'])
                        print(f"[Market Analysis] ✓ Saved cleaned JSON back to MessageRequest")
                    # Add metadata
                    analysis_data['metadata'] = {
                        'analysis_date': timezone.now().isoformat(),
                        'llm_response': response_text,
                        'chat_id': chat.chat_id,
                        'request_id': str(message_request.id)
                    }
                    
                    # Update node with validation
                    try:
                        node.mark_completed(analysis_data)
                        print(f"[Market Analysis] ✓ Node '{node.title}' marked as completed")
                    except Exception as e:
                        print(f"[Market Analysis] ✗ Failed to mark node completed: {e}")
                        node.mark_failed()
                        return False
                    
                    # Create child nodes if not at max depth
                    if node.level < 3:
                        try:
                            children = node.create_child_nodes()
                            print(f"[Market Analysis] Created {len(children)} child nodes for '{node.title}'")
                            
                            # Update job total_nodes count
                            job = node.jobs.first() or node.parent.jobs.first() if node.parent else None
                            if job:
                                job.total_nodes += len(children)
                                # If we auto-completed level-3 leaf nodes, count them as completed too
                                auto_completed = sum(
                                    1 for child in children
                                    if child.level >= 3 and child.status == MarketNode.Status.COMPLETED
                                )
                                if auto_completed:
                                    job.completed_nodes += auto_completed
                                job.save(update_fields=['total_nodes', 'completed_nodes'])
                        except Exception as e:
                            print(f"[Market Analysis] ✗ Failed to create child nodes: {e}")
                            # Don't fail the node, it's already completed
                    
                    # Update job completed count
                    job = node.jobs.first() or (node.parent.jobs.first() if node.parent else None)
                    if job:
                        job.completed_nodes += 1
                        job.save()
                    
                    return True
                else:
                    print(f"[Market Analysis] ✗ Failed to parse response for '{node.title}'")
                    node.mark_failed()
                    return False
            
            elif message_request.status == MessageRequest.Status.FAILED:
                elapsed_time = (poll_count * 5) / 60
                error_msg = message_request.error_message or "Unknown error"
                print(f"[Market Analysis] ✗ Failed '{node.title}' (Level {node.level}) after {elapsed_time:.1f} minutes - Error: {error_msg}")
                
                # Check if we should retry
                if node.retry_count < max_retries:
                    retry_delay = min(300, 30 * (2 ** node.retry_count))  # Exponential backoff: 30s, 60s, 120s, max 300s
                    print(f"[Market Analysis] Will retry in {retry_delay} seconds (Retry #{node.retry_count + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    return self._analyze_node(node, is_root=is_root, max_retries=max_retries)
                else:
                    print(f"[Market Analysis] ✗ Max retries ({max_retries}) exceeded for '{node.title}'")
                    node.mark_failed()
                    return False
            
            # Wait before polling again (check every 5 seconds to reduce load)
            time.sleep(5)
    
    def _parse_llm_response(self, response_text, return_cleaned_json=False):
        """
        Parse LLM response and extract JSON data
        Handles the new detailed prompt format
        
        Args:
            response_text: Raw response from LLM
            return_cleaned_json: If True, returns (parsed_data, cleaned_json_text) tuple
        
        Returns:
            If return_cleaned_json=False: parsed_data dict or None
            If return_cleaned_json=True: (parsed_data dict or None, cleaned_json_text or None)
        """
        try:
            # Try to find JSON in the response
            # LLM might wrap it in markdown code blocks
            text = response_text.strip()
            
            print(f"[Parser] Response length: {len(text)} chars")
            print(f"[Parser] First 200 chars: {text[:200]}")
            
            # Remove markdown code blocks if present
            if text.startswith('```'):
                lines = text.split('\n')
                text = '\n'.join(lines[1:-1]) if len(lines) > 2 else text
                text = text.replace('```json', '').replace('```', '').strip()
                print(f"[Parser] Removed markdown, new length: {len(text)} chars")
            
            # Remove common LLM artifacts (e.g., "jsonCopy code", "json\nCopy code")
            artifacts = ['jsonCopy code', 'json\nCopy code', 'json Copy code', 'Copy code']
            for artifact in artifacts:
                if text.startswith(artifact):
                    text = text[len(artifact):].strip()
                    print(f"[Parser] Removed artifact '{artifact}', new length: {len(text)} chars")
                    break
            
            # Try to find JSON if there's extra text
            if not text.startswith('{'):
                # Look for the first {
                start_idx = text.find('{')
                if start_idx != -1:
                    text = text[start_idx:]
                    print(f"[Parser] Found JSON starting at position {start_idx}")
            
            # Try to parse as-is first (maybe it's already valid)
            try:
                data = json.loads(text)
                print(f"[Parser] JSON is already valid, no fixes needed")
                cleaned_json_text = text
                # Skip to validation section
            except json.JSONDecodeError as first_error:
                print(f"[Parser] Initial parse failed: {first_error.msg} at position {first_error.pos}")
                
                # Now try fixes
                original_text = text
                fixes_applied = []
                
                # Fix 1: Remove trailing text after the last }
                # Only remove if it's clearly non-JSON text (no JSON structural characters)
                if '{' in text:
                    last_brace = text.rfind('}')
                    if last_brace != -1 and last_brace < len(text) - 1:
                        trailing_text = text[last_brace + 1:].strip()
                        # Only remove if it looks like conversational text (no JSON structural chars)
                        # Allow whitespace but not: {}[]":,
                        if trailing_text and not any(c in trailing_text for c in '{}[]":,'):
                            # Extra safety: verify the JSON without trailing text is valid
                            test_text = text[:last_brace + 1]
                            try:
                                json.loads(test_text)
                                text = test_text
                                fixes_applied.append(f"removed trailing text: '{trailing_text[:30]}...'")
                            except json.JSONDecodeError:
                                # Don't remove if it breaks the JSON
                                print(f"[Parser] Skipping trailing text removal - would break JSON")
                
                # Fix 2: Check bracket balance
                open_brackets = text.count('[')
                close_brackets = text.count(']')
                open_braces = text.count('{')
                close_braces = text.count('}')
                
                if open_brackets != close_brackets or open_braces != close_braces:
                    print(f"[Parser] Bracket imbalance: [ {open_brackets}/{close_brackets}, {{ {open_braces}/{close_braces}")
                    
                    # Fix 2a: Context-aware bracket fix for arrays
                    # Track opening brackets and fix mismatched closers based on context
                    import re
                    
                    def fix_array_brackets(json_str):
                        """Fix mismatched array brackets by tracking context"""
                        result = []
                        stack = []  # Track what we've opened: 'array' or 'object'
                        in_string = False
                        escape_next = False
                        
                        for i, char in enumerate(json_str):
                            # Handle string state
                            if escape_next:
                                result.append(char)
                                escape_next = False
                                continue
                            
                            if char == '\\' and in_string:
                                result.append(char)
                                escape_next = True
                                continue
                            
                            if char == '"':
                                in_string = not in_string
                                result.append(char)
                                continue
                            
                            # Only process structural characters outside strings
                            if not in_string:
                                if char == '[':
                                    stack.append('array')
                                    result.append(char)
                                elif char == '{':
                                    stack.append('object')
                                    result.append(char)
                                elif char == ']':
                                    if stack and stack[-1] == 'array':
                                        stack.pop()
                                        result.append(char)
                                    elif stack and stack[-1] == 'object':
                                        # Wrong closer - should be } but got ]
                                        stack.pop()
                                        result.append('}')
                                    else:
                                        result.append(char)
                                elif char == '}':
                                    if stack and stack[-1] == 'object':
                                        stack.pop()
                                        result.append(char)
                                    elif stack and stack[-1] == 'array':
                                        # Wrong closer - should be ] but got }
                                        stack.pop()
                                        result.append(']')
                                    else:
                                        result.append(char)
                                else:
                                    result.append(char)
                            else:
                                result.append(char)
                        
                        return ''.join(result)
                    
                    test_text = fix_array_brackets(text)
                    
                    # Test if this fix helps
                    try:
                        json.loads(test_text)
                        text = test_text
                        fixes_applied.append("fixed array/object bracket mismatches")
                    except json.JSONDecodeError:
                        # Fix didn't help, try fallback approach
                        if open_brackets > close_brackets and open_braces > close_braces:
                            # Both brackets and braces are unclosed - likely truncated JSON
                            print(f"[Parser] JSON appears truncated, cannot safely fix")
                        elif open_brackets > close_brackets:
                            # More [ than ] - try replacing trailing } with ]
                            deficit = open_brackets - close_brackets
                            test_text = text
                            for _ in range(min(deficit, 3)):  # Limit to 3 replacements max
                                last_brace_pos = test_text.rfind('}')
                                if last_brace_pos != -1:
                                    test_text = test_text[:last_brace_pos] + ']' + test_text[last_brace_pos + 1:]
                            
                            # Test if this fix works
                            try:
                                json.loads(test_text)
                                text = test_text
                                fixes_applied.append(f"replaced {deficit} trailing }} with ]")
                            except json.JSONDecodeError:
                                print(f"[Parser] Bracket replacement didn't fix the JSON")
                
                if fixes_applied:
                    print(f"[Parser] Applied fixes: {', '.join(fixes_applied)}")
                
                # Final parse attempt
                data = json.loads(text)
                cleaned_json_text = text
                print(f"[Parser] Successfully parsed JSON after fixes")
            
            # Validation section
            print(f"[Parser] Validating JSON structure with keys: {list(data.keys())}")
            
            # Validate structure - new format has 'parent' and 'children' keys
            if 'parent' in data and 'children' in data:
                print(f"[Parser] Detected new format with {len(data['children'])} children")
                # New detailed format
                parent = data['parent']
                children = data['children']
                notes = data.get('notes', {})
                
                # Validate parent has required fields
                if 'value_added_usd' not in parent or 'employment' not in parent:
                    print(f"[Parser] ERROR: Parent missing required fields. Has: {list(parent.keys())}")
                    return None
                
                # Convert children to sub_markets format
                sub_markets = []
                for i, child in enumerate(children):
                    try:
                        sub_market = {
                            'name': child['name'],
                            'value_added_usd': child['value_added_usd'],
                            'employment_count': child['employment'],
                            'share_of_parent': child.get('share_of_parent', 0),
                            'definition': child.get('definition', {}),
                            'rationale': child.get('rationale', []),
                            'confidence': child.get('confidence', 1.0)
                        }
                        sub_markets.append(sub_market)
                    except KeyError as e:
                        print(f"[Parser] ERROR: Child {i} missing field: {e}")
                        print(f"[Parser] Child {i} has keys: {list(child.keys())}")
                        return None
                
                result = {
                    'value_added_usd': parent['value_added_usd'],
                    'employment_count': parent['employment'],
                    'year': parent.get('year', timezone.now().year),
                    'sub_markets': sub_markets,
                    'notes': notes
                }
                print(f"[Parser] ✓ Successfully parsed new format")
                if return_cleaned_json:
                    return result, cleaned_json_text
                return result
            
            # Fallback: old simple format
            elif 'market_name' in data or 'total_value_added_usd' in data:
                print(f"[Parser] Detected old format")
                result = {
                    'value_added_usd': data.get('total_value_added_usd', 0),
                    'employment_count': data.get('total_employment', 0),
                    'rationale': data.get('rationale', ''),
                    'sub_markets': data.get('sub_markets', [])
                }
                if return_cleaned_json:
                    return result, cleaned_json_text
                return result
            
            else:
                print(f"[Parser] ERROR: Unexpected JSON structure with keys: {list(data.keys())}")
                print(f"[Parser] Full data: {json.dumps(data, indent=2)[:500]}...")
                if return_cleaned_json:
                    return None, None
                return None
            
        except json.JSONDecodeError as e:
            print(f"[Parser] ERROR: JSON decode failed: {e}")
            print(f"[Parser] Error at line {e.lineno}, column {e.colno}")
            print(f"[Parser] Response text (first 1000 chars):")
            print(response_text[:1000])
            print("...")
            if return_cleaned_json:
                return None, None
            return None
        except (KeyError, ValueError, TypeError) as e:
            print(f"[Parser] ERROR: {type(e).__name__}: {e}")
            print(f"[Parser] Response text (first 500 chars): {response_text[:500]}...")
            if return_cleaned_json:
                return None, None
            return None
    
    def get_tree_data(self, root_node):
        """
        Get hierarchical tree data for visualization
        """
        def build_tree(node):
            # Clean data by removing metadata and llm_response
            clean_data = node.data.copy() if node.data else {}
            if 'metadata' in clean_data:
                del clean_data['metadata']
            if 'llm_response' in clean_data:
                del clean_data['llm_response']
            
            return {
                'id': str(node.id),
                'name': node.title,
                'value': node.value_added,
                'employment': node.employment,
                'level': node.level,
                'status': node.status,
                'data': clean_data,
                'children': [build_tree(child) for child in node.children.all()]
            }
        
        return build_tree(root_node)
