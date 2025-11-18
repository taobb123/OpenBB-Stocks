"""
AKShare 数据源集成
用于获取 A 股市场数据
"""

import akshare as ak
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd


class AKShareDataSource:
    """AKShare 数据源封装类"""
    
    def __init__(self):
        """初始化 AKShare 数据源"""
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """检查 akshare 是否可用"""
        try:
            import akshare as ak
            return True
        except ImportError:
            print("⚠️ akshare 未安装，请运行: pip install akshare")
            return False
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取所有 A 股股票列表
        
        Returns:
            包含股票代码、名称等信息的 DataFrame
        """
        if not self.available:
            return pd.DataFrame()
        
        try:
            # 获取 A 股实时行情（优先使用新浪接口，不走push2）
            try:
                # 新浪接口最稳定，不被封锁
                df = ak.stock_zh_a_spot()
            except Exception as e1:
                print(f"  ⚠️ stock_zh_a_spot 失败: {e1}，尝试其他接口...")
                try:
                    # 如果新浪接口失败，尝试其他接口
                    df = ak.stock_zh_a_spot_em()
                except Exception as e2:
                    print(f"  ⚠️ stock_zh_a_spot_em 也失败: {e2}")
                    df = pd.DataFrame()
            return df
        except Exception as e:
            print(f"⚠️ 获取 A 股股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_stock_historical(
        self, 
        symbol: str, 
        start_date: str = None, 
        end_date: str = None,
        period: str = "daily",
        adjust: str = "qfq"  # qfq=前复权, bfq=后复权, ""=不复权
    ) -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            symbol: 股票代码（6位数字，如 "600519"）
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期（格式：YYYYMMDD）
            period: 周期（"daily", "weekly", "monthly"）
            adjust: 复权类型（"qfq", "bfq", ""）
        
        Returns:
            历史价格数据 DataFrame
        """
        if not self.available:
            return pd.DataFrame()
        
        try:
            # 如果没有指定日期，默认获取最近1年
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            return df
        except Exception as e:
            print(f"⚠️ 获取 {symbol} 历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
        
        Returns:
            股票信息字典
        """
        if not self.available:
            return {}
        
        try:
            # 获取股票基本信息
            info = ak.stock_individual_info_em(symbol=symbol)
            # 转换为字典
            info_dict = {}
            if isinstance(info, pd.DataFrame):
                for _, row in info.iterrows():
                    key = row.iloc[0] if len(row) > 0 else ""
                    value = row.iloc[1] if len(row) > 1 else ""
                    if key and value:
                        info_dict[key] = value
            return info_dict
        except Exception as e:
            print(f"⚠️ 获取 {symbol} 基本信息失败: {e}")
            return {}
    
    def get_sector_performance(self) -> List[Dict[str, Any]]:
        """
        获取行业表现数据
        
        Returns:
            行业表现数据列表
        """
        if not self.available:
            return []
        
        try:
            # 获取申万行业指数表现
            # 注意：akshare 的行业数据可能需要不同的函数
            # 这里使用股票列表按行业分组的方式
            
            # 获取所有 A 股实时行情（使用新浪接口，不走push2）
            try:
                # 优先使用新浪接口（更稳定，不被封锁）
                stock_df = ak.stock_zh_a_spot()
            except:
                # 如果新浪接口失败，尝试其他接口
                try:
                    stock_df = ak.stock_zh_a_spot_em()
                except:
                    stock_df = pd.DataFrame()
            
            if stock_df.empty:
                return []
            
            # 按行业分组计算平均涨跌幅
            if "所属行业" in stock_df.columns:
                sector_performance = []
                sectors = stock_df.groupby("所属行业")
                
                for sector_name, group in sectors:
                    # 计算该行业的平均涨跌幅
                    if "涨跌幅" in group.columns:
                        avg_change = group["涨跌幅"].mean() / 100  # 转换为小数
                        sector_performance.append({
                            "name": sector_name,
                            "performance_1d": avg_change,  # 日涨跌幅
                            "stock_count": len(group)
                        })
                
                return sector_performance
            
            # 如果没有行业列，尝试使用其他方法
            # 获取申万行业指数
            try:
                sw_index = ak.sw_index_cons(symbol="801010")  # 申万一级行业示例
                # 这里可以进一步处理行业指数数据
            except:
                pass
            
            return []
        except Exception as e:
            print(f"⚠️ 获取行业表现数据失败: {e}")
            return []
    
    def search_stocks(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索股票
        
        Args:
            query: 搜索关键词（股票代码或名称）
            limit: 返回结果数量限制
        
        Returns:
            股票列表
        """
        if not self.available:
            return []
        
        try:
            # 获取所有 A 股列表
            stock_df = ak.stock_zh_a_spot_em()
            
            if stock_df.empty:
                return []
            
            # 搜索匹配的股票
            results = []
            query_upper = query.upper()
            
            for _, row in stock_df.iterrows():
                code = str(row.get("代码", ""))
                name = str(row.get("名称", ""))
                
                # 匹配代码或名称
                if query_upper in code or query in name:
                    results.append({
                        "symbol": code,
                        "name": name,
                        "market_cap": row.get("总市值", 0),
                        "price": row.get("最新价", 0),
                        "change_percent": row.get("涨跌幅", 0) / 100 if row.get("涨跌幅") else 0
                    })
                    
                    if len(results) >= limit:
                        break
            
            return results
        except Exception as e:
            print(f"⚠️ 搜索股票失败: {e}")
            return []
    
    def get_stock_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票基本面数据（使用2025最新稳定接口）
        
        Args:
            symbol: 股票代码
        
        Returns:
            基本面数据字典
        """
        if not self.available:
            return {}
        
        try:
            fundamentals = {}
            
            # 方法1：使用最稳定的财务分析指标接口（推荐，不走push2）
            try:
                print(f"  使用 stock_financial_analysis_indicator 获取 {symbol} 基本面数据...")
                df = ak.stock_financial_analysis_indicator(stock=symbol)
                
                if not df.empty:
                    # 获取最新一期数据（通常是最后一行）
                    latest = df.iloc[-1]
                    
                    # 提取关键指标
                    for col in df.columns:
                        value = latest.get(col)
                        if pd.notna(value):
                            # 转换列名为中文（如果可能）
                            col_name = str(col)
                            fundamentals[col_name] = value
                    
                    # 确保关键指标存在
                    key_mappings = {
                        "市盈率": ["市盈率", "PE", "pe", "市盈率TTM"],
                        "市净率": ["市净率", "PB", "pb", "市净率MRQ"],
                        "ROE": ["净资产收益率", "ROE", "roe", "净资产收益率TTM"],
                        "ROA": ["总资产收益率", "ROA", "roa"],
                        "毛利率": ["毛利率", "销售毛利率", "毛利率TTM"],
                        "净利率": ["净利率", "销售净利率", "净利率TTM"],
                        "EPS": ["每股收益", "EPS", "eps", "基本每股收益"],
                        "每股净资产": ["每股净资产", "BPS", "bps"],
                        "每股现金流": ["每股现金流", "每股经营现金流"],
                        "营业收入": ["营业收入", "营业总收入"],
                        "净利润": ["净利润", "归属净利润"]
                    }
                    
                    # 尝试找到关键指标
                    for key, possible_names in key_mappings.items():
                        if key not in fundamentals:
                            for name in possible_names:
                                if name in fundamentals:
                                    fundamentals[key] = fundamentals[name]
                                    break
                    
                    print(f"  ✅ 通过 stock_financial_analysis_indicator 获取到 {len(fundamentals)} 个指标")
            except Exception as e:
                print(f"  ⚠️ stock_financial_analysis_indicator 失败: {e}")
            
            # 方法2：获取实时行情（使用新浪接口，不走push2）
            try:
                print(f"  使用 stock_zh_a_spot 获取 {symbol} 实时行情...")
                spot_data = ak.stock_zh_a_spot()
                
                if not spot_data.empty:
                    # 查找股票（代码列可能是"代码"或"symbol"）
                    code_col = None
                    for col in ["代码", "symbol", "股票代码"]:
                        if col in spot_data.columns:
                            code_col = col
                            break
                    
                    if code_col:
                        stock_row = spot_data[spot_data[code_col] == symbol]
                        if not stock_row.empty:
                            row = stock_row.iloc[0]
                            
                            # 提取实时数据
                            price_cols = {
                                "最新价": ["最新价", "现价", "price", "current"],
                                "涨跌幅": ["涨跌幅", "涨跌%", "change_pct", "pctChg"],
                                "成交量": ["成交量", "volume", "vol"],
                                "换手率": ["换手率", "turnover", "turnoverRate"],
                                "市盈率": ["市盈率", "PE", "pe"],
                                "市净率": ["市净率", "PB", "pb"],
                                "总市值": ["总市值", "market_cap", "mktcap"],
                                "流通市值": ["流通市值", "circulating_market_cap"]
                            }
                            
                            for key, possible_names in price_cols.items():
                                for name in possible_names:
                                    if name in row.index:
                                        value = row.get(name)
                                        if pd.notna(value):
                                            fundamentals[key] = value
                                            break
                            
                            print(f"  ✅ 通过 stock_zh_a_spot 获取到实时行情")
            except Exception as e:
                print(f"  ⚠️ stock_zh_a_spot 失败: {e}")
            
            # 方法3：获取财务报表摘要（如果前两个都失败）
            if not fundamentals:
                try:
                    print(f"  尝试使用 stock_financial_report_sina 获取 {symbol} 财务数据...")
                    # 获取利润表最新数据
                    income = ak.stock_financial_report_sina(stock=symbol, symbol="利润表")
                    if not income.empty:
                        latest_income = income.iloc[-1]
                        fundamentals["营业收入"] = latest_income.get("营业收入", None)
                        fundamentals["净利润"] = latest_income.get("净利润", None)
                        fundamentals["每股收益"] = latest_income.get("每股收益", None)
                except Exception as e:
                    print(f"  ⚠️ stock_financial_report_sina 失败: {e}")
            
            return fundamentals if fundamentals else {}
            
        except Exception as e:
            print(f"⚠️ 获取 {symbol} 基本面数据失败: {e}")
            return {}
    
    def screen_stocks(
        self,
        sector: str = None,
        mktcap_min: float = None,
        mktcap_max: float = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        筛选股票
        
        Args:
            sector: 行业名称
            mktcap_min: 最小市值（元）
            mktcap_max: 最大市值（元）
            limit: 返回数量限制
        
        Returns:
            筛选后的股票列表
        """
        if not self.available:
            return []
        
        try:
            # 获取所有 A 股实时行情
            stock_df = ak.stock_zh_a_spot_em()
            
            if stock_df.empty:
                return []
            
            # 应用筛选条件
            filtered_df = stock_df.copy()
            
            # 行业筛选
            if sector and "所属行业" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["所属行业"].str.contains(sector, na=False)]
            
            # 市值筛选
            if mktcap_min and "总市值" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["总市值"] >= mktcap_min]
            if mktcap_max and "总市值" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["总市值"] <= mktcap_max]
            
            # 转换为字典列表
            results = []
            for _, row in filtered_df.head(limit).iterrows():
                results.append({
                    "symbol": row.get("代码", ""),
                    "name": row.get("名称", ""),
                    "market_cap": row.get("总市值", 0),
                    "price": row.get("最新价", 0),
                    "change_percent": row.get("涨跌幅", 0) / 100 if row.get("涨跌幅") else 0,
                    "volume": row.get("成交量", 0),
                    "turnover": row.get("换手率", 0) / 100 if row.get("换手率") else 0,
                    "sector": row.get("所属行业", "")
                })
            
            return results
        except Exception as e:
            print(f"⚠️ 筛选股票失败: {e}")
            return []

