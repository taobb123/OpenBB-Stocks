"""
测试成长板块股票筛选功能
"""

import sys
import logging
from growth_stock_screener import GrowthStockScreener
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_load_fund_codes_from_file():
    """测试从文件读取基金代码"""
    print("\n" + "="*60)
    print("测试1: 从文件读取基金代码")
    print("="*60)
    
    screener = GrowthStockScreener()
    
    # 创建示例文件
    test_file = "test_fund_codes.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("# 这是注释行\n")
        f.write("005827\n")
        f.write("005669\n")
        f.write("161725\n")
        f.write("\n")  # 空行
        f.write("# 另一只基金\n")
        f.write("110022\n")
    
    try:
        fund_codes = screener.load_fund_codes_from_file(test_file)
        print(f"\n✅ 成功从文件读取 {len(fund_codes)} 个基金代码")
        print(f"基金代码列表: {fund_codes}")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理测试文件
        import os
        if os.path.exists(test_file):
            os.remove(test_file)


def test_is_growth_stock():
    """测试判断是否为成长板块股票"""
    print("\n" + "="*60)
    print("测试2: 判断是否为成长板块股票")
    print("="*60)
    
    screener = GrowthStockScreener()
    
    test_stocks = [
        ("600519", "贵州茅台"),  # 传统消费，非成长
        ("300750", "宁德时代"),  # 新能源，成长
        ("002129", "TCL中环"),   # 光伏，成长
        ("600036", "招商银行"),  # 金融，非成长
    ]
    
    for stock_code, stock_name in test_stocks:
        is_growth = screener.is_growth_stock(stock_code, stock_name)
        status = "✅ 成长板块" if is_growth else "❌ 非成长板块"
        print(f"{stock_code} ({stock_name}): {status}")


def test_find_growth_stocks_from_funds():
    """测试从基金池找出成长板块股票"""
    print("\n" + "="*60)
    print("测试3: 从基金池找出成长板块股票")
    print("="*60)
    
    screener = GrowthStockScreener()
    
    # 使用基金代码列表
    fund_codes = ["005827", "005669", "161725"]
    year_prev = "2022"
    year_curr = "2023"
    
    try:
        growth_stocks = screener.find_growth_stocks_from_funds(
            fund_codes,
            year_prev,
            year_curr,
            method='nav_ratio',
            min_change=0.0,
            min_fund_count=2,
            growth_min_fund_count=2
        )
        
        if not growth_stocks.empty:
            print(f"\n✅ 找到 {len(growth_stocks)} 只成长板块股票")
            print(f"\n成长板块股票列表:")
            
            # 添加行业信息
            growth_stocks = screener.add_industry_info(growth_stocks)
            
            # 显示主要信息
            display_cols = ['stock_code', 'stock_name', 'fund_count', 'avg_change', '行业']
            available_cols = [col for col in display_cols if col in growth_stocks.columns]
            
            print(growth_stocks[available_cols].to_string())
            
            # 显示详细信息（前5只）
            print(f"\n前5只成长板块股票的详细信息:")
            for idx, row in growth_stocks.head(5).iterrows():
                print(f"\n股票: {row['stock_code']} ({row['stock_name']})")
                print(f"  行业: {row.get('行业', 'N/A')}")
                print(f"  被 {row['fund_count']} 只基金增持")
                print(f"  平均增仓变化: {row['avg_change']:.4f}")
        else:
            print(f"\n⚠️ 未找到成长板块股票")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_from_file():
    """测试从文件读取基金代码并筛选成长板块股票"""
    print("\n" + "="*60)
    print("测试4: 从文件读取基金代码并筛选成长板块股票")
    print("="*60)
    
    screener = GrowthStockScreener()
    
    # 创建基金代码文件
    fund_file = "fund_codes.txt"
    with open(fund_file, 'w', encoding='utf-8') as f:
        f.write("# 关注的基金池\n")
        f.write("# 易方达蓝筹精选混合\n")
        f.write("005827\n")
        f.write("# 易方达消费行业股票\n")
        f.write("005669\n")
        f.write("# 招商中证白酒指数\n")
        f.write("161725\n")
    
    try:
        # 直接传入文件路径
        growth_stocks = screener.find_growth_stocks_from_funds(
            fund_file,  # 传入文件路径
            "2022",
            "2023",
            min_fund_count=2,
            growth_min_fund_count=2
        )
        
        if not growth_stocks.empty:
            print(f"\n✅ 从文件读取基金代码，找到 {len(growth_stocks)} 只成长板块股票")
            print(f"\n成长板块股票列表:")
            
            # 添加行业信息
            growth_stocks = screener.add_industry_info(growth_stocks)
            
            display_cols = ['stock_code', 'stock_name', 'fund_count', 'avg_change', '行业']
            available_cols = [col for col in display_cols if col in growth_stocks.columns]
            print(growth_stocks[available_cols].to_string())
        else:
            print(f"\n⚠️ 未找到成长板块股票")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理测试文件
        import os
        if os.path.exists(fund_file):
            os.remove(fund_file)


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试成长板块股票筛选功能")
    print("="*60)
    
    # 运行所有测试
    test_load_fund_codes_from_file()
    test_is_growth_stock()
    test_find_growth_stocks_from_funds()
    test_from_file()
    
    print("\n" + "="*60)
    print("所有测试完成")
    print("="*60)


if __name__ == "__main__":
    main()

