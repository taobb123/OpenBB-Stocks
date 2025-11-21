"""
测试多基金共同增仓股票筛选功能
"""

import sys
import logging
from fund_holdings_analyzer import FundHoldingsAnalyzer
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_analyze_multiple_funds_increased_holdings():
    """测试分析多只基金的增仓股票"""
    print("\n" + "="*60)
    print("测试1: 分析多只基金的增仓股票")
    print("="*60)
    
    analyzer = FundHoldingsAnalyzer()
    
    # 关注的基金池
    fund_codes = ["005827", "005669", "161725"]  # 易方达蓝筹精选、易方达消费行业、招商中证白酒
    year_prev = "2022"
    year_curr = "2023"
    
    try:
        results = analyzer.analyze_multiple_funds_increased_holdings(
            fund_codes, year_prev, year_curr, method='nav_ratio', min_change=0.0
        )
        
        print(f"\n✅ 成功分析 {len(fund_codes)} 只基金的增仓股票")
        
        for fund_code, increased_df in results.items():
            print(f"\n基金 {fund_code}:")
            if not increased_df.empty:
                print(f"  共 {len(increased_df)} 只增仓股票")
                print(f"  前5只增仓股票:")
                print(increased_df.head().to_string())
            else:
                print(f"  无增仓股票数据")
                
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_find_common_increased_stocks():
    """测试找出共同增仓股票"""
    print("\n" + "="*60)
    print("测试2: 找出多只基金共同增仓的股票")
    print("="*60)
    
    analyzer = FundHoldingsAnalyzer()
    
    # 关注的基金池
    fund_codes = ["005827", "005669", "161725"]
    year_prev = "2022"
    year_curr = "2023"
    
    try:
        common_stocks = analyzer.find_common_increased_stocks(
            fund_codes, 
            year_prev, 
            year_curr, 
            method='nav_ratio',
            min_change=0.0,
            min_fund_count=2  # 至少被2只基金增持
        )
        
        if not common_stocks.empty:
            print(f"\n✅ 找到 {len(common_stocks)} 只共同增仓股票")
            print(f"\n共同增仓股票列表（按被增持基金数量排序）:")
            
            # 显示主要信息
            display_cols = ['stock_code', 'stock_name', 'fund_count', 'avg_change', 'total_change']
            available_cols = [col for col in display_cols if col in common_stocks.columns]
            
            print(common_stocks[available_cols].to_string())
            
            # 显示详细信息（前3只）
            print(f"\n前3只共同增仓股票的详细信息:")
            for idx, row in common_stocks.head(3).iterrows():
                print(f"\n股票: {row['stock_code']} ({row['stock_name']})")
                print(f"  被 {row['fund_count']} 只基金增持")
                print(f"  平均增仓变化: {row['avg_change']:.4f}")
                print(f"  总增仓变化: {row['total_change']:.4f}")
                print(f"  各基金增仓详情:")
                for fund_info in row['funds_detail']:
                    print(f"    - 基金 {fund_info['fund_code']}: 变化 {fund_info['change']:.4f} "
                          f"({fund_info['change_pct']:.2f}%)")
        else:
            print(f"\n⚠️ 未找到共同增仓股票")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_get_stock_fund_details():
    """测试获取单只股票的详细信息"""
    print("\n" + "="*60)
    print("测试3: 获取单只股票的详细信息")
    print("="*60)
    
    analyzer = FundHoldingsAnalyzer()
    
    fund_codes = ["005827", "005669", "161725"]
    year_prev = "2022"
    year_curr = "2023"
    
    try:
        # 先获取共同增仓股票
        common_stocks = analyzer.find_common_increased_stocks(
            fund_codes, year_prev, year_curr, min_fund_count=2
        )
        
        if not common_stocks.empty:
            # 获取第一只股票的详细信息
            first_stock = common_stocks.iloc[0]['stock_code']
            details = analyzer.get_stock_fund_details(first_stock, common_stocks)
            
            if details:
                print(f"\n✅ 股票 {first_stock} 的详细信息:")
                print(f"  股票名称: {details['stock_name']}")
                print(f"  被增持基金数量: {details['fund_count']}")
                print(f"  平均增仓变化: {details['avg_change']:.4f}")
                print(f"  总增仓变化: {details['total_change']:.4f}")
                print(f"  最大增仓变化: {details['max_change']:.4f}")
                print(f"  最小增仓变化: {details['min_change']:.4f}")
                print(f"  各基金增仓详情:")
                for fund_info in details['funds']:
                    print(f"    - 基金 {fund_info['fund_code']}: "
                          f"变化 {fund_info['change']:.4f} "
                          f"({fund_info['change_pct']:.2f}%)")
            else:
                print(f"\n⚠️ 未找到股票详细信息")
        else:
            print(f"\n⚠️ 未找到共同增仓股票，无法测试")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_with_different_parameters():
    """测试不同参数设置"""
    print("\n" + "="*60)
    print("测试4: 使用不同参数筛选共同增仓股票")
    print("="*60)
    
    analyzer = FundHoldingsAnalyzer()
    
    fund_codes = ["005827", "005669", "161725"]
    year_prev = "2022"
    year_curr = "2023"
    
    # 测试1: 要求至少被3只基金增持
    print("\n--- 测试: 至少被3只基金增持 ---")
    try:
        common_stocks = analyzer.find_common_increased_stocks(
            fund_codes, year_prev, year_curr, 
            min_fund_count=3  # 要求所有基金都增持
        )
        print(f"找到 {len(common_stocks)} 只被至少3只基金增持的股票")
        if not common_stocks.empty:
            print(common_stocks[['stock_code', 'stock_name', 'fund_count']].to_string())
    except Exception as e:
        print(f"测试失败: {e}")
    
    # 测试2: 设置最小变化阈值
    print("\n--- 测试: 最小增仓变化阈值 0.5% ---")
    try:
        common_stocks = analyzer.find_common_increased_stocks(
            fund_codes, year_prev, year_curr, 
            min_change=0.5,  # 占净值比例至少增加0.5%
            min_fund_count=2
        )
        print(f"找到 {len(common_stocks)} 只符合条件的共同增仓股票")
        if not common_stocks.empty:
            print(common_stocks[['stock_code', 'stock_name', 'fund_count', 'avg_change']].to_string())
    except Exception as e:
        print(f"测试失败: {e}")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试多基金共同增仓股票筛选功能")
    print("="*60)
    
    # 运行所有测试
    test_analyze_multiple_funds_increased_holdings()
    test_find_common_increased_stocks()
    test_get_stock_fund_details()
    test_with_different_parameters()
    
    print("\n" + "="*60)
    print("所有测试完成")
    print("="*60)


if __name__ == "__main__":
    main()

