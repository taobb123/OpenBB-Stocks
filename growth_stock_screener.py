"""
成长板块股票筛选模块
在共同增仓股票列表的基础上，筛选出属于成长板块的股票
"""

import pandas as pd
import akshare as ak
from typing import List, Dict, Optional
import logging
from fund_holdings_analyzer import FundHoldingsAnalyzer
import os

logger = logging.getLogger(__name__)


class GrowthStockScreener:
    """成长板块股票筛选器"""
    
    # 成长板块相关关键词（概念板块和行业）
    GROWTH_KEYWORDS = [
        # 科技类
        "芯片", "半导体", "集成电路", "国产芯片",
        "人工智能", "AI", "机器学习", "深度学习",
        "云计算", "大数据", "数据中心",
        "5G", "6G", "通信", "物联网",
        "软件", "信息技术", "计算机",
        "网络安全", "信息安全", "数据安全",
        
        # 新能源类
        "新能源", "光伏", "太阳能", "风电", "风能",
        "储能", "电池", "锂电池", "动力电池",
        "新能源汽车", "电动车", "充电桩",
        "氢能源", "燃料电池",
        
        # 生物医药类
        "生物医药", "创新药", "疫苗", "医疗器械",
        "基因", "细胞治疗", "精准医疗",
        "CXO", "CRO", "CDMO",
        
        # 高端制造类
        "机器人", "工业互联网", "智能制造",
        "航空航天", "军工", "高端装备",
        "新材料", "碳纤维", "石墨烯",
        
        # 消费升级类
        "消费电子", "智能家居", "智能穿戴",
        "在线教育", "在线医疗", "互联网",
        
        # 其他成长性行业
        "传媒", "游戏", "影视", "短视频",
        "金融科技", "区块链", "数字货币"
    ]
    
    def __init__(self, analyzer: Optional[FundHoldingsAnalyzer] = None):
        """
        初始化筛选器
        
        Args:
            analyzer: 基金持仓分析器实例，如果为None则创建新实例
        """
        self.analyzer = analyzer or FundHoldingsAnalyzer()
        self._stock_info_cache = {}  # 缓存股票信息
    
    def load_fund_codes_from_file(self, file_path: str) -> List[str]:
        """
        从文件读取基金代码列表
        
        文件格式支持：
        1. 每行一个基金代码
        2. 支持 # 开头的注释行
        3. 自动去除空白行和前后空格
        
        Args:
            file_path: 文件路径
        
        Returns:
            基金代码列表
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return []
        
        fund_codes = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释行
                    if not line or line.startswith('#'):
                        continue
                    fund_codes.append(line)
            
            logger.info(f"从文件 {file_path} 读取了 {len(fund_codes)} 个基金代码")
            return fund_codes
        except Exception as e:
            logger.error(f"读取文件 {file_path} 失败: {e}")
            return []
    
    def get_stock_concepts(self, stock_code: str) -> List[str]:
        """
        获取股票所属的概念板块列表
        
        Args:
            stock_code: 股票代码
        
        Returns:
            概念板块名称列表
        """
        # 先尝试从缓存获取
        if stock_code in self._stock_info_cache:
            return self._stock_info_cache[stock_code].get('concepts', [])
        
        concepts = []
        try:
            # 方法1: 尝试获取股票的概念板块信息
            # 注意：akshare 可能需要通过概念板块列表反向查询
            # 这里先尝试获取股票基本信息，看是否包含概念信息
            
            # 方法2: 通过行业信息判断（作为备选方案）
            stock_info = ak.stock_individual_info_em(symbol=stock_code)
            if not stock_info.empty:
                # 查找行业信息
                industry_row = stock_info[stock_info['item'] == '行业']
                if not industry_row.empty:
                    industry = industry_row.iloc[0]['value']
                    if industry and industry != 'N/A':
                        concepts.append(industry)
            
            # 缓存结果
            if stock_code not in self._stock_info_cache:
                self._stock_info_cache[stock_code] = {}
            self._stock_info_cache[stock_code]['concepts'] = concepts
            
        except Exception as e:
            logger.warning(f"获取股票 {stock_code} 的概念板块信息失败: {e}")
        
        return concepts
    
    def is_growth_stock(self, stock_code: str, stock_name: str = "") -> bool:
        """
        判断股票是否属于成长板块
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称（可选，用于辅助判断）
        
        Returns:
            是否为成长板块股票
        """
        # 方法1: 通过概念板块判断
        concepts = self.get_stock_concepts(stock_code)
        
        # 检查概念板块是否包含成长关键词
        for concept in concepts:
            for keyword in self.GROWTH_KEYWORDS:
                if keyword in concept:
                    return True
        
        # 方法2: 通过股票名称判断（辅助）
        if stock_name:
            for keyword in self.GROWTH_KEYWORDS:
                if keyword in stock_name:
                    return True
        
        return False
    
    def screen_growth_stocks(
        self,
        common_stocks_df: pd.DataFrame,
        min_fund_count: int = 2
    ) -> pd.DataFrame:
        """
        从共同增仓股票列表中筛选出成长板块股票
        
        Args:
            common_stocks_df: 共同增仓股票DataFrame（由find_common_increased_stocks返回）
            min_fund_count: 最少被多少只基金增持（用于二次筛选）
        
        Returns:
            成长板块股票DataFrame
        """
        if common_stocks_df.empty:
            logger.warning("共同增仓股票列表为空")
            return pd.DataFrame()
        
        growth_stocks = []
        
        for idx, row in common_stocks_df.iterrows():
            stock_code = str(row['stock_code'])
            stock_name = row.get('stock_name', '')
            fund_count = row.get('fund_count', 0)
            
            # 先检查基金数量要求
            if fund_count < min_fund_count:
                continue
            
            # 判断是否为成长板块
            if self.is_growth_stock(stock_code, stock_name):
                growth_stocks.append(row)
                logger.debug(f"股票 {stock_code} ({stock_name}) 属于成长板块")
        
        if not growth_stocks:
            logger.warning("未找到符合条件的成长板块股票")
            return pd.DataFrame()
        
        result_df = pd.DataFrame(growth_stocks)
        logger.info(f"筛选出 {len(result_df)} 只成长板块股票")
        
        return result_df
    
    def find_growth_stocks_from_funds(
        self,
        fund_codes: List[str],
        year_prev: str = None,
        year_curr: str = None,
        method: str = 'nav_ratio',
        min_change: float = 0.0,
        min_fund_count: int = 2,
        growth_min_fund_count: int = 2,
        use_latest_quarter: bool = False,
        max_years_back: int = 2
    ) -> pd.DataFrame:
        """
        从基金池中找出共同增仓的成长板块股票（一站式方法）
        
        Args:
            fund_codes: 基金代码列表（也可以传入文件路径，会自动识别）
            year_prev: 前一报告期年份（当use_latest_quarter=False时使用）
            year_curr: 当前报告期年份（当use_latest_quarter=False时使用）
            method: 比较方法，'nav_ratio'或'market_value'
            min_change: 最小变化阈值
            min_fund_count: 共同增仓的最少基金数量
            growth_min_fund_count: 成长板块股票的最少基金数量（可更严格）
            use_latest_quarter: 是否自动使用最新季度，默认False
            max_years_back: 当use_latest_quarter=True时，最多向前查找的年数，默认2年
        
        Returns:
            成长板块股票DataFrame
        """
        # 如果传入的是文件路径，则读取文件
        if isinstance(fund_codes, str) and os.path.exists(fund_codes):
            fund_codes = self.load_fund_codes_from_file(fund_codes)
        
        if not fund_codes:
            logger.error("基金代码列表为空")
            return pd.DataFrame()
        
        # 1. 找出共同增仓股票
        logger.info(f"开始分析 {len(fund_codes)} 只基金的共同增仓股票...")
        common_stocks = self.analyzer.find_common_increased_stocks(
            fund_codes, year_prev, year_curr, method, min_change, min_fund_count,
            use_latest_quarter, max_years_back
        )
        
        if common_stocks.empty:
            logger.warning("未找到共同增仓股票")
            return pd.DataFrame()
        
        # 2. 筛选成长板块股票
        logger.info("开始筛选成长板块股票...")
        growth_stocks = self.screen_growth_stocks(common_stocks, growth_min_fund_count)
        
        return growth_stocks
    
    def get_stock_industry(self, stock_code: str) -> str:
        """
        获取股票所属行业
        
        Args:
            stock_code: 股票代码
        
        Returns:
            行业名称，如果获取失败返回空字符串
        """
        try:
            stock_info = ak.stock_individual_info_em(symbol=stock_code)
            if not stock_info.empty:
                industry_row = stock_info[stock_info['item'] == '行业']
                if not industry_row.empty:
                    return industry_row.iloc[0]['value']
        except Exception as e:
            logger.warning(f"获取股票 {stock_code} 的行业信息失败: {e}")
        
        return ""
    
    def add_industry_info(self, stocks_df: pd.DataFrame) -> pd.DataFrame:
        """
        为股票DataFrame添加行业信息列
        
        Args:
            stocks_df: 股票DataFrame
        
        Returns:
            添加了行业信息的DataFrame
        """
        if stocks_df.empty:
            return stocks_df
        
        industries = []
        for idx, row in stocks_df.iterrows():
            stock_code = str(row['stock_code'])
            industry = self.get_stock_industry(stock_code)
            industries.append(industry)
        
        stocks_df = stocks_df.copy()
        stocks_df['行业'] = industries
        
        return stocks_df

