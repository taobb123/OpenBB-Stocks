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
import numpy as np
import pandas as pd

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


def make_json_serializable(obj):
    """
    递归地将对象转换为 JSON 可序列化的格式
    处理 numpy、pandas 类型和 Python bool 类型
    """
    # 处理 numpy 类型
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        # 确保所有布尔值都转换为 Python bool
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Series):
        return obj.to_dict()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict('records')
    # 处理字典
    elif isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    # 处理列表和元组
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    # 处理基本类型
    elif isinstance(obj, (int, float, str, type(None))):
        return obj
    # 对于其他类型，尝试转换为字符串或返回 None
    else:
        try:
            # 尝试 JSON 序列化测试
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            # 如果无法序列化，尝试转换为字符串
            try:
                return str(obj)
            except:
                return None


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
            analyzer = None
            try:
                # 使用 akshare 进行分析（OpenBB SDK 已禁用，技术指标使用 akshare 数据计算）
                analyzer = InteractiveMarketAnalyzer(use_akshare=True, use_openbb=False)
                
                # 执行分析
                analysis = await analyzer.analyze_custom_stocks(
                    stock_codes,
                    market_type=market_type
                )
                
                # 生成报告（即使分析有部分错误，也尝试生成报告）
                report = ""
                try:
                    report = analyzer.format_custom_analysis_report(analysis)
                except Exception as report_error:
                    print(f"⚠️ 生成报告时出错: {str(report_error)[:200]}")
                    # 如果报告生成失败，创建一个简单的报告
                    report = f"分析完成，但报告生成时出现错误: {str(report_error)[:200]}\n\n"
                    if analysis and analysis.get("stocks"):
                        report += f"共分析 {len(analysis.get('stocks', []))} 只股票\n"
                        for stock in analysis.get("stocks", []):
                            symbol = stock.get("symbol", "N/A")
                            report += f"\n股票代码: {symbol}\n"
                
                # 保存买入建议到 Buy.txt（追加模式）
                try:
                    analyzer._save_buy_recommendations(analysis.get("stocks", []))
                except Exception as save_error:
                    print(f"⚠️ 保存买入建议时出错: {str(save_error)[:200]}")
                
                return {
                    'success': True,
                    'data': analysis,
                    'report': report
                }
            except Exception as analysis_error:
                # 即使分析失败，也尝试返回部分结果
                error_msg = str(analysis_error)
                print(f"❌ 分析过程出错: {error_msg[:500]}")
                
                # 尝试生成错误报告
                error_report = f"分析过程中出现错误:\n{error_msg[:500]}\n\n"
                error_report += f"已分析的股票代码: {', '.join(stock_codes)}\n"
                
                return {
                    'success': False,
                    'error': error_msg[:500],
                    'report': error_report,
                    'data': None
                }
            finally:
                if analyzer:
                    try:
                        await analyzer.close()
                    except:
                        pass
        
        # 执行异步函数
        result = asyncio.run(run_analysis())
        # 确保所有数据都是 JSON 可序列化的
        result = make_json_serializable(result)
        return JsonResponse(result)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ API 调用出错: {error_trace}")
        return JsonResponse({
            'success': False,
            'error': str(e)[:500],
            'report': f'分析失败:\n{str(e)[:500]}\n\n请检查后端日志获取详细信息。'
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
        # 确保所有数据都是 JSON 可序列化的
        result = make_json_serializable(result)
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

