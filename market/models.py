from django.db import models
from account.models import GPTAccount
import uuid


class MarketNode(models.Model):
    """
    Hierarchical market node with economic data stored in JSON.
    Only title and parent_id are in database fields for efficient querying.
    All economic data (value_added, employment, sub-markets, etc.) in JSON field.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Analysis'
        ANALYZING = 'analyzing', 'Analyzing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(GPTAccount, on_delete=models.CASCADE, related_name='market_nodes')
    
    # Database fields for querying
    title = models.CharField(max_length=500, help_text="Market name/title")
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children'
    )
    level = models.IntegerField(default=0, help_text="Depth level: 0=root, 1=first level, 2=second level, 3=third level")
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # JSON field for all economic data
    data = models.JSONField(
        default=dict,
        help_text="""
        Stores all economic data:
        {
            "value_added_usd": float,
            "employment_count": int,
            "rationale": str,
            "sub_markets": [
                {
                    "name": str,
                    "value_added_usd": float,
                    "employment_count": int,
                    "rationale": str
                }
            ],
            "metadata": {
                "analysis_date": str,
                "llm_response": str,
                "chat_id": str,
                "request_id": str
            }
        }
        """
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Market Node"
        verbose_name_plural = "Market Nodes"
        ordering = ['level', '-created_at']
        indexes = [
            models.Index(fields=['account', 'level']),
            models.Index(fields=['parent', 'status']),
            models.Index(fields=['status', 'level']),
        ]
    
    def __str__(self):
        return f"L{self.level}: {self.title} ({self.status})"
    
    @property
    def value_added(self):
        """Get value added from JSON data"""
        return self.data.get('value_added_usd', 0)
    
    @property
    def employment(self):
        """Get employment count from JSON data"""
        return self.data.get('employment_count', 0)
    
    @property
    def sub_markets(self):
        """Get sub-markets from JSON data"""
        return self.data.get('sub_markets', [])
    
    def mark_analyzing(self):
        """Mark node as being analyzed"""
        self.status = self.Status.ANALYZING
        self.save(update_fields=['status'])
    
    def mark_completed(self, analysis_data):
        """Mark node as completed with analysis data"""
        from django.utils import timezone
        self.status = self.Status.COMPLETED
        self.data = analysis_data
        self.analyzed_at = timezone.now()
        self.save(update_fields=['status', 'data', 'analyzed_at'])
    
    def mark_failed(self):
        """Mark node as failed"""
        self.status = self.Status.FAILED
        self.save(update_fields=['status'])
    
    def create_child_nodes(self):
        """
        Create child nodes from sub_markets in data.
        Returns list of created MarketNode instances.
        """
        if self.level >= 3:  # Max depth is 3 (0, 1, 2, 3)
            return []
        
        children = []
        for sub_market in self.sub_markets:
            child = MarketNode.objects.create(
                account=self.account,
                title=sub_market.get('name', 'Unnamed Market'),
                parent=self,
                level=self.level + 1,
                status=self.Status.PENDING,
                data={
                    'value_added_usd': sub_market.get('value_added_usd', 0),
                    'employment_count': sub_market.get('employment_count', 0),
                    'rationale': sub_market.get('rationale', ''),
                }
            )
            children.append(child)
        
        return children


class MarketAnalysisJob(models.Model):
    """
    Tracks the overall analysis job for a root market node.
    Manages the recursive analysis process across all levels.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(GPTAccount, on_delete=models.CASCADE, related_name='market_jobs')
    root_node = models.ForeignKey(
        MarketNode, 
        on_delete=models.CASCADE, 
        related_name='jobs'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Progress tracking
    total_nodes = models.IntegerField(default=0)
    completed_nodes = models.IntegerField(default=0)
    failed_nodes = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Market Analysis Job"
        verbose_name_plural = "Market Analysis Jobs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Job for {self.root_node.title} - {self.status}"
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.total_nodes == 0:
            return 0
        return int((self.completed_nodes / self.total_nodes) * 100)
