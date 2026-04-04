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
            '/api/analyze-custom-stocks/charts/',
            '/api/analyze-custom-stocks/report/',
            '/api/run-full-analysis/',
        ]
    })

urlpatterns = [
    path('', api_health_check, name='api-health'),
    path('extract-stock-codes/', views.extract_stock_codes_api, name='extract-stock-codes'),
    path('analyze-custom-stocks/', views.analyze_custom_stocks_api, name='analyze-custom-stocks'),
    path(
        'analyze-custom-stocks/charts/',
        views.analyze_custom_stocks_charts_api,
        name='analyze-custom-stocks-charts',
    ),
    path(
        'analyze-custom-stocks/report/',
        views.analyze_custom_stocks_report_api,
        name='analyze-custom-stocks-report',
    ),
    path('run-full-analysis/', views.run_full_market_analysis_api, name='run-full-analysis'),
]

