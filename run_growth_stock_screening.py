"""
成长板块股票筛选主程序
从文件读取基金池，筛选出共同增仓的成长板块股票
"""

import sys
import logging
from datetime import datetime
from growth_stock_screener import GrowthStockScreener
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'growth_stock_screening_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("成长板块股票筛选系统")
    print("="*80)
    
    # 1. 初始化筛选器
    screener = GrowthStockScreener()
    
    # 2. 从文件读取基金代码列表
    fund_file = "growth_stock.txt"
    print(f"\n📂 从文件读取基金代码: {fund_file}")
    
    fund_codes = screener.load_fund_codes_from_file(fund_file)
    
    if not fund_codes:
        print(f"❌ 未能从文件读取到基金代码，请检查文件: {fund_file}")
        return
    
    print(f"✅ 成功读取 {len(fund_codes)} 个基金代码: {fund_codes}")
    
    # 3. 设置分析参数
    use_latest_quarter = True  # 自动使用最新季度数据
    min_change = 0.0    # 最小增仓变化阈值（占净值比例）
    min_fund_count = 2  # 共同增仓的最少基金数量
    growth_min_fund_count = 2  # 成长板块股票的最少基金数量
    max_years_back = 2  # 最多向前查找的年数
    
    print(f"\n📊 分析参数:")
    if use_latest_quarter:
        print(f"  报告期: 自动使用最新季度数据")
    else:
        year_prev = "2022"  # 前一报告期年份
        year_curr = "2023"  # 当前报告期年份
        print(f"  报告期: {year_prev} -> {year_curr}")
    print(f"  最小增仓变化: {min_change}")
    print(f"  共同增仓最少基金数: {min_fund_count}")
    print(f"  成长板块最少基金数: {growth_min_fund_count}")
    
    # 4. 执行筛选
    print(f"\n🔍 开始筛选成长板块股票...")
    print("-" * 80)
    
    try:
        # 使用一站式方法：找出共同增仓的成长板块股票
        growth_stocks = screener.find_growth_stocks_from_funds(
            fund_codes=fund_codes,
            method='nav_ratio',
            min_change=min_change,
            min_fund_count=min_fund_count,
            growth_min_fund_count=growth_min_fund_count,
            use_latest_quarter=use_latest_quarter,
            max_years_back=max_years_back
        )
        
        if growth_stocks.empty:
            print(f"\n⚠️ 未找到符合条件的成长板块股票")
            print("\n可能的原因:")
            print("  1. 这些基金在指定年份没有共同增仓的股票")
            print("  2. 共同增仓的股票都不属于成长板块")
            print("  3. 可以尝试调整参数（如降低 min_fund_count）")
            return
        
        # 5. 添加行业信息
        print(f"\n📈 获取股票行业信息...")
        growth_stocks = screener.add_industry_info(growth_stocks)
        
        # 6. 显示结果
        print("\n" + "="*80)
        print(f"✅ 筛选完成！找到 {len(growth_stocks)} 只成长板块股票")
        print("="*80)
        
        # 按被增持基金数量排序
        growth_stocks = growth_stocks.sort_values('fund_count', ascending=False)
        
        # 显示主要信息
        print(f"\n📋 成长板块股票列表（按被增持基金数量排序）:")
        print("-" * 80)
        
        display_cols = ['stock_code', 'stock_name', 'fund_count', 'avg_change', 'total_change', '行业']
        available_cols = [col for col in display_cols if col in growth_stocks.columns]
        
        # 格式化显示
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 20)
        
        print(growth_stocks[available_cols].to_string(index=False))
        
        # 7. 显示详细信息（前10只）
        print(f"\n" + "="*80)
        print(f"📊 前10只成长板块股票详细信息:")
        print("="*80)
        
        for idx, (_, row) in enumerate(growth_stocks.head(10).iterrows(), 1):
            print(f"\n【{idx}】{row['stock_code']} - {row['stock_name']}")
            print(f"  行业: {row.get('行业', 'N/A')}")
            print(f"  被 {row['fund_count']} 只基金增持")
            print(f"  平均增仓变化: {row['avg_change']:.4f}%")
            print(f"  总增仓变化: {row['total_change']:.4f}%")
            print(f"  最大增仓变化: {row['max_change']:.4f}%")
            print(f"  最小增仓变化: {row['min_change']:.4f}%")
            
            # 显示各基金增仓详情
            if 'funds_detail' in row and row['funds_detail']:
                print(f"  各基金增仓详情:")
                for fund_info in row['funds_detail'][:5]:  # 只显示前5个
                    print(f"    - 基金 {fund_info['fund_code']}: "
                          f"变化 {fund_info['change']:.4f}% "
                          f"({fund_info['change_pct']:.2f}%)")
                if len(row['funds_detail']) > 5:
                    print(f"    ... 还有 {len(row['funds_detail']) - 5} 只基金")
        
        # 8. 保存结果到文件
        output_file = f"growth_stocks_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            # 准备保存的数据（移除funds_detail列，因为包含复杂结构）
            save_df = growth_stocks.copy()
            if 'funds_detail' in save_df.columns:
                save_df = save_df.drop(columns=['funds_detail'])
            
            save_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n💾 结果已保存到文件: {output_file}")
        except Exception as e:
            logger.warning(f"保存结果文件失败: {e}")
        
        # 9. 统计信息
        print(f"\n" + "="*80)
        print(f"📊 统计信息:")
        print("="*80)
        print(f"  总基金数量: {len(fund_codes)}")
        print(f"  成长板块股票数量: {len(growth_stocks)}")
        print(f"  平均被增持基金数: {growth_stocks['fund_count'].mean():.2f}")
        print(f"  最多被增持基金数: {growth_stocks['fund_count'].max()}")
        print(f"  平均增仓变化: {growth_stocks['avg_change'].mean():.4f}%")
        
        # 按行业统计
        if '行业' in growth_stocks.columns:
            industry_stats = growth_stocks['行业'].value_counts()
            print(f"\n  行业分布:")
            for industry, count in industry_stats.head(10).items():
                if industry and industry != '':
                    print(f"    {industry}: {count} 只")
        
    except Exception as e:
        print(f"\n❌ 筛选过程出错: {e}")
        logger.error(f"筛选过程出错", exc_info=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

