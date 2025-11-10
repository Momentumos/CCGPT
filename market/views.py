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
