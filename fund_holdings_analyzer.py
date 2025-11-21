"""
基金持仓分析模块
负责分析单只基金的持仓变化，识别增仓股票
"""

import pandas as pd
from typing import Optional, List, Dict, Tuple
import logging
from fund_data_fetcher import FundDataFetcher

logger = logging.getLogger(__name__)


class FundHoldingsAnalyzer:
    """基金持仓分析器"""
    
    def __init__(self, data_fetcher: Optional[FundDataFetcher] = None):
        """
        初始化分析器
        
        Args:
            data_fetcher: 数据获取器实例，如果为None则创建新实例
        """
        self.data_fetcher = data_fetcher or FundDataFetcher()
    
    def _find_key_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        自动识别DataFrame中的关键列
        
        Returns:
            包含关键列名的字典
        """
        columns = {
            'stock_code': None,  # 股票代码
            'stock_name': None,  # 股票名称
            'nav_ratio': None,   # 占净值比例
            'market_value': None, # 持仓市值
            'shares': None,      # 持股数
            'period': None       # 报告期
        }
        
        # 查找股票代码列
        for col in df.columns:
            col_lower = col.lower()
            if '股票代码' in col or '代码' in col or 'symbol' in col_lower or 'code' in col_lower:
                columns['stock_code'] = col
                break
        
        # 查找股票名称列
        for col in df.columns:
            col_lower = col.lower()
            if '股票名称' in col or '名称' in col or 'name' in col_lower:
                columns['stock_name'] = col
                break
        
        # 查找占净值比例列
        for col in df.columns:
            if '占净值比例' in col or '净值比例' in col or '比例' in col:
                columns['nav_ratio'] = col
                break
        
        # 查找持仓市值列
        for col in df.columns:
            if '持仓市值' in col or '市值' in col or 'market_value' in col.lower():
                columns['market_value'] = col
                break
        
        # 查找持股数列
        for col in df.columns:
            if '持股数' in col or '持股' in col or 'shares' in col_lower:
                columns['shares'] = col
                break
        
        # 查找报告期列
        for col in df.columns:
            if '报告期' in col or '日期' in col or 'period' in col.lower():
                columns['period'] = col
                break
        
        return columns
    
    def analyze_holdings_change(
        self,
        holdings_prev: pd.DataFrame,
        holdings_curr: pd.DataFrame,
        method: str = 'nav_ratio'
    ) -> pd.DataFrame:
        """
        分析两个报告期之间的持仓变化
        
        Args:
            holdings_prev: 前一报告期的持仓数据
            holdings_curr: 当前报告期的持仓数据
            method: 比较方法，'nav_ratio'（占净值比例）或 'market_value'（持仓市值），默认'nav_ratio'
        
        Returns:
            包含持仓变化信息的DataFrame，包括增仓、减仓、新进、退出等
        """
        if holdings_prev.empty or holdings_curr.empty:
            logger.warning("持仓数据为空，无法进行比较")
            return pd.DataFrame()
        
        # 识别关键列
        cols_prev = self._find_key_columns(holdings_prev)
        cols_curr = self._find_key_columns(holdings_curr)
        
        stock_code_col_prev = cols_prev['stock_code']
        stock_code_col_curr = cols_curr['stock_code']
        
        if stock_code_col_prev is None or stock_code_col_curr is None:
            logger.error("无法找到股票代码列")
            return pd.DataFrame()
        
        # 确定比较列
        if method == 'nav_ratio':
            compare_col_prev = cols_prev['nav_ratio']
            compare_col_curr = cols_curr['nav_ratio']
        else:
            compare_col_prev = cols_prev['market_value']
            compare_col_curr = cols_curr['market_value']
        
        if compare_col_prev is None or compare_col_curr is None:
            logger.error(f"无法找到{method}列")
            return pd.DataFrame()
        
        # 确保比较列为数值类型
        holdings_prev[compare_col_prev] = pd.to_numeric(
            holdings_prev[compare_col_prev], 
            errors='coerce'
        )
        holdings_curr[compare_col_curr] = pd.to_numeric(
            holdings_curr[compare_col_curr], 
            errors='coerce'
        )
        
        # 合并数据
        merged = pd.merge(
            holdings_prev[[stock_code_col_prev, compare_col_prev]].rename(
                columns={stock_code_col_prev: 'stock_code', compare_col_prev: f'{method}_prev'}
            ),
            holdings_curr[[stock_code_col_curr, compare_col_curr]].rename(
                columns={stock_code_col_curr: 'stock_code', compare_col_curr: f'{method}_curr'}
            ),
            on='stock_code',
            how='outer'
        )
        
        # 填充缺失值
        merged[f'{method}_prev'] = merged[f'{method}_prev'].fillna(0)
        merged[f'{method}_curr'] = merged[f'{method}_curr'].fillna(0)
        
        # 计算变化
        merged['change'] = merged[f'{method}_curr'] - merged[f'{method}_prev']
        merged['change_pct'] = merged.apply(
            lambda row: (row['change'] / row[f'{method}_prev'] * 100) 
            if row[f'{method}_prev'] > 0 else float('inf'),
            axis=1
        )
        
        # 标记变化类型
        merged['change_type'] = merged.apply(
            lambda row: '新进' if row[f'{method}_prev'] == 0 and row[f'{method}_curr'] > 0
            else '退出' if row[f'{method}_prev'] > 0 and row[f'{method}_curr'] == 0
            else '增仓' if row['change'] > 0
            else '减仓' if row['change'] < 0
            else '持平',
            axis=1
        )
        
        # 添加股票名称（如果可用）
        if cols_curr['stock_name']:
            name_map = dict(zip(
                holdings_curr[stock_code_col_curr],
                holdings_curr[cols_curr['stock_name']]
            ))
            merged['stock_name'] = merged['stock_code'].map(name_map)
        
        return merged
    
    def get_increased_holdings(
        self,
        holdings_prev: pd.DataFrame,
        holdings_curr: pd.DataFrame,
        method: str = 'nav_ratio',
        min_change: float = 0.0
    ) -> pd.DataFrame:
        """
        获取增仓的股票列表
        
        Args:
            holdings_prev: 前一报告期的持仓数据
            holdings_curr: 当前报告期的持仓数据
            method: 比较方法，'nav_ratio'或'market_value'
            min_change: 最小变化阈值，只返回变化大于此值的股票
        
        Returns:
            增仓股票DataFrame，按变化量降序排列
        """
        changes = self.analyze_holdings_change(holdings_prev, holdings_curr, method)
        
        if changes.empty:
            return pd.DataFrame()
        
        # 筛选增仓股票（包括新进）
        increased = changes[
            (changes['change_type'].isin(['增仓', '新进'])) & 
            (changes['change'] > min_change)
        ]
        
        # 按变化量降序排序
        increased = increased.sort_values('change', ascending=False)
        
        return increased
    
    def get_latest_quarters_info(
        self,
        fund_codes: List[str],
        max_years_back: int = 2
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        获取基金池的最新可用季度信息
        
        Args:
            fund_codes: 基金代码列表
            max_years_back: 最多向前查找的年数，默认2年
        
        Returns:
            (最新季度年份, 最新季度报告期, 上一季度年份, 上一季度报告期) 元组
        """
        # 使用第一只基金来检测最新季度（假设所有基金的数据可用性相似）
        if not fund_codes:
            return None, None, None, None
        
        sample_fund = fund_codes[0]
        latest_info = self.data_fetcher.get_latest_available_quarter(sample_fund, max_years_back)
        
        if latest_info is None:
            return None, None, None, None
        
        latest_year, latest_period = latest_info
        
        # 解析最新季度日期
        latest_date = self.data_fetcher._parse_report_date(latest_period)
        if latest_date is None:
            return latest_year, latest_period, None, None
        
        # 计算上一季度
        # 季度对应：Q1(3月31日), Q2(6月30日), Q3(9月30日), Q4(12月31日)
        if latest_date.month == 3:  # Q1 -> 上一季度是去年Q4
            prev_date = latest_date.replace(year=latest_date.year - 1, month=12, day=31)
        elif latest_date.month == 6:  # Q2 -> 上一季度是Q1
            prev_date = latest_date.replace(month=3, day=31)
        elif latest_date.month == 9:  # Q3 -> 上一季度是Q2
            prev_date = latest_date.replace(month=6, day=30)
        else:  # Q4 -> 上一季度是Q3
            prev_date = latest_date.replace(month=9, day=30)
        
        prev_year = str(prev_date.year)
        # 尝试获取上一季度的实际报告期字符串
        try:
            prev_holdings = self.data_fetcher.get_fund_holdings(sample_fund, prev_year)
            if not prev_holdings.empty:
                period_col = self.data_fetcher._find_report_period_column(prev_holdings)
                if period_col:
                    # 找到最接近上一季度日期的报告期
                    prev_periods = prev_holdings[period_col].unique()
                    closest_period = None
                    min_diff = float('inf')
                    for period in prev_periods:
                        period_dt = self.data_fetcher._parse_report_date(str(period))
                        if period_dt:
                            diff = abs((period_dt - prev_date).days)
                            if diff < min_diff:
                                min_diff = diff
                                closest_period = str(period)
                    if closest_period:
                        return latest_year, latest_period, prev_year, closest_period
        except:
            pass
        
        # 如果无法获取，使用计算的日期
        prev_period = prev_date.strftime("%Y-%m-%d")
        return latest_year, latest_period, prev_year, prev_period
    
    def analyze_fund_holdings_change(
        self,
        fund_code: str,
        year_prev: str,
        year_curr: str,
        method: str = 'nav_ratio',
        use_latest_quarter: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        分析单只基金在两个年份之间的持仓变化
        
        Args:
            fund_code: 基金代码
            year_prev: 前一报告期年份（当use_latest_quarter=False时使用）
            year_curr: 当前报告期年份（当use_latest_quarter=False时使用）
            method: 比较方法
            use_latest_quarter: 是否使用最新季度，默认False
        
        Returns:
            (持仓变化DataFrame, 增仓股票DataFrame)
        """
        # 如果使用最新季度，自动获取
        if use_latest_quarter:
            latest_info = self.data_fetcher.get_latest_available_quarter(fund_code)
            if latest_info:
                year_curr, period_curr = latest_info
                # 获取当前季度的数据
                holdings_curr, _ = self.data_fetcher.get_fund_holdings_by_latest_quarter(fund_code)
                
                # 计算上一季度
                latest_date = self.data_fetcher._parse_report_date(period_curr)
                if latest_date:
                    if latest_date.month == 3:
                        prev_date = latest_date.replace(year=latest_date.year - 1, month=12, day=31)
                    elif latest_date.month == 6:
                        prev_date = latest_date.replace(month=3, day=31)
                    elif latest_date.month == 9:
                        prev_date = latest_date.replace(month=6, day=30)
                    else:
                        prev_date = latest_date.replace(month=9, day=30)
                    
                    year_prev = str(prev_date.year)
                    # 获取上一季度的数据
                    holdings_prev = self.data_fetcher.get_fund_holdings(fund_code, year_prev, use_latest_quarter=False)
                    
                    # 如果有报告期列，筛选出上一季度的数据
                    if not holdings_prev.empty:
                        period_col = self.data_fetcher._find_report_period_column(holdings_prev)
                        if period_col:
                            # 找到最接近的上一季度报告期
                            prev_periods = holdings_prev[period_col].unique()
                            closest_period = None
                            min_diff = float('inf')
                            for period in prev_periods:
                                period_dt = self.data_fetcher._parse_report_date(str(period))
                                if period_dt:
                                    diff = abs((period_dt - prev_date).days)
                                    if diff < min_diff:
                                        min_diff = diff
                                        closest_period = str(period)
                            if closest_period:
                                holdings_prev = holdings_prev[holdings_prev[period_col].astype(str) == closest_period]
                else:
                    holdings_prev = self.data_fetcher.get_fund_holdings(fund_code, year_prev, use_latest_quarter=False)
            else:
                holdings_prev = pd.DataFrame()
                holdings_curr = pd.DataFrame()
        else:
            # 获取两个报告期的数据
            holdings_prev = self.data_fetcher.get_fund_holdings(fund_code, year_prev)
            holdings_curr = self.data_fetcher.get_fund_holdings(fund_code, year_curr)
        
        if holdings_prev.empty or holdings_curr.empty:
            logger.warning(f"基金 {fund_code} 在指定报告期没有数据")
            return pd.DataFrame(), pd.DataFrame()
        
        # 如果有报告期列，需要筛选出最新的季度数据
        # 这里简化处理，取每个年份的最后一条记录（假设按时间排序）
        # 实际使用时可能需要根据报告期列进行更精确的筛选
        
        # 分析变化
        changes = self.analyze_holdings_change(holdings_prev, holdings_curr, method)
        increased = self.get_increased_holdings(holdings_prev, holdings_curr, method)
        
        return changes, increased
    
    def analyze_multiple_funds_increased_holdings(
        self,
        fund_codes: List[str],
        year_prev: str,
        year_curr: str,
        method: str = 'nav_ratio',
        min_change: float = 0.0,
        use_latest_quarter: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        分析多只基金的增仓股票列表
        
        Args:
            fund_codes: 基金代码列表
            year_prev: 前一报告期年份
            year_curr: 当前报告期年份
            method: 比较方法，'nav_ratio'或'market_value'
            min_change: 最小变化阈值
        
        Returns:
            字典，key为基金代码，value为该基金的增仓股票DataFrame
        """
        results = {}
        
        for fund_code in fund_codes:
            try:
                logger.info(f"正在分析基金 {fund_code} 的增仓股票...")
                _, increased = self.analyze_fund_holdings_change(
                    fund_code, year_prev, year_curr, method, use_latest_quarter
                )
                
                # 应用最小变化阈值
                if not increased.empty and min_change > 0:
                    increased = increased[increased['change'] >= min_change]
                
                results[fund_code] = increased
                logger.info(f"基金 {fund_code} 共有 {len(increased)} 只增仓股票")
                
            except Exception as e:
                logger.error(f"分析基金 {fund_code} 增仓股票失败: {e}")
                results[fund_code] = pd.DataFrame()
        
        return results
    
    def find_common_increased_stocks(
        self,
        fund_codes: List[str],
        year_prev: str = None,
        year_curr: str = None,
        method: str = 'nav_ratio',
        min_change: float = 0.0,
        min_fund_count: int = 2,
        use_latest_quarter: bool = False,
        max_years_back: int = 2
    ) -> pd.DataFrame:
        """
        找出多只基金共同增仓的股票
        
        Args:
            fund_codes: 基金代码列表
            year_prev: 前一报告期年份（当use_latest_quarter=False时使用）
            year_curr: 当前报告期年份（当use_latest_quarter=False时使用）
            method: 比较方法，'nav_ratio'或'market_value'
            min_change: 最小变化阈值
            min_fund_count: 最少被多少只基金增持才纳入统计，默认2只
            use_latest_quarter: 是否使用最新季度，默认False
            max_years_back: 当use_latest_quarter=True时，最多向前查找的年数，默认2年
        
        Returns:
            共同增仓股票DataFrame，包含股票代码、股票名称、被增持的基金数量、
            各基金的增仓变化等信息，按被增持基金数量降序排列
        """
        # 如果使用最新季度，自动获取季度信息
        if use_latest_quarter:
            latest_year, latest_period, prev_year, prev_period = self.get_latest_quarters_info(
                fund_codes, max_years_back
            )
            if latest_year and prev_year:
                year_prev = prev_year
                year_curr = latest_year
                logger.info(f"自动使用最新季度: {prev_period} -> {latest_period}")
            else:
                logger.warning("无法获取最新季度信息，使用指定年份")
        
        if not year_prev or not year_curr:
            logger.error("缺少报告期年份信息")
            return pd.DataFrame()
        
        logger.info(f"开始分析 {len(fund_codes)} 只基金的共同增仓股票...")
        logger.info(f"报告期: {year_prev} -> {year_curr}")
        
        # 获取每只基金的增仓股票
        fund_increased_holdings = self.analyze_multiple_funds_increased_holdings(
            fund_codes, year_prev, year_curr, method, min_change, use_latest_quarter
        )
        
        # 统计每只股票出现在多少只基金的增仓列表中
        stock_fund_map = {}  # {stock_code: {fund_code: change_data}}
        
        for fund_code, increased_df in fund_increased_holdings.items():
            if increased_df.empty:
                continue
            
            # 获取股票代码列
            stock_code_col = None
            for col in increased_df.columns:
                if col == 'stock_code' or '股票代码' in col or '代码' in col:
                    stock_code_col = col
                    break
            
            if stock_code_col is None:
                logger.warning(f"基金 {fund_code} 的增仓数据中未找到股票代码列")
                continue
            
            # 遍历每只增仓股票
            for _, row in increased_df.iterrows():
                stock_code = str(row[stock_code_col])
                
                if stock_code not in stock_fund_map:
                    stock_fund_map[stock_code] = {
                        'stock_code': stock_code,
                        'stock_name': row.get('stock_name', ''),
                        'fund_count': 0,
                        'funds': [],
                        'total_change': 0.0,
                        'avg_change': 0.0,
                        'max_change': 0.0,
                        'min_change': float('inf')
                    }
                
                # 记录该基金对该股票的增仓信息
                change_value = row.get('change', 0.0)
                stock_fund_map[stock_code]['fund_count'] += 1
                stock_fund_map[stock_code]['funds'].append({
                    'fund_code': fund_code,
                    'change': change_value,
                    'change_pct': row.get('change_pct', 0.0),
                    'nav_ratio_curr': row.get('nav_ratio_curr', 0.0) if method == 'nav_ratio' else row.get('market_value_curr', 0.0)
                })
                stock_fund_map[stock_code]['total_change'] += change_value
                stock_fund_map[stock_code]['max_change'] = max(
                    stock_fund_map[stock_code]['max_change'], 
                    change_value
                )
                stock_fund_map[stock_code]['min_change'] = min(
                    stock_fund_map[stock_code]['min_change'], 
                    change_value
                )
        
        # 计算平均变化
        for stock_code in stock_fund_map:
            fund_count = stock_fund_map[stock_code]['fund_count']
            if fund_count > 0:
                stock_fund_map[stock_code]['avg_change'] = (
                    stock_fund_map[stock_code]['total_change'] / fund_count
                )
            if stock_fund_map[stock_code]['min_change'] == float('inf'):
                stock_fund_map[stock_code]['min_change'] = 0.0
        
        # 转换为DataFrame
        common_stocks = []
        for stock_code, data in stock_fund_map.items():
            if data['fund_count'] >= min_fund_count:
                common_stocks.append({
                    'stock_code': data['stock_code'],
                    'stock_name': data['stock_name'],
                    'fund_count': data['fund_count'],
                    'total_change': data['total_change'],
                    'avg_change': data['avg_change'],
                    'max_change': data['max_change'],
                    'min_change': data['min_change'],
                    'funds_detail': data['funds']
                })
        
        if not common_stocks:
            logger.warning(f"未找到被至少 {min_fund_count} 只基金共同增持的股票")
            return pd.DataFrame()
        
        # 创建DataFrame并按被增持基金数量降序排列
        result_df = pd.DataFrame(common_stocks)
        result_df = result_df.sort_values('fund_count', ascending=False)
        
        logger.info(f"找到 {len(result_df)} 只共同增仓股票")
        
        return result_df
    
    def get_stock_fund_details(
        self,
        stock_code: str,
        common_stocks_df: pd.DataFrame
    ) -> Dict:
        """
        获取某只股票在共同增仓列表中的详细信息
        
        Args:
            stock_code: 股票代码
            common_stocks_df: 共同增仓股票DataFrame（由find_common_increased_stocks返回）
        
        Returns:
            包含该股票详细信息的字典
        """
        if common_stocks_df.empty:
            return {}
        
        stock_row = common_stocks_df[common_stocks_df['stock_code'] == stock_code]
        
        if stock_row.empty:
            return {}
        
        row = stock_row.iloc[0]
        return {
            'stock_code': row['stock_code'],
            'stock_name': row['stock_name'],
            'fund_count': row['fund_count'],
            'total_change': row['total_change'],
            'avg_change': row['avg_change'],
            'max_change': row['max_change'],
            'min_change': row['min_change'],
            'funds': row['funds_detail']
        }

