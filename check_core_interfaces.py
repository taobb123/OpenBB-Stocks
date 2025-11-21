"""
检查核心接口失败情况
诊断报告生成所需的关键接口
"""

import sys
import os
import traceback
from typing import Dict, List, Any

def check_core_interfaces():
    """检查核心接口状态"""
    print("=" * 60)
    print("核心接口诊断报告")
    print("=" * 60)
    print()
    
    results = {
        "akshare_available": False,
        "interfaces": {}
    }
    
    # 1. 检查 akshare 是否可用
    print("1. 检查 akshare 模块...")
    try:
        import akshare as ak
        results["akshare_available"] = True
        print("   ✅ akshare 模块可用")
    except ImportError as e:
        print(f"   ❌ akshare 模块不可用: {e}")
        return results
    
    # 2. 检查代理设置
    print("\n2. 检查网络代理设置...")
    http_proxy = os.environ.get("HTTP_PROXY", "")
    https_proxy = os.environ.get("HTTPS_PROXY", "")
    if http_proxy or https_proxy:
        print(f"   ⚠️ 检测到代理设置:")
        if http_proxy:
            print(f"      HTTP_PROXY: {http_proxy}")
        if https_proxy:
            print(f"      HTTPS_PROXY: {https_proxy}")
        print("   💡 提示: 如果代理无法连接，可能导致接口失败")
    else:
        print("   ✅ 未设置代理")
    
    # 3. 检查核心接口
    print("\n3. 检查核心接口...")
    
    test_symbol = "600519"  # 测试股票代码
    
    # 接口列表
    interfaces_to_check = [
        {
            "name": "历史数据接口",
            "methods": [
                {
                    "name": "stock_zh_a_hist (前复权)",
                    "func": lambda: ak.stock_zh_a_hist(
                        symbol=test_symbol,
                        period="daily",
                        start_date="20240101",
                        end_date="20241120",
                        adjust="qfq"
                    )
                },
                {
                    "name": "stock_zh_a_hist (不复权)",
                    "func": lambda: ak.stock_zh_a_hist(
                        symbol=test_symbol,
                        period="daily",
                        start_date="20240101",
                        end_date="20241120",
                        adjust=""
                    )
                }
            ]
        },
        {
            "name": "股票基本信息接口",
            "methods": [
                {
                    "name": "stock_individual_info_em",
                    "func": lambda: ak.stock_individual_info_em(symbol=test_symbol)
                },
                {
                    "name": "stock_zh_a_spot (新浪接口)",
                    "func": lambda: ak.stock_zh_a_spot()
                },
                {
                    "name": "stock_info_a_code_name",
                    "func": lambda: ak.stock_info_a_code_name()
                }
            ]
        },
        {
            "name": "基本面数据接口",
            "methods": [
                {
                    "name": "stock_financial_analysis_indicator",
                    "func": lambda: ak.stock_financial_analysis_indicator(symbol=test_symbol)
                },
                {
                    "name": "stock_financial_report_sina",
                    "func": lambda: ak.stock_financial_report_sina(stock=test_symbol, symbol="利润表")
                }
            ]
        }
    ]
    
    for interface_group in interfaces_to_check:
        group_name = interface_group["name"]
        print(f"\n   📊 {group_name}:")
        results["interfaces"][group_name] = {}
        
        for method in interface_group["methods"]:
            method_name = method["name"]
            print(f"      - {method_name}...", end=" ")
            
            try:
                result = method["func"]()
                
                # 检查结果
                if hasattr(result, 'empty'):
                    # DataFrame
                    if not result.empty:
                        print(f"✅ 成功 (获取到 {len(result)} 条数据)")
                        results["interfaces"][group_name][method_name] = {
                            "status": "success",
                            "data_count": len(result)
                        }
                    else:
                        print("⚠️ 返回空数据")
                        results["interfaces"][group_name][method_name] = {
                            "status": "empty",
                            "data_count": 0
                        }
                elif isinstance(result, (list, dict)):
                    # 列表或字典
                    if result:
                        print(f"✅ 成功 (获取到数据)")
                        results["interfaces"][group_name][method_name] = {
                            "status": "success",
                            "data_count": len(result) if isinstance(result, list) else "dict"
                        }
                    else:
                        print("⚠️ 返回空数据")
                        results["interfaces"][group_name][method_name] = {
                            "status": "empty",
                            "data_count": 0
                        }
                else:
                    print("✅ 成功")
                    results["interfaces"][group_name][method_name] = {
                        "status": "success"
                    }
                    
            except Exception as e:
                error_msg = str(e)
                # 检查是否是代理错误
                if "ProxyError" in error_msg or "proxy" in error_msg.lower():
                    print(f"❌ 失败 (代理错误)")
                    results["interfaces"][group_name][method_name] = {
                        "status": "proxy_error",
                        "error": error_msg[:100]  # 只保存前100个字符
                    }
                elif "push2" in error_msg.lower() or "eastmoney" in error_msg.lower():
                    print(f"❌ 失败 (网络连接错误)")
                    results["interfaces"][group_name][method_name] = {
                        "status": "network_error",
                        "error": error_msg[:100]
                    }
                else:
                    print(f"❌ 失败 ({error_msg[:50]})")
                    results["interfaces"][group_name][method_name] = {
                        "status": "error",
                        "error": error_msg[:100]
                    }
    
    # 4. 总结和建议
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    
    # 统计失败接口
    total_interfaces = 0
    failed_interfaces = 0
    proxy_errors = 0
    network_errors = 0
    
    for group_name, methods in results["interfaces"].items():
        for method_name, status in methods.items():
            total_interfaces += 1
            if status["status"] != "success":
                failed_interfaces += 1
                if status.get("status") == "proxy_error":
                    proxy_errors += 1
                elif status.get("status") == "network_error":
                    network_errors += 1
    
    print(f"\n接口统计:")
    print(f"  总接口数: {total_interfaces}")
    print(f"  成功: {total_interfaces - failed_interfaces}")
    print(f"  失败: {failed_interfaces}")
    if proxy_errors > 0:
        print(f"  ⚠️ 代理错误: {proxy_errors}")
    if network_errors > 0:
        print(f"  ⚠️ 网络错误: {network_errors}")
    
    # 给出建议
    print(f"\n💡 建议:")
    
    if proxy_errors > 0:
        print("   1. 代理连接问题:")
        print("      - 检查代理设置是否正确")
        print("      - 尝试禁用代理: 在代码中设置 os.environ.pop('HTTP_PROXY', None)")
        print("      - 或配置正确的代理地址")
    
    if network_errors > 0:
        print("   2. 网络连接问题:")
        print("      - push2.eastmoney.com 可能被封锁")
        print("      - 建议使用新浪接口 (stock_zh_a_spot)")
        print("      - 或使用其他备用接口")
    
    # 检查是否有可用的备用接口
    print("\n   3. 可用的备用接口:")
    available_backups = []
    for group_name, methods in results["interfaces"].items():
        for method_name, status in methods.items():
            if status["status"] == "success":
                if "sina" in method_name.lower() or "stock_zh_a_spot" in method_name:
                    available_backups.append(f"      ✅ {method_name}")
    
    if available_backups:
        for backup in available_backups:
            print(backup)
    else:
        print("      ⚠️ 未找到可用的备用接口")
    
    return results


if __name__ == "__main__":
    results = check_core_interfaces()
    
    # 返回退出码
    failed_count = sum(
        1 for group in results["interfaces"].values()
        for method in group.values()
        if method.get("status") != "success"
    )
    
    if failed_count > 0:
        print(f"\n⚠️ 发现 {failed_count} 个接口失败")
        sys.exit(1)
    else:
        print("\n✅ 所有接口正常")
        sys.exit(0)

