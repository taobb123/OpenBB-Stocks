"""
AKShare 数据源集成
用于获取 A 股市场数据
"""

import akshare as ak
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import os

# 尝试导入 requests（用于 iTick API）
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️ requests 未安装，iTick API 功能将不可用。请运行: pip install requests")


def _symbol_to_ts_code(symbol: str) -> str:
    """A 股 6 位代码 -> Tushare ts_code（如 600018.SH）。"""
    s = (symbol or "").strip()
    if len(s) != 6 or not s.isdigit():
        return ""
    if s.startswith("6"):
        return f"{s}.SH"
    return f"{s}.SZ"


def _try_init_tushare_pro():
    """从环境变量 TUSHARE_TOKEN 初始化 Tushare Pro；未配置则返回 None。"""
    token = os.getenv("TUSHARE_TOKEN", "").strip()
    if not token:
        return None
    try:
        import tushare as ts
        ts.set_token(token)
        return ts.pro_api()
    except Exception as e:
        print(f"⚠️ Tushare Pro 初始化失败: {e}")
        return None


class AKShareDataSource:
    """AKShare 数据源封装类"""
    
    def __init__(self, itick_token: Optional[str] = None):
        """
        初始化 AKShare 数据源
        
        Args:
            itick_token: iTick API token；为 None 时仅使用环境变量 ITICK_TOKEN（不设默认密钥）
        """
        self.available = self._check_availability()
        if itick_token is not None and str(itick_token).strip():
            self.itick_token = str(itick_token).strip()
        else:
            self.itick_token = os.getenv("ITICK_TOKEN", "").strip()
        self.itick_available = bool(self.itick_token) and REQUESTS_AVAILABLE
        self.tushare_pro = _try_init_tushare_pro()
        if self.tushare_pro:
            print(
                "✅ Tushare Pro 已启用（TUSHARE_TOKEN）：A 股数据优先走 Tushare，AkShare 为回退"
            )
    
    def _check_availability(self) -> bool:
        """检查 akshare 是否可用"""
        try:
            import akshare as ak
            return True
        except ImportError:
            print("⚠️ akshare 未安装，请运行: pip install akshare")
            return False

    def _get_hist_from_tushare(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Tushare daily 拉取 A 股日线，列名与 akshare 常用中文列对齐。"""
        if not self.tushare_pro:
            return pd.DataFrame()
        ts_code = _symbol_to_ts_code(symbol)
        if not ts_code:
            return pd.DataFrame()
        try:
            print(f"  使用 Tushare daily 获取 {symbol} 历史数据（优先源）...")
            df = self.tushare_pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.sort_values("trade_date")
            out = pd.DataFrame(
                {
                    "日期": pd.to_datetime(df["trade_date"].astype(str)),
                    "开盘": pd.to_numeric(df["open"], errors="coerce"),
                    "收盘": pd.to_numeric(df["close"], errors="coerce"),
                    "最高": pd.to_numeric(df["high"], errors="coerce"),
                    "最低": pd.to_numeric(df["low"], errors="coerce"),
                    "成交量": pd.to_numeric(df["vol"], errors="coerce") * 100.0,
                }
            )
            out["date"] = out["日期"]
            print(f"  ✅ Tushare 返回 {len(out)} 条日线")
            return out
        except Exception as e:
            print(f"  ⚠️ Tushare daily 失败: {str(e)[:160]}")
            return pd.DataFrame()

    def _merge_tushare_daily_basic(
        self,
        symbol: str,
        fundamentals: Dict[str, Any],
        *,
        prefer_first: bool = False,
    ) -> None:
        """
        Tushare daily_basic：最新价、PE、PB、换手率等。
        prefer_first=True 时由 Tushare 主导写入；False 时仅填补空缺字段。
        """
        if not self.tushare_pro:
            return
        ts_code = _symbol_to_ts_code(symbol)
        if not ts_code:
            return

        def _set(key: str, value: Any) -> None:
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return
            if prefer_first or key not in fundamentals or fundamentals.get(key) is None:
                fundamentals[key] = float(value) if isinstance(value, (int, float)) else value

        try:
            df = self.tushare_pro.daily_basic(
                ts_code=ts_code,
                fields="trade_date,close,turnover_rate,volume_ratio,pe_ttm,pb,total_mv,circ_mv",
            )
            if df is None or df.empty:
                return
            row = df.iloc[0]
            _set("最新价", row.get("close"))
            _set("市盈率", row.get("pe_ttm"))
            _set("市净率", row.get("pb"))
            _set("换手率", row.get("turnover_rate"))
            if pd.notna(row.get("total_mv")):
                _set("总市值", float(row["total_mv"]) * 10000.0)
            if pd.notna(row.get("circ_mv")):
                _set("流通市值", float(row["circ_mv"]) * 10000.0)
            print(
                f"  ✅ Tushare daily_basic（trade_date={row.get('trade_date', '')}）"
            )
        except Exception as e:
            print(f"  ⚠️ Tushare daily_basic 失败: {str(e)[:160]}")

    def _merge_tushare_fina_indicator(self, symbol: str, fundamentals: Dict[str, Any]) -> None:
        """Tushare fina_indicator 最新一期，写入财务指标（与下游中英文键兼容）。"""
        if not self.tushare_pro:
            return
        ts_code = _symbol_to_ts_code(symbol)
        if not ts_code:
            return
        try:
            df = self.tushare_pro.fina_indicator(ts_code=ts_code)
            if df is None or df.empty:
                return
            if "end_date" in df.columns:
                df = df.sort_values("end_date")
            row = df.iloc[-1]
            for col in df.columns:
                v = row.get(col)
                if col is not None and pd.notna(v):
                    fundamentals[str(col)] = v
            if pd.notna(row.get("roe")):
                fundamentals["ROE"] = float(row["roe"])
                fundamentals["净资产收益率"] = float(row["roe"])
            if pd.notna(row.get("roa")):
                fundamentals["ROA"] = float(row["roa"])
                fundamentals["总资产收益率"] = float(row["roa"])
            for src, dst in (
                ("eps", "EPS"),
                ("eps", "每股收益"),
                ("bps", "每股净资产"),
                ("ocfps", "每股现金流"),
                ("grossprofit_margin", "毛利率"),
                ("netprofit_margin", "净利率"),
                ("netprofit_margin", "销售净利率"),
            ):
                if pd.notna(row.get(src)):
                    fundamentals[dst] = float(row[src])
            print(f"  ✅ Tushare fina_indicator（报告期 end_date={row.get('end_date', '')}）")
        except Exception as e:
            print(f"  ⚠️ Tushare fina_indicator 失败: {str(e)[:160]}")
    
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
        获取股票历史数据（直接使用 stock_zh_a_daily 接口）
        
        Args:
            symbol: 股票代码（6位数字，如 "600519"）
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期（格式：YYYYMMDD）
            period: 周期（"daily", "weekly", "monthly"）
            adjust: 复权类型（"qfq", "bfq", ""）
        
        Returns:
            历史价格数据 DataFrame
        """
        if not self.available and not self.tushare_pro:
            return pd.DataFrame()
        
        # 如果没有指定日期，默认获取最近1年
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        
        if self.tushare_pro:
            tu = self._get_hist_from_tushare(symbol, start_date, end_date)
            if not tu.empty:
                return tu
            print(
                f"  ℹ️ Tushare daily 无数据或拉取失败，改用 AkShare（{symbol}）"
            )
        else:
            print(
                "  ℹ️ 未启用 Tushare：当前进程无 TUSHARE_TOKEN。"
                "请在启动 Django 的终端设置该变量，或在仓库根目录 / market_analysis_api 下配置 .env"
            )

        if not self.available:
            return pd.DataFrame()
        
        # AkShare（Tushare 未配置或失败时的数据源；含前复权）
        try:
            print(f"  使用 stock_zh_a_daily（AkShare）获取 {symbol} 历史数据...")
            # stock_zh_a_daily 需要带市场前缀
            if symbol.startswith("6"):
                daily_symbol = f"sh{symbol}"  # 上海
            elif symbol.startswith("0") or symbol.startswith("3"):
                daily_symbol = f"sz{symbol}"  # 深圳
            else:
                daily_symbol = symbol
            
            # 获取数据
            df = ak.stock_zh_a_daily(symbol=daily_symbol, adjust=adjust)
            if not df.empty:
                # 如果指定了日期范围，进行过滤
                if start_date and end_date:
                    # 确保日期列是日期类型
                    if "date" in df.columns:
                        df["date"] = pd.to_datetime(df["date"])
                        start_dt = pd.to_datetime(start_date, format="%Y%m%d")
                        end_dt = pd.to_datetime(end_date, format="%Y%m%d")
                        df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
                    elif "日期" in df.columns:
                        df["日期"] = pd.to_datetime(df["日期"])
                        start_dt = pd.to_datetime(start_date, format="%Y%m%d")
                        end_dt = pd.to_datetime(end_date, format="%Y%m%d")
                        df = df[(df["日期"] >= start_dt) & (df["日期"] <= end_dt)]
                
                if not df.empty:
                    print(f"  ✅ 通过 stock_zh_a_daily 获取到 {len(df)} 条历史数据")
                    return df
                else:
                    print(f"  ⚠️ 日期过滤后数据为空")
            else:
                print(f"  ⚠️ stock_zh_a_daily 返回空数据")
        except Exception as e:
            print(f"  ❌ stock_zh_a_daily 失败: {str(e)[:200]}")
        
        return pd.DataFrame()
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票基本信息（直接使用 stock_info_a_code_name 接口）
        
        Args:
            symbol: 股票代码
        
        Returns:
            股票信息字典
        """
        if not self.available and not self.tushare_pro:
            return {}
        
        if self.tushare_pro:
            ts_code = _symbol_to_ts_code(symbol)
            if ts_code:
                try:
                    print(f"  优先使用 Tushare stock_basic 获取 {symbol} 基本信息...")
                    df = self.tushare_pro.stock_basic(
                        ts_code=ts_code,
                        fields="ts_code,name,industry,area,market,list_date",
                    )
                    if df is not None and not df.empty:
                        row = df.iloc[0]
                        name = row.get("name") or ""
                        industry = row.get("industry") or "N/A"
                        if name:
                            print("  ✅ Tushare stock_basic 获取到基本信息")
                            return {
                                "股票简称": name,
                                "名称": name,
                                "所属行业": industry,
                                "行业": industry,
                            }
                except Exception as e:
                    print(f"  ⚠️ Tushare stock_basic 失败: {str(e)[:200]}")
        
        if not self.available:
            return {}
        
        try:
            print(f"  使用 stock_info_a_code_name（AkShare 回退）获取 {symbol} 基本信息...")
            info = ak.stock_info_a_code_name()
            if not info.empty:
                # 查找对应的股票代码
                stock_info = info[info["code"] == symbol]
                if not stock_info.empty:
                    info_dict = {
                        "股票简称": stock_info.iloc[0].get("name", ""),
                        "名称": stock_info.iloc[0].get("name", "")
                    }
                    if info_dict.get("股票简称"):
                        print(f"  ✅ 通过 stock_info_a_code_name 获取到基本信息")
                        return info_dict
        except Exception as e:
            print(f"  ⚠️ stock_info_a_code_name 失败: {str(e)[:200]}")
        
        print(f"  ❌ 无法获取 {symbol} 基本信息")
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
        if not self.available and not self.tushare_pro:
            return {}
        
        try:
            fundamentals: Dict[str, Any] = {}
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
                "净利润": ["净利润", "归属净利润"],
            }

            if self.tushare_pro:
                print(f"  优先使用 Tushare Pro 获取 {symbol} 基本面…")
                self._merge_tushare_daily_basic(symbol, fundamentals, prefer_first=True)
                self._merge_tushare_fina_indicator(symbol, fundamentals)

            if self.available:
                try:
                    print(
                        f"  使用 AkShare stock_financial_analysis_indicator 补齐 {symbol} 空缺字段…"
                    )
                    df = ak.stock_financial_analysis_indicator(symbol=symbol)
                    if not df.empty:
                        latest = df.iloc[-1]
                        ak_part: Dict[str, Any] = {}
                        for col in df.columns:
                            value = latest.get(col)
                            if pd.notna(value):
                                ak_part[str(col)] = value
                        for key, possible_names in key_mappings.items():
                            if key not in ak_part:
                                for name in possible_names:
                                    if name in ak_part:
                                        ak_part[key] = ak_part[name]
                                        break
                        if self.tushare_pro:
                            for k, v in ak_part.items():
                                if v is None or (
                                    isinstance(v, float) and pd.isna(v)
                                ):
                                    continue
                                cur = fundamentals.get(k)
                                if cur is None or (
                                    isinstance(cur, float) and pd.isna(cur)
                                ):
                                    fundamentals[k] = v
                        else:
                            fundamentals.update(ak_part)
                            for key, possible_names in key_mappings.items():
                                if key not in fundamentals:
                                    for name in possible_names:
                                        if name in fundamentals:
                                            fundamentals[key] = fundamentals[name]
                                            break
                        print(
                            f"  ✅ AkShare 合并后基本面字段约 {len(fundamentals)} 个"
                        )
                except Exception as e:
                    print(f"  ⚠️ stock_financial_analysis_indicator 失败: {e}")

            # 已配置 Tushare 时不再请求 iTick（通常无权限；避免 401）
            if self.itick_available and not self.tushare_pro:
                try:
                    print(f"  使用 iTick API 获取 {symbol} 实时行情…")
                    realtime_data = self._get_realtime_from_itick(symbol)
                    if realtime_data:
                        fundamentals.update(realtime_data)
                        print(f"  ✅ 通过 iTick API 获取到实时行情数据")
                except Exception as e:
                    print(f"  ⚠️ iTick API 获取实时行情失败: {e}")
            
            if not fundamentals and self.available:
                try:
                    print(f"  尝试使用 stock_financial_report_sina 获取 {symbol} 财务数据…")
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
    
    def _get_realtime_from_itick(self, symbol: str) -> Dict[str, Any]:
        """
        使用 iTick API 获取股票实时行情数据
        
        Args:
            symbol: 股票代码（6位数字，如 "600519"）
        
        Returns:
            实时行情数据字典
        """
        if not self.itick_available:
            return {}
        
        try:
            # 根据股票代码确定交易所区域
            # 上海：600xxx, 688xxx, 601xxx, 603xxx, 605xxx -> SH
            # 深圳：000xxx, 002xxx, 300xxx, 301xxx -> SZ
            if symbol.startswith(("600", "688", "601", "603", "605")):
                region = "SH"
            elif symbol.startswith(("000", "002", "300", "301")):
                region = "SZ"
            else:
                # 默认尝试 SH
                region = "SH"
            
            # 调用 iTick API
            url = "https://api.itick.org/stock/tick"
            params = {
                "region": region,
                "code": symbol
            }
            headers = {
                "accept": "application/json",
                "token": self.itick_token
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 解析 iTick 返回的数据
                realtime = {}
                
                # 根据 iTick API 返回的数据结构提取字段
                # 注意：实际字段名可能因 API 版本而异，需要根据实际返回调整
                
                # 处理不同的返回格式
                if isinstance(data, dict):
                    # 如果返回的数据在 data 字段中
                    if "data" in data and isinstance(data["data"], dict):
                        data = data["data"]
                    
                    # 提取价格相关数据（尝试多个可能的字段名）
                    price_fields = ["price", "last", "close", "current", "lastPrice", "closePrice"]
                    for field in price_fields:
                        if field in data and data[field] is not None:
                            realtime["最新价"] = float(data[field])
                            break
                    
                    # 提取涨跌幅
                    change_fields = ["change_pct", "pct_chg", "changePercent", "pctChg", "change"]
                    for field in change_fields:
                        if field in data and data[field] is not None:
                            realtime["涨跌幅"] = float(data[field])
                            break
                    
                    # 提取成交量
                    if "volume" in data and data["volume"] is not None:
                        realtime["成交量"] = float(data["volume"])
                    
                    # 提取换手率
                    turnover_fields = ["turnover_rate", "turnoverRate", "turnover"]
                    for field in turnover_fields:
                        if field in data and data[field] is not None:
                            realtime["换手率"] = float(data[field])
                            break
                    
                    # 提取市值
                    mcap_fields = ["market_cap", "mkt_cap", "marketCap", "totalMarketCap"]
                    for field in mcap_fields:
                        if field in data and data[field] is not None:
                            realtime["总市值"] = float(data[field])
                            break
                    
                    # 提取市盈率
                    pe_fields = ["pe", "pe_ratio", "peRatio", "P/E"]
                    for field in pe_fields:
                        if field in data and data[field] is not None:
                            realtime["市盈率"] = float(data[field])
                            break
                    
                    # 提取市净率
                    pb_fields = ["pb", "pb_ratio", "pbRatio", "P/B"]
                    for field in pb_fields:
                        if field in data and data[field] is not None:
                            realtime["市净率"] = float(data[field])
                            break
                    
                    # 提取涨跌额
                    if "change" in data and data["change"] is not None:
                        # 如果 change 是价格变化（不是百分比），也保存
                        if "涨跌幅" not in realtime:
                            try:
                                # 尝试计算涨跌幅（如果有 price 和 change）
                                if "最新价" in realtime and realtime["最新价"] > 0:
                                    realtime["涨跌幅"] = (float(data["change"]) / realtime["最新价"]) * 100
                            except:
                                pass
                    
                elif isinstance(data, list) and len(data) > 0:
                    # 如果返回的是列表，取第一个元素
                    item = data[0] if isinstance(data[0], dict) else {}
                    # 递归处理（将 item 作为 dict 处理）
                    if isinstance(item, dict):
                        # 使用相同的字段提取逻辑
                        price_fields = ["price", "last", "close", "current"]
                        for field in price_fields:
                            if field in item and item[field] is not None:
                                realtime["最新价"] = float(item[field])
                                break
                        
                        change_fields = ["change_pct", "pct_chg", "changePercent"]
                        for field in change_fields:
                            if field in item and item[field] is not None:
                                realtime["涨跌幅"] = float(item[field])
                                break
                        
                        if "volume" in item and item["volume"] is not None:
                            realtime["成交量"] = float(item["volume"])
                
                return realtime
            else:
                print(f"  ⚠️ iTick API 返回错误状态码: {response.status_code}")
                return {}
                
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️ iTick API 请求异常: {e}")
            return {}
        except Exception as e:
            print(f"  ⚠️ iTick API 解析数据异常: {e}")
            return {}

    def _extract_realtime_from_spot_df(
        self,
        df: Optional[pd.DataFrame],
        symbol: str,
        fundamentals: Dict[str, Any]
    ) -> bool:
        """
        从实时行情 DataFrame 中提取指定股票的数据
        """
        if df is None or df.empty:
            return False
        
        # 查找可能的代码列
        code_col = None
        for col in ["代码", "symbol", "股票代码", "证券代码"]:
            if col in df.columns:
                code_col = col
                break
        
        if not code_col:
            return False
        
        stock_row = df[df[code_col] == symbol]
        if stock_row.empty and symbol.startswith(("6", "0", "3")):
            # 有些接口会自动带上交易所后缀，尝试补齐
            alt_symbol = f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ"
            stock_row = df[df[code_col] == alt_symbol]
        
        if stock_row.empty:
            return False
        
        row = stock_row.iloc[0]
        
        price_cols = {
            "最新价": ["最新价", "现价", "price", "current", "最新价(元)"],
            "涨跌幅": ["涨跌幅", "涨跌%", "change_pct", "pctChg"],
            "成交量": ["成交量", "volume", "vol"],
            "换手率": ["换手率", "turnover", "turnoverRate"],
            "市盈率": ["市盈率", "PE", "pe"],
            "市净率": ["市净率", "PB", "pb"],
            "总市值": ["总市值", "market_cap", "mktcap"],
            "流通市值": ["流通市值", "circulating_market_cap"]
        }
        
        updated = False
        for key, possible_names in price_cols.items():
            for name in possible_names:
                if name in row.index:
                    value = row.get(name)
                    if pd.notna(value):
                        fundamentals[key] = value
                        updated = True
                        break
        
        return updated
    
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
    
    # ==================== ETF 相关接口 ====================
    
    def get_etf_historical(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取ETF历史行情数据
        
        Args:
            symbol: ETF代码（如 "510300"，不需要带市场前缀）
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期（格式：YYYYMMDD）
            period: 数据周期，"daily"（日线）、"weekly"（周线）或"monthly"（月线）
            adjust: 复权方式，"qfq"（前复权）、"hfq"（后复权）或""（不复权）
        
        Returns:
            ETF历史行情数据 DataFrame
        """
        if not self.available:
            return pd.DataFrame()
        
        # 如果没有指定日期，默认获取最近1年
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        
        try:
            print(f"  获取ETF {symbol} 历史数据（{start_date} 至 {end_date}）...")
            df = ak.fund_etf_hist_em(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            if not df.empty:
                print(f"  ✅ 获取到 {len(df)} 条ETF历史数据")
                return df
            else:
                print(f"  ⚠️ ETF历史数据为空")
                return pd.DataFrame()
        except Exception as e:
            print(f"  ⚠️ 获取ETF历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_etf_spot(self) -> pd.DataFrame:
        """
        获取所有ETF的实时行情
        
        Returns:
            包含所有ETF实时行情的 DataFrame
        """
        if not self.available:
            return pd.DataFrame()
        
        try:
            print(f"  获取ETF实时行情...")
            df = ak.fund_etf_spot_em()
            if not df.empty:
                print(f"  ✅ 获取到 {len(df)} 只ETF的实时行情")
                return df
            else:
                print(f"  ⚠️ ETF实时行情数据为空")
                return pd.DataFrame()
        except Exception as e:
            print(f"  ⚠️ 获取ETF实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_etf_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取ETF基本信息（规模、净值等）
        
        Args:
            symbol: ETF代码（如 "511280"）
        
        Returns:
            ETF基本信息字典
        """
        if not self.available:
            return {}
        
        try:
            print(f"  获取ETF {symbol} 基本信息...")
            df = ak.fund_em_etf_info(symbol=symbol)
            
            info_dict = {}
            if isinstance(df, pd.DataFrame) and not df.empty:
                # 转换为字典格式
                for _, row in df.iterrows():
                    if len(row) >= 2:
                        key = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                        value = row.iloc[1] if len(row) > 1 else ""
                        if key and pd.notna(value):
                            info_dict[key] = value
                
                if info_dict:
                    print(f"  ✅ 获取到ETF基本信息")
                    return info_dict
            else:
                print(f"  ⚠️ ETF基本信息为空")
                return {}
        except Exception as e:
            print(f"  ⚠️ 获取ETF基本信息失败: {e}")
            return {}
    
    def get_fund_list(self) -> pd.DataFrame:
        """
        获取包括ETF在内的所有基金列表及代码
        
        Returns:
            基金列表 DataFrame
        """
        if not self.available:
            return pd.DataFrame()
        
        try:
            print(f"  获取基金列表...")
            df = ak.fund_em_fund_name()
            if not df.empty:
                print(f"  ✅ 获取到 {len(df)} 只基金")
                return df
            else:
                print(f"  ⚠️ 基金列表为空")
                return pd.DataFrame()
        except Exception as e:
            print(f"  ⚠️ 获取基金列表失败: {e}")
            return pd.DataFrame()

