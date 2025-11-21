"""
测试基金数据获取功能
"""

import sys
import logging
from fund_data_fetcher import FundDataFetcher
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_get_fund_holdings():
    """测试获取基金持仓数据"""
    print("\n" + "="*60)
    print("测试1: 获取基金持仓数据")
    print("="*60)
    
    fetcher = FundDataFetcher()
    
    # 测试基金代码：易方达蓝筹精选混合 (005827)
    fund_code = "005827"
    date = "2023"
    
    try:
        holdings = fetcher.get_fund_holdings(fund_code, date)
        
        if not holdings.empty:
            print(f"\n✅ 成功获取基金 {fund_code} 在 {date} 年的持仓数据")
            print(f"   共 {len(holdings)} 条记录")
            print(f"\n数据列名: {list(holdings.columns)}")
            print(f"\n前5条数据:")
            print(holdings.head().to_string())
        else:
            print(f"\n⚠️ 基金 {fund_code} 在 {date} 年没有持仓数据")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_get_fund_top_holdings():
    """测试获取基金前N大重仓股"""
    print("\n" + "="*60)
    print("测试2: 获取基金前N大重仓股")
    print("="*60)
    
    fetcher = FundDataFetcher()
    
    fund_code = "005827"
    date = "2023"
    top_n = 10
    
    try:
        top_holdings = fetcher.get_fund_top_holdings(fund_code, date, top_n)
        
        if not top_holdings.empty:
            print(f"\n✅ 成功获取基金 {fund_code} 的前 {top_n} 大重仓股")
            print(f"   共 {len(top_holdings)} 条记录")
            print(f"\n前{top_n}大重仓股:")
            print(top_holdings.to_string())
        else:
            print(f"\n⚠️ 未获取到重仓股数据")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_get_multiple_funds_holdings():
    """测试批量获取多只基金的持仓数据"""
    print("\n" + "="*60)
    print("测试3: 批量获取多只基金的持仓数据")
    print("="*60)
    
    fetcher = FundDataFetcher()
    
    # 测试多只基金
    fund_codes = ["005827", "000001", "110022"]  # 易方达蓝筹精选、华夏成长、易方达消费行业
    date = "2023"
    
    try:
        results = fetcher.get_multiple_funds_holdings(fund_codes, date)
        
        print(f"\n✅ 批量获取完成")
        for fund_code, holdings in results.items():
            if not holdings.empty:
                print(f"\n基金 {fund_code}:")
                print(f"  共 {len(holdings)} 条持仓记录")
                print(f"  前3条数据:")
                print(holdings.head(3).to_string())
            else:
                print(f"\n基金 {fund_code}: 无数据")
                
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_get_fund_holdings_by_quarters():
    """测试获取基金按季度分组的持仓数据"""
    print("\n" + "="*60)
    print("测试4: 获取基金按季度分组的持仓数据")
    print("="*60)
    
    fetcher = FundDataFetcher()
    
    fund_code = "005827"
    year = "2023"
    
    try:
        quarters_data = fetcher.get_fund_holdings_by_quarters(fund_code, year)
        
        if quarters_data:
            print(f"\n✅ 成功获取基金 {fund_code} 在 {year} 年的季度数据")
            print(f"   共 {len(quarters_data)} 个报告期")
            
            for period, data in quarters_data.items():
                print(f"\n报告期 {period}:")
                print(f"  共 {len(data)} 条持仓记录")
                if not data.empty:
                    print(f"  前3条数据:")
                    print(data.head(3).to_string())
        else:
            print(f"\n⚠️ 未获取到季度数据")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_with_current_year():
    """测试使用当前年份（不指定date参数）"""
    print("\n" + "="*60)
    print("测试5: 使用当前年份获取基金持仓")
    print("="*60)
    
    fetcher = FundDataFetcher()
    
    fund_code = "005827"
    
    try:
        # 不指定date，应该使用当前年份
        holdings = fetcher.get_fund_holdings(fund_code)
        
        if not holdings.empty:
            print(f"\n✅ 成功获取基金 {fund_code} 的持仓数据（使用当前年份）")
            print(f"   共 {len(holdings)} 条记录")
            print(f"\n数据列名: {list(holdings.columns)}")
        else:
            print(f"\n⚠️ 基金 {fund_code} 在当前年份没有持仓数据")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试基金数据获取功能")
    print("="*60)
    
    # 运行所有测试
    test_get_fund_holdings()
    test_get_fund_top_holdings()
    test_get_multiple_funds_holdings()
    test_get_fund_holdings_by_quarters()
    test_with_current_year()
    
    print("\n" + "="*60)
    print("所有测试完成")
    print("="*60)


if __name__ == "__main__":
    main()

