from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from chat.views import APIKeyAuthentication
from .models import MarketNode, MarketAnalysisJob
from .serializers import (
    MarketNodeSerializer, MarketNodeTreeSerializer,
    MarketAnalysisJobSerializer, MarketAnalysisStartSerializer
)
from .services import MarketAnalysisService
import threading
import csv


@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
def start_analysis(request):
    """
    Start a new market analysis for one or more root markets
    """
    serializer = MarketAnalysisStartSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    account = request.user
    market_titles = serializer.validated_data['market_titles']
    max_depth = serializer.validated_data.get('max_depth', 2)
    
    # Create analysis service
    service = MarketAnalysisService(account)
    
    # Start analysis jobs
    jobs = service.start_analysis(market_titles, max_depth)
    
    # Process jobs in background threads
    for job in jobs:
        thread = threading.Thread(target=service.process_job, args=(job,))
        thread.daemon = True
        thread.start()
    
    # Return created jobs
    return Response(
        MarketAnalysisJobSerializer(jobs, many=True).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def list_jobs(request):
    """
    List all market analysis jobs for the authenticated account
    """
    account = request.user
    jobs = MarketAnalysisJob.objects.filter(account=account)
    
    # Filter by status if provided
    status_filter = request.query_params.get('status')
    if status_filter:
        jobs = jobs.filter(status=status_filter)
    
    serializer = MarketAnalysisJobSerializer(jobs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def get_job(request, job_id):
    """
    Get details of a specific market analysis job
    """
    account = request.user
    job = get_object_or_404(MarketAnalysisJob, id=job_id, account=account)
    
    serializer = MarketAnalysisJobSerializer(job)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def list_nodes(request):
    """
    List all market nodes for the authenticated account
    """
    account = request.user
    nodes = MarketNode.objects.filter(account=account)
    
    # Filter by level if provided
    level_filter = request.query_params.get('level')
    if level_filter is not None:
        nodes = nodes.filter(level=int(level_filter))
    
    # Filter by status if provided
    status_filter = request.query_params.get('status')
    if status_filter:
        nodes = nodes.filter(status=status_filter)
    
    # Filter by parent if provided
    parent_filter = request.query_params.get('parent')
    if parent_filter:
        nodes = nodes.filter(parent_id=parent_filter)
    
    serializer = MarketNodeSerializer(
        nodes, 
        many=True,
        context={'request': request}
    )
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def get_node(request, node_id):
    """
    Get details of a specific market node
    """
    account = request.user
    node = get_object_or_404(MarketNode, id=node_id, account=account)
    
    serializer = MarketNodeSerializer(node, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def get_tree(request, root_node_id):
    """
    Get full hierarchical tree for a root node (for visualization)
    """
    account = request.user
    root_node = get_object_or_404(
        MarketNode, 
        id=root_node_id, 
        account=account,
        level=0  # Ensure it's a root node
    )
    
    service = MarketAnalysisService(account)
    tree_data = service.get_tree_data(root_node)
    
    return Response(tree_data)


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def get_root_nodes(request):
    """
    Get all root nodes (level 0) for the authenticated account
    """
    account = request.user
    root_nodes = MarketNode.objects.filter(account=account, level=0)
    
    serializer = MarketNodeSerializer(root_nodes, many=True)
    return Response(serializer.data)


@api_view(['DELETE'])
@authentication_classes([APIKeyAuthentication])
def delete_node(request, node_id):
    """
    Delete a market node and all its children
    """
    account = request.user
    node = get_object_or_404(MarketNode, id=node_id, account=account)
    
    # Delete node (cascades to children)
    node.delete()
    
    return Response(
        {"message": "Node and its children deleted successfully"},
        status=status.HTTP_204_NO_CONTENT
    )


@api_view(['GET'])
def export_all_nodes(request):
    """
    Export all market nodes as a single JSON file for visualization.
    Returns a hierarchical structure with all root nodes and their complete trees.
    No authentication required - returns all nodes from all accounts.
    
    Response format:
    {
        "metadata": {
            "export_date": "...",
            "total_nodes": 123,
            "root_count": 5
        },
        "trees": [
            {
                "id": "...",
                "title": "Market Name",
                "level": 0,
                "status": "completed",
                "value_added": 1000000,
                "employment": 5000,
                "data": {...},
                "created_at": "...",
                "analyzed_at": "...",
                "children": [...]
            }
        ]
    }
    """
    from django.http import JsonResponse
    from django.utils import timezone
    import json
    
    # Get all root nodes from all accounts
    root_nodes = MarketNode.objects.filter(level=0).order_by('created_at')
    
    # Build complete trees for each root
    def build_node_data(node):
        """Recursively build node data with all children"""
        children = node.children.all().order_by('created_at')
        
        # Clean data by removing metadata
        clean_data = node.data.copy() if node.data else {}
        if 'metadata' in clean_data:
            del clean_data['metadata']
        
        return {
            'id': str(node.id),
            'title': node.title,
            'level': node.level,
            'status': node.status,
            'value_added': node.value_added,
            'employment': node.employment,
            'data': clean_data,
            'created_at': node.created_at.isoformat() if node.created_at else None,
            'updated_at': node.updated_at.isoformat() if node.updated_at else None,
            'analyzed_at': node.analyzed_at.isoformat() if node.analyzed_at else None,
            'retry_count': node.retry_count,
            'children': [build_node_data(child) for child in children]
        }
    
    # Build all trees
    trees = [build_node_data(root) for root in root_nodes]
    
    # Count total nodes
    total_nodes = MarketNode.objects.all().count()
    
    # Build response
    response_data = {
        'metadata': {
            'export_date': timezone.now().isoformat(),
            'total_nodes': total_nodes,
            'root_count': len(trees),
        },
        'trees': trees
    }
    
    # Return as downloadable JSON file
    response = JsonResponse(response_data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="market_nodes_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
    
    return response


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def export_tree_csv(request, root_node_id):
    """
    Export a single market tree as CSV file.
    Returns a flat CSV with one row per node, including hierarchical information.
    
    CSV Columns:
    - ID, Title, Level, Status, Value Added, Employment, Parent ID, Parent Title, 
      Created At, Updated At, Analyzed At, Retry Count
    """
    from django.http import HttpResponse
    from django.utils import timezone
    
    account = request.user
    root_node = get_object_or_404(
        MarketNode, 
        id=root_node_id, 
        account=account,
        level=0
    )
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{root_node.title.replace(" ", "_")}_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'ID',
        'Title',
        'Level',
        'Value Added',
        'Employment',
        'Parent ID',
        'Parent Title',
    ])
    
    # Recursively collect all nodes
    def write_node_and_children(node):
        """Recursively write node and its children to CSV"""
        writer.writerow([
            str(node.id),
            node.title,
            node.level,
            node.value_added or 0,
            node.employment or 0,
            str(node.parent.id) if node.parent else '',
            node.parent.title if node.parent else '',
        ])
        
        # Write all children
        for child in node.children.all().order_by('created_at'):
            write_node_and_children(child)
    
    # Write root and all descendants
    write_node_and_children(root_node)
    
    return response
