from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('submit/', views.submit_message, name='submit_message'),
    path('requests/', views.list_requests, name='list_requests'),
    path('requests/<uuid:request_id>/', views.get_request_status, name='get_request_status'),
    path('chats/', views.list_chats, name='list_chats'),
    path('chats/<str:chat_id>/', views.get_chat, name='get_chat'),
]
