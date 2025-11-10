from django.shortcuts import render


def market_app(request):
    """Render the market analysis client application"""
    return render(request, 'market/index.html')
