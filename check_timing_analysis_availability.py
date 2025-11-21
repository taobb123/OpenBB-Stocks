"""
检查 get_stock_timing_analysis() 接口的可用性
"""

import sys
import traceback
from typing import Dict, Any

def check_interface_availability():
    """检查接口可用性"""
    print("=" * 60)
    print("检查 get_stock_timing_analysis() 接口可用性")
    print("=" * 60)
    print()
    
    results = {
        "akshare_module": False,
        "akshare_data_source": False,
        "interactive_analyzer": False,
        "akshare_instance": False,
        "test_symbol": None,
        "test_result": None,
        "errors": []
    }
    
    # 1. 检查 akshare 模块
    print("1. 检查 akshare 模块...")
    try:
        import akshare as ak
        results["akshare_module"] = True
        print("   ✅ akshare 模块可用")
    except ImportError as e:
        results["errors"].append(f"akshare 模块导入失败: {e}")
        print(f"   ❌ akshare 模块不可用: {e}")
        print("   建议: pip install akshare")
        return results
    
    # 2. 检查 akshare_data_source 模块
    print("\n2. 检查 akshare_data_source 模块...")
    try:
        from akshare_data_source import AKShareDataSource
        results["akshare_data_source"] = True
        print("   ✅ akshare_data_source 模块可用")
    except ImportError as e:
        results["errors"].append(f"akshare_data_source 模块导入失败: {e}")
        print(f"   ❌ akshare_data_source 模块不可用: {e}")
        return results
    
    # 3. 检查 InteractiveMarketAnalyzer
    print("\n3. 检查 InteractiveMarketAnalyzer...")
    try:
        from interactive_analysis import InteractiveMarketAnalyzer
        results["interactive_analyzer"] = True
        print("   ✅ InteractiveMarketAnalyzer 类可用")
    except ImportError as e:
        results["errors"].append(f"InteractiveMarketAnalyzer 导入失败: {e}")
        print(f"   ❌ InteractiveMarketAnalyzer 不可用: {e}")
        traceback.print_exc()
        return results
    
    # 4. 初始化分析器
    print("\n4. 初始化 InteractiveMarketAnalyzer...")
    try:
        analyzer = InteractiveMarketAnalyzer(use_akshare=True)
        results["interactive_analyzer"] = True
        print("   ✅ InteractiveMarketAnalyzer 初始化成功")
        
        # 检查 akshare 实例
        if analyzer.akshare:
            results["akshare_instance"] = True
            print("   ✅ akshare 实例可用")
        else:
            results["errors"].append("akshare 实例为 None")
            print("   ❌ akshare 实例不可用（可能未安装或初始化失败）")
            return results
    except Exception as e:
        results["errors"].append(f"InteractiveMarketAnalyzer 初始化失败: {e}")
        print(f"   ❌ InteractiveMarketAnalyzer 初始化失败: {e}")
        traceback.print_exc()
        return results
    
    # 5. 测试接口 - 使用一个常见的股票代码
    print("\n5. 测试 get_stock_timing_analysis() 接口...")
    test_symbols = ["600519", "000001", "000002"]  # 贵州茅台、平安银行、万科A
    
    for symbol in test_symbols:
        print(f"\n   测试股票代码: {symbol}")
        try:
            result = analyzer.get_stock_timing_analysis(symbol)
            
            # 检查返回结果
            if isinstance(result, dict):
                if "error" in result:
                    print(f"   ⚠️ 返回错误: {result['error']}")
                    results["errors"].append(f"{symbol}: {result['error']}")
                    continue
                
                # 检查必要字段
                required_fields = ["symbol", "indicators", "timing"]
                missing_fields = [field for field in required_fields if field not in result]
                
                if missing_fields:
                    print(f"   ⚠️ 缺少必要字段: {missing_fields}")
                    results["errors"].append(f"{symbol}: 缺少字段 {missing_fields}")
                    continue
                
                # 检查 indicators
                indicators = result.get("indicators", {})
                indicator_keys = list(indicators.keys())
                print(f"   ✅ 接口调用成功")
                print(f"   📊 获取到 {len(indicator_keys)} 个技术指标: {', '.join(indicator_keys)}")
                
                # 检查 timing
                timing = result.get("timing", {})
                if timing:
                    score = timing.get("score", "N/A")
                    recommendation = timing.get("recommendation", "N/A")
                    factors_count = len(timing.get("factors", []))
                    print(f"   ⏰ 时机评分: {score}, 建议: {recommendation}, 关键因素: {factors_count} 个")
                
                results["test_symbol"] = symbol
                results["test_result"] = {
                    "success": True,
                    "indicators_count": len(indicator_keys),
                    "indicators": indicator_keys,
                    "timing_score": timing.get("score") if timing else None,
                    "timing_recommendation": timing.get("recommendation") if timing else None
                }
                print(f"\n   ✅ 接口测试通过！")
                break  # 成功一个就退出
                
            else:
                print(f"   ❌ 返回结果格式错误: 期望 dict，得到 {type(result)}")
                results["errors"].append(f"{symbol}: 返回格式错误")
                
        except Exception as e:
            print(f"   ❌ 接口调用失败: {e}")
            results["errors"].append(f"{symbol}: {str(e)}")
            traceback.print_exc()
            continue
    
    # 6. 详细检查接口返回的数据结构
    if results["test_result"] and results["test_result"].get("success"):
        print("\n6. 检查返回数据结构...")
        try:
            result = analyzer.get_stock_timing_analysis(results["test_symbol"])
            
            print("\n   数据结构检查:")
            print(f"   - symbol: {result.get('symbol')}")
            print(f"   - current_price: {result.get('current_price')}")
            
            indicators = result.get("indicators", {})
            print(f"   - indicators: {len(indicators)} 个")
            for key, value in indicators.items():
                if isinstance(value, dict):
                    print(f"     * {key}: {len(value)} 个字段")
                else:
                    print(f"     * {key}: {type(value)}")
            
            timing = result.get("timing", {})
            if timing:
                print(f"   - timing:")
                print(f"     * score: {timing.get('score')}")
                print(f"     * recommendation: {timing.get('recommendation')}")
                print(f"     * factors: {len(timing.get('factors', []))} 个")
            
            print("   ✅ 数据结构检查通过")
            
        except Exception as e:
            print(f"   ❌ 数据结构检查失败: {e}")
            results["errors"].append(f"数据结构检查: {str(e)}")
    
    # 7. 总结
    print("\n" + "=" * 60)
    print("检查总结")
    print("=" * 60)
    
    all_checks = [
        ("akshare 模块", results["akshare_module"]),
        ("akshare_data_source 模块", results["akshare_data_source"]),
        ("InteractiveMarketAnalyzer 类", results["interactive_analyzer"]),
        ("akshare 实例", results["akshare_instance"]),
        ("接口测试", results["test_result"] and results["test_result"].get("success")),
    ]
    
    for check_name, status in all_checks:
        status_str = "✅ 通过" if status else "❌ 失败"
        print(f"{check_name}: {status_str}")
    
    if results["errors"]:
        print(f"\n⚠️ 发现 {len(results['errors'])} 个错误:")
        for i, error in enumerate(results["errors"], 1):
            print(f"   {i}. {error}")
    else:
        print("\n✅ 所有检查通过！接口可用。")
    
    return results


if __name__ == "__main__":
    results = check_interface_availability()
    
    # 返回退出码
    if results["errors"]:
        sys.exit(1)
    else:
        sys.exit(0)

