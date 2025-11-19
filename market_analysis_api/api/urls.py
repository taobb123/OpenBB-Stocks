"""
API URL 配置
"""
from django.urls import path
from django.http import JsonResponse
from . import views

def api_health_check(request):
    """API 健康检查端点"""
    return JsonResponse({
        'status': 'ok',
        'message': 'Market Analysis API is running',
        'endpoints': [
            '/api/extract-stock-codes/',
            '/api/analyze-custom-stocks/',
            '/api/run-full-analysis/',
        ]
    })

urlpatterns = [
    path('', api_health_check, name='api-health'),
    path('extract-stock-codes/', views.extract_stock_codes_api, name='extract-stock-codes'),
    path('analyze-custom-stocks/', views.analyze_custom_stocks_api, name='analyze-custom-stocks'),
    path('run-full-analysis/', views.run_full_market_analysis_api, name='run-full-analysis'),
]

