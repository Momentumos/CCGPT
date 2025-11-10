from rest_framework import serializers
from .models import MarketNode, MarketAnalysisJob


class MarketNodeSerializer(serializers.ModelSerializer):
    """Serializer for MarketNode with nested children"""
    value_added = serializers.ReadOnlyField()
    employment = serializers.ReadOnlyField()
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = MarketNode
        fields = [
            'id', 'title', 'level', 'status', 'parent',
            'value_added', 'employment', 'data',
            'created_at', 'updated_at', 'analyzed_at',
            'children'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'analyzed_at']
    
    def get_children(self, obj):
        """Get children nodes if requested"""
        request = self.context.get('request')
        if request and request.query_params.get('include_children') == 'true':
            children = obj.children.all()
            return MarketNodeSerializer(children, many=True, context=self.context).data
        return []


class MarketNodeTreeSerializer(serializers.ModelSerializer):
    """Serializer for full tree structure"""
    value_added = serializers.ReadOnlyField()
    employment = serializers.ReadOnlyField()
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = MarketNode
        fields = [
            'id', 'title', 'level', 'status',
            'value_added', 'employment', 'data',
            'children'
        ]
    
    def get_children(self, obj):
        """Recursively get all children"""
        children = obj.children.all()
        return MarketNodeTreeSerializer(children, many=True).data


class MarketAnalysisJobSerializer(serializers.ModelSerializer):
    root_node = MarketNodeSerializer(read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = MarketAnalysisJob
        fields = [
            'id', 'root_node', 'status', 'total_nodes', 
            'completed_nodes', 'failed_nodes', 'progress_percentage',
            'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'started_at', 'completed_at']


class MarketAnalysisStartSerializer(serializers.Serializer):
    """Serializer for starting a new market analysis"""
    market_titles = serializers.ListField(
        child=serializers.CharField(max_length=500),
        help_text="List of root market titles to analyze (e.g., ['AI Market', 'Fitness Market'])"
    )
    max_depth = serializers.IntegerField(
        default=3,
        min_value=0,
        max_value=3,
        help_text="Maximum depth level (0-3)"
    )
