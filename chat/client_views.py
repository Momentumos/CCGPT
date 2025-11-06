from django.shortcuts import render


def client_app(request):
    """Serve the HTML/JS client application"""
    return render(request, 'client/index.html')
