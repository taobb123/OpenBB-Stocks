"""
市场分析 API 视图
"""
import asyncio
import sys
import os
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 延迟导入，避免在 Django 启动时导入所有模块
def get_interactive_analyzer():
    """延迟导入 InteractiveMarketAnalyzer"""
    from interactive_analysis import InteractiveMarketAnalyzer
    return InteractiveMarketAnalyzer

def get_extract_function():
    """延迟导入 extract_stock_codes"""
    from extract_stock_codes import extract_stock_codes
    return extract_stock_codes


@csrf_exempt
def extract_stock_codes_api(request):
    """
    提取股票代码 API
    POST /api/extract-stock-codes/
    Body: {"content": "股票代码文本内容"}
    """
    if request.method != "POST":
        return JsonResponse({
            'success': False,
            'error': '此端点仅支持 POST 请求',
            'method': request.method,
            'allowed_methods': ['POST']
        }, status=405)
    
    try:
        data = json.loads(request.body)
        content = data.get('content', '')
        
        if not content:
            return JsonResponse({
                'success': False,
                'error': '内容不能为空'
            }, status=400)
        
        # 提取股票代码（延迟导入）
        extract_stock_codes = get_extract_function()
        stock_codes = extract_stock_codes(content)
        
        return JsonResponse({
            'success': True,
            'stock_codes': stock_codes,
            'count': len(stock_codes)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def analyze_custom_stocks_api(request):
    """
    分析自定义股票列表 API（选项2）
    POST /api/analyze-custom-stocks/
    Body: {"stock_codes": ["600519", "000001"], "market_type": "A股"}
    """
    if request.method != "POST":
        return JsonResponse({
            'success': False,
            'error': '此端点仅支持 POST 请求',
            'method': request.method,
            'allowed_methods': ['POST']
        }, status=405)
    
    try:
        data = json.loads(request.body)
        stock_codes = data.get('stock_codes', [])
        market_type = data.get('market_type', 'A股')
        
        if not stock_codes:
            return JsonResponse({
                'success': False,
                'error': '股票代码列表不能为空'
            }, status=400)
        
        # 运行异步分析（延迟导入）
        InteractiveMarketAnalyzer = get_interactive_analyzer()
        async def run_analysis():
            analyzer = InteractiveMarketAnalyzer(use_akshare=True)
            try:
                analysis = await analyzer.analyze_custom_stocks(
                    stock_codes,
                    market_type=market_type
                )
                report = analyzer.format_custom_analysis_report(analysis)
                return {
                    'success': True,
                    'data': analysis,
                    'report': report
                }
            finally:
                await analyzer.close()
        
        # 执行异步函数
        result = asyncio.run(run_analysis())
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def run_full_market_analysis_api(request):
    """
    运行完整市场分析 API（选项4）
    POST /api/run-full-analysis/
    Body: {"index_query": "China", "market_type": "A股"}
    """
    if request.method != "POST":
        return JsonResponse({
            'success': False,
            'error': '此端点仅支持 POST 请求',
            'method': request.method,
            'allowed_methods': ['POST'],
            'usage': '请使用 POST 请求，并在 body 中传递 JSON 数据'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        index_query = data.get('index_query', 'China')
        market_type = data.get('market_type', 'A股')
        
        # 运行异步分析（延迟导入）
        InteractiveMarketAnalyzer = get_interactive_analyzer()
        async def run_analysis():
            analyzer = InteractiveMarketAnalyzer(use_akshare=True)
            try:
                result = await analyzer.analyzer.run_full_analysis(
                    index_query=index_query,
                    market_type=market_type,
                    skip_stock_screening=True
                )
                
                # 生成报告
                from market_structure_analysis import MarketStructureAnalyzer
                report_analyzer = MarketStructureAnalyzer()
                report = report_analyzer.generate_investment_report(result)
                
                return {
                    'success': True,
                    'data': result,
                    'report': report
                }
            finally:
                await analyzer.close()
        
        # 执行异步函数
        result = asyncio.run(run_analysis())
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

