from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/extension/', consumers.BrowserExtensionConsumer.as_asgi()),
]
