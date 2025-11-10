from django.urls import path
from . import views

app_name = 'market'

urlpatterns = [
    # Analysis jobs
    path('analyze/', views.start_analysis, name='start_analysis'),
    path('jobs/', views.list_jobs, name='list_jobs'),
    path('jobs/<uuid:job_id>/', views.get_job, name='get_job'),
    
    # Market nodes
    path('nodes/', views.list_nodes, name='list_nodes'),
    path('nodes/roots/', views.get_root_nodes, name='get_root_nodes'),
    path('nodes/<uuid:node_id>/', views.get_node, name='get_node'),
    path('nodes/<uuid:node_id>/delete/', views.delete_node, name='delete_node'),
    
    # Tree visualization
    path('tree/<uuid:root_node_id>/', views.get_tree, name='get_tree'),
]
