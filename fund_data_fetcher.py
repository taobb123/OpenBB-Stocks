"""
基金持仓数据获取模块
负责从 akshare 获取基金持仓数据
"""

import akshare as ak
import pandas as pd
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger(__name__)


class FundDataFetcher:
    """基金数据获取器"""
    
    def __init__(self):
        """初始化数据获取器"""
        pass
    
    def _parse_report_date(self, date_str: str) -> Optional[datetime]:
        """
        解析报告期日期字符串
        
        Args:
            date_str: 日期字符串，可能是 "2024-09-30"、"20240930"、"2024Q3" 等格式
        
        Returns:
            datetime对象，如果解析失败返回None
        """
        if pd.isna(date_str) or not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # 尝试多种日期格式
        formats = [
            "%Y-%m-%d",
            "%Y%m%d",
            "%Y/%m/%d",
            "%Y-%m-%d %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        # 尝试解析季度格式 "2024Q3"
        quarter_match = re.match(r'(\d{4})[Qq](\d)', date_str)
        if quarter_match:
            year = int(quarter_match.group(1))
            quarter = int(quarter_match.group(2))
            # 季度对应的月末日期：Q1=3月31日, Q2=6月30日, Q3=9月30日, Q4=12月31日
            quarter_end_dates = {
                1: (3, 31),
                2: (6, 30),
                3: (9, 30),
                4: (12, 31)
            }
            if quarter in quarter_end_dates:
                month, day = quarter_end_dates[quarter]
                try:
                    return datetime(year, month, day)
                except:
                    pass
        
        return None
    
    def _find_report_period_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        查找报告期列名
        
        Args:
            df: DataFrame
        
        Returns:
            报告期列名，如果未找到返回None
        """
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in ['报告期', '日期', 'period', 'date', '报告日期']):
                return col
        return None
    
    def get_latest_available_quarter(
        self, 
        fund_code: str, 
        max_years_back: int = 2
    ) -> Optional[Tuple[str, str]]:
        """
        获取基金最新的可用季度数据
        
        Args:
            fund_code: 基金代码
            max_years_back: 最多向前查找的年数，默认2年
        
        Returns:
            (年份, 报告期字符串) 元组，如果未找到返回None
        """
        current_year = datetime.now().year
        start_year = current_year - max_years_back
        
        latest_date = None
        latest_period_str = None
        
        # 从当前年份向前查找
        for year in range(current_year, start_year - 1, -1):
            try:
                logger.debug(f"检查基金 {fund_code} 在 {year} 年的数据...")
                holdings = ak.fund_portfolio_hold_em(symbol=fund_code, date=str(year))
                
                if holdings.empty:
                    continue
                
                # 查找报告期列
                period_col = self._find_report_period_column(holdings)
                if period_col is None:
                    # 如果没有报告期列，假设是该年份的最新数据
                    if latest_date is None or datetime(year, 12, 31) > latest_date:
                        latest_date = datetime(year, 12, 31)
                        latest_period_str = f"{year}-12-31"
                    continue
                
                # 解析所有报告期日期，找到最新的
                for period in holdings[period_col].unique():
                    period_date = self._parse_report_date(str(period))
                    if period_date and (latest_date is None or period_date > latest_date):
                        latest_date = period_date
                        latest_period_str = str(period)
            
            except Exception as e:
                logger.debug(f"获取基金 {fund_code} 在 {year} 年的数据失败: {e}")
                continue
        
        if latest_date:
            return (str(latest_date.year), latest_period_str)
        
        return None
    
    def get_fund_holdings_by_latest_quarter(
        self,
        fund_code: str,
        max_years_back: int = 2
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        获取基金最新季度的持仓数据
        
        Args:
            fund_code: 基金代码
            max_years_back: 最多向前查找的年数，默认2年
        
        Returns:
            (持仓DataFrame, 报告期字符串) 元组
        """
        # 获取最新可用季度
        latest_info = self.get_latest_available_quarter(fund_code, max_years_back)
        
        if latest_info is None:
            logger.warning(f"未找到基金 {fund_code} 的可用持仓数据")
            return pd.DataFrame(), None
        
        year, period_str = latest_info
        
        # 直接获取该年份的所有数据（避免递归调用）
        try:
            logger.debug(f"获取基金 {fund_code} 在 {year} 年的持仓数据...")
            holdings = ak.fund_portfolio_hold_em(symbol=fund_code, date=year)
            
            if holdings.empty:
                logger.warning(f"基金 {fund_code} 在 {year} 年没有持仓数据")
                return pd.DataFrame(), None
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 在 {year} 年的持仓数据失败: {e}")
            return pd.DataFrame(), None
        
        # 如果有报告期列，筛选出最新季度的数据
        period_col = self._find_report_period_column(holdings)
        if period_col and period_str:
            filtered = holdings[holdings[period_col].astype(str) == period_str]
            if not filtered.empty:
                logger.info(f"获取基金 {fund_code} 最新季度 {period_str} 的持仓数据，共 {len(filtered)} 条记录")
                return filtered, period_str
        
        # 如果没有报告期列或筛选失败，返回全部数据
        logger.info(f"获取基金 {fund_code} 在 {year} 年的持仓数据，共 {len(holdings)} 条记录")
        return holdings, period_str
    
    def get_fund_holdings(
        self, 
        fund_code: str, 
        date: Optional[str] = None,
        use_latest_quarter: bool = False,
        max_years_back: int = 2
    ) -> pd.DataFrame:
        """
        获取基金持仓数据
        
        Args:
            fund_code: 基金代码，例如 "005827"
            date: 报告期年份，格式为 "YYYY"，例如 "2023"。如果为None且use_latest_quarter=False，则使用当前年份
            use_latest_quarter: 是否自动使用最新可用季度，默认False。如果为True，会忽略date参数，自动查找最新季度
            max_years_back: 当use_latest_quarter=True时，最多向前查找的年数，默认2年
        
        Returns:
            包含基金持仓信息的DataFrame，包含股票代码、股票名称、持股数、持仓市值、占净值比例等
        """
        # 如果使用最新季度，自动查找
        if use_latest_quarter:
            holdings, period_str = self.get_fund_holdings_by_latest_quarter(
                fund_code, max_years_back
            )
            return holdings
        
        # 原有逻辑：按指定年份获取
        if date is None:
            date = datetime.now().strftime('%Y')
        
        try:
            logger.info(f"正在获取基金 {fund_code} 在 {date} 年的持仓数据...")
            holdings = ak.fund_portfolio_hold_em(symbol=fund_code, date=date)
            
            if holdings.empty:
                logger.warning(f"基金 {fund_code} 在 {date} 年没有持仓数据")
                return pd.DataFrame()
            
            logger.info(f"成功获取基金 {fund_code} 的持仓数据，共 {len(holdings)} 条记录")
            return holdings
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 持仓数据失败: {e}")
            raise
    
    def get_fund_top_holdings(
        self, 
        fund_code: str, 
        date: Optional[str] = None,
        top_n: int = 10,
        use_latest_quarter: bool = False,
        max_years_back: int = 2
    ) -> pd.DataFrame:
        """
        获取基金前N大重仓股
        
        Args:
            fund_code: 基金代码
            date: 报告期年份
            top_n: 返回前N大重仓股，默认10
            use_latest_quarter: 是否自动使用最新可用季度，默认False
            max_years_back: 当use_latest_quarter=True时，最多向前查找的年数，默认2年
        
        Returns:
            前N大重仓股DataFrame
        """
        holdings = self.get_fund_holdings(fund_code, date, use_latest_quarter, max_years_back)
        
        if holdings.empty:
            return pd.DataFrame()
        
        # 查找占净值比例列
        nav_ratio_col = None
        for col in holdings.columns:
            if '占净值比例' in col or '净值比例' in col or '比例' in col:
                nav_ratio_col = col
                break
        
        if nav_ratio_col is None:
            logger.warning(f"未找到占净值比例列，返回前{top_n}条数据")
            return holdings.head(top_n)
        
        # 确保占净值比例为数值类型
        holdings[nav_ratio_col] = pd.to_numeric(
            holdings[nav_ratio_col], 
            errors='coerce'
        )
        
        # 按占净值比例降序排序，取前N
        top_holdings = holdings.nlargest(top_n, nav_ratio_col)
        
        return top_holdings
    
    def get_multiple_funds_holdings(
        self, 
        fund_codes: List[str], 
        date: Optional[str] = None,
        use_latest_quarter: bool = False,
        max_years_back: int = 2
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多只基金的持仓数据
        
        Args:
            fund_codes: 基金代码列表
            date: 报告期年份
            use_latest_quarter: 是否自动使用最新可用季度，默认False
            max_years_back: 当use_latest_quarter=True时，最多向前查找的年数，默认2年
        
        Returns:
            字典，key为基金代码，value为持仓DataFrame
        """
        results = {}
        
        for fund_code in fund_codes:
            try:
                holdings = self.get_fund_holdings(fund_code, date, use_latest_quarter, max_years_back)
                results[fund_code] = holdings
            except Exception as e:
                logger.error(f"获取基金 {fund_code} 持仓失败: {e}")
                results[fund_code] = pd.DataFrame()
        
        return results
    
    def get_fund_holdings_by_quarters(
        self, 
        fund_code: str, 
        year: str
    ) -> Dict[str, pd.DataFrame]:
        """
        获取基金在指定年份的所有季度持仓数据
        
        注意：akshare的fund_portfolio_hold_em按年份返回数据，
        可能包含多个季度的数据，需要根据返回数据中的报告期字段进行筛选
        
        Args:
            fund_code: 基金代码
            year: 年份，例如 "2023"
        
        Returns:
            字典，key为报告期（如"2023Q1"），value为持仓DataFrame
        """
        holdings = self.get_fund_holdings(fund_code, year)
        
        if holdings.empty:
            return {}
        
        # 查找报告期列
        period_col = None
        for col in holdings.columns:
            if '报告期' in col or '日期' in col or 'period' in col.lower():
                period_col = col
                break
        
        if period_col is None:
            # 如果没有报告期列，返回全部数据，key为年份
            return {year: holdings}
        
        # 按报告期分组
        quarters_data = {}
        for period, group in holdings.groupby(period_col):
            quarters_data[str(period)] = group
        
        return quarters_data

