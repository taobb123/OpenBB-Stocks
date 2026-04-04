"""
交互式市场分析系统
支持用户输入股票代码、外部工具协作、时机判断等功能
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
from market_structure_analysis import MarketStructureAnalyzer

# 尝试导入 akshare
try:
    from akshare_data_source import AKShareDataSource
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

# 尝试导入 OpenBB SDK
try:
    from openbb import obb
    OPENBB_SDK_AVAILABLE = True
except ImportError:
    try:
        from openbb_terminal.sdk import openbb as obb
        OPENBB_SDK_AVAILABLE = True
    except ImportError:
        OPENBB_SDK_AVAILABLE = False
        obb = None


class InteractiveMarketAnalyzer:
    """交互式市场分析器"""
    
    def __init__(self, mcp_url: str = "http://127.0.0.1:8002/mcp", use_akshare: bool = True, use_openbb: bool = False):
        """
        初始化交互式分析器
        
        Args:
            mcp_url: MCP服务器地址
            use_akshare: 是否使用 akshare
            use_openbb: 是否使用 OpenBB SDK（默认False，因为版本不兼容）
        """
        self.analyzer = MarketStructureAnalyzer(mcp_url=mcp_url, use_akshare=use_akshare)
        self.akshare = self.analyzer.akshare if use_akshare and AKSHARE_AVAILABLE else None
        
        # OpenBB SDK 已禁用（版本不兼容），技术指标使用 akshare 数据计算
        self.use_openbb = False
        self.obb = None
        # 注意：get_stock_technical_indicators_openbb 方法现在使用 akshare 数据，不再依赖 OpenBB SDK
    
    def _generate_report_filename(self, prefix: str = "custom_stock_analysis") -> str:
        """
        生成报告文件名（纯数字日期格式：年月日时分，重复时加序号）
        
        Args:
            prefix: 文件名前缀（实际不使用，保持兼容性）
        
        Returns:
            文件名（带序号，如果重复）
        """
        # 格式：YYYYMMDDHHmm（年月日时分）
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        base_filename = f"{timestamp}.txt"
        
        # 检查文件是否存在，如果存在则加序号
        if os.path.exists(base_filename):
            counter = 1
            while True:
                filename = f"{timestamp}_{counter}.txt"
                if not os.path.exists(filename):
                    return filename
                counter += 1
        else:
            return base_filename
    
    def get_stock_timing_analysis(self, symbol: str, hist_data=None) -> Dict[str, Any]:
        """
        分析股票买入时机
        
        Args:
            symbol: 股票代码
            hist_data: 可选，已获取的历史数据（避免重复获取）
        
        Returns:
            时机分析结果
        """
        if not self.akshare:
            return {"error": "AKShare 不可用"}
        
        try:
            # 如果没有提供历史数据，则获取
            if hist_data is None or hist_data.empty:
                # 获取历史数据（最近1年）
                end_date = datetime.now().strftime("%Y%m%d")
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
                
                hist_data = self.akshare.get_stock_historical(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    period="daily",
                    adjust="qfq"  # 前复权
                )
            
            if hist_data.empty:
                return {"error": "无法获取历史数据"}
            
            # 标准化列名（akshare可能返回英文列名，统一转换为中文）
            df = hist_data.copy()
            column_mapping = {
                "close": "收盘",
                "volume": "成交量",
                "open": "开盘",
                "high": "最高",
                "low": "最低"
            }
            for eng_col, cn_col in column_mapping.items():
                if eng_col in df.columns and cn_col not in df.columns:
                    df[cn_col] = df[eng_col]
            
            # 计算技术指标
            analysis = {
                "symbol": symbol,
                "current_price": float(df.iloc[-1]["收盘"]) if "收盘" in df.columns else 0,
                "indicators": {}
            }
            
            # 1. 移动平均线
            if "收盘" in df.columns:
                close_prices = df["收盘"].astype(float)
                current_price = close_prices.iloc[-1]
                ma5 = close_prices.tail(5).mean()
                ma20 = close_prices.tail(20).mean()
                ma60 = close_prices.tail(60).mean() if len(close_prices) >= 60 else None
                
                # 判断均线多头排列（右侧交易重要指标）
                ma_bullish = False
                if ma60:
                    ma_bullish = ma5 > ma20 > ma60
                else:
                    ma_bullish = ma5 > ma20
                
                # 判断价格是否在均线之上
                price_above_ma = current_price > ma5 and current_price > ma20
                
                analysis["indicators"]["MA"] = {
                    "MA5": float(ma5),
                    "MA20": float(ma20),
                    "MA60": float(ma60) if ma60 else None,
                    "trend": "上升" if ma5 > ma20 else "下降",
                    "bullish_arrangement": ma_bullish,  # 多头排列
                    "price_above_ma": price_above_ma  # 价格在均线之上
                }
            
            # 2. 相对强弱指标（RSI）
            if "收盘" in df.columns:
                close_prices = df["收盘"].astype(float)
                delta = close_prices.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = float(rsi.iloc[-1]) if not rsi.empty else None
                
                # 右侧交易：RSI在50-70区间为强势信号
                rsi_signal = "超买" if current_rsi and current_rsi > 70 else \
                             "超卖" if current_rsi and current_rsi < 30 else \
                             "强势" if current_rsi and 50 <= current_rsi <= 70 else \
                             "弱势" if current_rsi and 30 <= current_rsi < 50 else "正常"
                
                analysis["indicators"]["RSI"] = {
                    "value": current_rsi,
                    "signal": rsi_signal
                }
            
            # 3. 价格位置（相对于52周高低点）
            if "收盘" in df.columns:
                close_prices = df["收盘"].astype(float)
                high_52w = close_prices.max()
                low_52w = close_prices.min()
                current = close_prices.iloc[-1]
                position = (current - low_52w) / (high_52w - low_52w) * 100 if high_52w != low_52w else 50
                
                # 右侧交易偏好中高位（50%-85%为理想区间）
                if position > 85:
                    pos_signal = "极高"
                elif position > 70:
                    pos_signal = "高位"
                elif position > 50:
                    pos_signal = "中高位"
                elif position > 30:
                    pos_signal = "中位"
                elif position > 20:
                    pos_signal = "中低位"
                else:
                    pos_signal = "低位"
                
                analysis["indicators"]["PricePosition"] = {
                    "high_52w": float(high_52w),
                    "low_52w": float(low_52w),
                    "current": float(current),
                    "position_percent": float(position),
                    "signal": pos_signal
                }
            
            # 3.5. 价格突破分析（右侧交易关键指标）
            if "收盘" in df.columns:
                close_prices = df["收盘"].astype(float)
                current_price = close_prices.iloc[-1]
                # 计算近期高点（排除当前价格，看前20日、60日）
                if len(close_prices) >= 21:
                    high_20d_prev = close_prices.iloc[-21:-1].max()  # 前20日（不含今日）最高点
                    breakthrough_20d = current_price >= high_20d_prev * 0.995  # 突破或接近前20日高点
                else:
                    high_20d_prev = close_prices.iloc[:-1].max() if len(close_prices) > 1 else current_price
                    breakthrough_20d = current_price >= high_20d_prev * 0.995
                
                if len(close_prices) >= 61:
                    high_60d_prev = close_prices.iloc[-61:-1].max()  # 前60日（不含今日）最高点
                    breakthrough_60d = current_price >= high_60d_prev * 0.995
                elif len(close_prices) >= 21:
                    high_60d_prev = close_prices.iloc[:-1].max()
                    breakthrough_60d = current_price >= high_60d_prev * 0.995
                else:
                    high_60d_prev = None
                    breakthrough_60d = False
                
                # 计算包含当前价格的最高点（用于显示）
                high_20d = close_prices.tail(20).max()
                high_60d = close_prices.tail(60).max() if len(close_prices) >= 60 else None
                
                analysis["indicators"]["Breakthrough"] = {
                    "high_20d": float(high_20d),
                    "high_60d": float(high_60d) if high_60d else None,
                    "breakthrough_20d": breakthrough_20d,
                    "breakthrough_60d": breakthrough_60d
                }
            
            # 3.6. 动量指标（价格变化率）
            if "收盘" in df.columns:
                close_prices = df["收盘"].astype(float)
                # 计算5日、20日价格变化率
                momentum_5d = ((close_prices.iloc[-1] - close_prices.iloc[-6]) / close_prices.iloc[-6] * 100) if len(close_prices) >= 6 else 0
                momentum_20d = ((close_prices.iloc[-1] - close_prices.iloc[-21]) / close_prices.iloc[-21] * 100) if len(close_prices) >= 21 else 0
                
                analysis["indicators"]["Momentum"] = {
                    "momentum_5d": float(momentum_5d),
                    "momentum_20d": float(momentum_20d),
                    "signal": "强势" if momentum_5d > 3 and momentum_20d > 5 else 
                             "弱势" if momentum_5d < -3 or momentum_20d < -5 else "正常"
                }
            
            # 4. 成交量分析（增强版：包含成交量趋势和价量配合）
            if "成交量" in df.columns:
                volumes = df["成交量"].astype(float)
                avg_volume = volumes.tail(20).mean()
                current_volume = volumes.iloc[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                
                # 成交量趋势分析（5日均量 vs 20日均量）
                volume_ma5 = volumes.tail(5).mean() if len(volumes) >= 5 else avg_volume
                volume_ma20 = avg_volume
                volume_trend = "上升" if volume_ma5 > volume_ma20 else "下降"
                
                # 价量配合分析（价格上涨+放量 = 强势信号）
                price_volume_sync = False
                if "收盘" in df.columns:
                    price_change = (close_prices.iloc[-1] - close_prices.iloc[-2]) / close_prices.iloc[-2] * 100 if len(close_prices) >= 2 else 0
                    # 价格上涨且放量，或价格下跌且缩量，都是价量配合
                    price_volume_sync = (price_change > 0 and volume_ratio > 1.2) or (price_change < 0 and volume_ratio < 0.8)
                
                analysis["indicators"]["Volume"] = {
                    "current": float(current_volume),
                    "avg_20d": float(avg_volume),
                    "ratio": float(volume_ratio),
                    "signal": "放量" if volume_ratio > 1.5 else "缩量" if volume_ratio < 0.7 else "正常",
                    "trend": volume_trend,  # 成交量趋势
                    "price_volume_sync": price_volume_sync  # 价量配合
                }
            
            # 综合时机判断（右侧交易风格：追涨杀跌）
            timing_score = 0
            timing_factors = []
            
            # 1. 均线多头排列（右侧交易核心指标）
            ma_data = {}  # 初始化为空字典，避免未定义错误
            if "MA" in analysis["indicators"]:
                ma_data = analysis["indicators"]["MA"]
                if ma_data.get("bullish_arrangement", False):
                    timing_score += 3
                    timing_factors.append("✅ 均线多头排列，趋势强劲")
                elif ma_data.get("trend") == "上升":
                    timing_score += 1
                    timing_factors.append("✅ 均线呈上升趋势")
                elif ma_data.get("trend") == "下降":
                    timing_score -= 2
                    timing_factors.append("❌ 均线呈下降趋势，不适合右侧交易")
            else:
                # 没有MA数据时，不应该直接判断为下降趋势
                timing_score -= 1  # 数据不足时适当减分，但不直接判断为下降趋势
                timing_factors.append("⚠️ 均线数据不足，无法判断趋势")
            
            # 2. 价格在均线之上（只有在有 MA 数据时才检查）
            if ma_data and ma_data.get("price_above_ma", False):
                timing_score += 2
                timing_factors.append("✅ 价格位于均线之上，处于上升通道")
            elif ma_data:
                timing_score -= 1
                timing_factors.append("⚠️ 价格位于均线之下，趋势偏弱")
            
            # 3. RSI信号（右侧交易偏好强势但不超买）
            rsi_signal = None  # 初始化为 None，避免未定义错误
            rsi_value = None
            if "RSI" in analysis["indicators"]:
                rsi_data = analysis["indicators"]["RSI"]
                rsi_signal = rsi_data.get("signal", "正常")
                rsi_value = rsi_data.get("value")
            
            if rsi_signal and rsi_signal == "强势" and rsi_value and 50 <= rsi_value <= 70:
                timing_score += 2
                timing_factors.append("✅ RSI处于强势区间，动量充足")
            elif rsi_signal == "超买":
                timing_score -= 2
                timing_factors.append("⚠️ RSI超买，注意回调风险")
            elif rsi_signal == "超卖":
                timing_score -= 2
                timing_factors.append("❌ RSI超卖，不符合右侧交易风格")
            elif rsi_signal == "弱势":
                timing_score -= 1
                timing_factors.append("⚠️ RSI偏弱，缺乏上涨动力")
            
            # 4. 价格位置（右侧交易偏好中高位）
            price_signal = None  # 初始化为 None，避免未定义错误
            position_percent = 50
            if "PricePosition" in analysis["indicators"]:
                pos_data = analysis["indicators"]["PricePosition"]
                price_signal = pos_data.get("signal", "中位")
                position_percent = pos_data.get("position_percent", 50)
            
            if price_signal and price_signal in ["中高位", "高位"] and 50 <= position_percent <= 85:
                timing_score += 2
                timing_factors.append("✅ 价格处于中高位，符合右侧交易")
            elif price_signal == "极高" and position_percent > 85:
                timing_score -= 1
                timing_factors.append("⚠️ 价格处于极高位置，追高风险较大")
            elif price_signal and price_signal in ["低位", "中低位"]:
                timing_score -= 2
                timing_factors.append("❌ 价格处于低位，不符合右侧交易风格")
            
            # 5. 价格突破（右侧交易关键信号）
            if "Breakthrough" in analysis["indicators"]:
                breakthrough = analysis["indicators"]["Breakthrough"]
                if breakthrough.get("breakthrough_60d", False):
                    timing_score += 3
                    timing_factors.append("✅ 突破60日高点，强势突破信号")
                elif breakthrough.get("breakthrough_20d", False):
                    timing_score += 2
                    timing_factors.append("✅ 突破20日高点，趋势延续")
            
            # 6. 动量指标
            if "Momentum" in analysis["indicators"]:
                momentum = analysis["indicators"]["Momentum"]
                if momentum.get("signal") == "强势":
                    timing_score += 2
                    timing_factors.append(f"✅ 短期动量强劲（5日{momentum.get('momentum_5d', 0):.2f}%，20日{momentum.get('momentum_20d', 0):.2f}%）")
                elif momentum.get("signal") == "弱势":
                    timing_score -= 2
                    timing_factors.append("❌ 动量偏弱，缺乏上涨动力")
            
            # 7. 成交量（右侧交易需要放量确认，增强版：考虑价量配合）
            volume_signal = None  # 初始化为 None，避免未定义错误
            volume_ratio = 1.0
            volume_trend = None
            price_volume_sync = False
            if "Volume" in analysis["indicators"]:
                volume_data = analysis["indicators"]["Volume"]
                volume_signal = volume_data.get("signal", "正常")
                volume_ratio = volume_data.get("ratio", 1)
                volume_trend = volume_data.get("trend")
                price_volume_sync = volume_data.get("price_volume_sync", False)
            
            # 价量配合是强势信号（价格上涨+放量）
            if price_volume_sync and volume_ratio > 1.2:
                timing_score += 3
                timing_factors.append(f"✅ 价量配合良好，价格上涨伴随放量{volume_ratio:.2f}倍，资金积极介入")
            elif volume_signal == "放量" and volume_ratio > 1.5:
                timing_score += 2
                timing_factors.append(f"✅ 成交量放大{volume_ratio:.2f}倍，资金积极介入")
            elif volume_trend == "上升" and volume_ratio > 1.2:
                timing_score += 1
                timing_factors.append(f"✅ 成交量趋势上升，量比{volume_ratio:.2f}，资金关注度提升")
            elif volume_signal == "缩量":
                timing_score -= 1
                timing_factors.append("⚠️ 成交量萎缩，缺乏资金推动")
            
            # 综合评分和建议（右侧交易需要更高的评分阈值）
            analysis["timing"] = {
                "score": timing_score,
                "recommendation": "买入" if timing_score >= 6 else "观望" if timing_score >= 2 else "谨慎",
                "factors": timing_factors
            }
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_stock_technical_indicators_openbb(self, symbol: str, hist_data=None) -> Dict[str, Any]:
        """
        使用 akshare 数据计算技术指标并生成右侧交易信号
        （注意：方法名保持兼容，但实际使用 akshare 数据，不再依赖 OpenBB SDK）
        
        Args:
            symbol: 股票代码
            hist_data: 可选，已获取的历史数据（避免重复获取）
        
        Returns:
            包含技术指标和交易信号的字典
        """
        if not self.akshare:
            return {"error": "AKShare 不可用"}
        
        try:
            # 如果没有提供历史数据，则获取
            if hist_data is None or hist_data.empty:
                # 获取历史数据（最近1年）
                end_date = datetime.now().strftime("%Y%m%d")
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
                
                print(f"  使用 akshare 数据计算 {symbol} 技术指标...")
                hist_data = self.akshare.get_stock_historical(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    period="daily",
                    adjust="qfq"  # 前复权
                )
            else:
                print(f"  使用已获取的历史数据计算 {symbol} 技术指标...")
            
            if hist_data.empty:
                return {"error": "无法获取历史数据"}
            
            # 转换为DataFrame并标准化列名
            import pandas as pd
            import numpy as np
            
            # 标准化列名（akshare 可能使用中文列名）
            df = hist_data.copy()
            if "收盘" in df.columns:
                df["close"] = df["收盘"].astype(float)
            elif "close" not in df.columns:
                return {"error": "无法找到收盘价数据"}
            
            close_prices = df["close"]
            if len(close_prices) < 50:
                return {"error": "历史数据不足，至少需要50个交易日"}
            
            # 计算技术指标
            indicators = {}
            signals = []
            
            # 1. 移动平均线（MA）- SMA50 和 SMA200
            sma_50 = close_prices.rolling(window=50).mean()
            sma_200 = close_prices.rolling(window=200).mean() if len(close_prices) >= 200 else None
            
            current_price = close_prices.iloc[-1]
            current_sma50 = sma_50.iloc[-1]
            current_sma200 = sma_200.iloc[-1] if sma_200 is not None and pd.notna(sma_200.iloc[-1]) else None
            
            # 均线交叉信号（右侧交易：短期均线上穿长期均线）
            ma_cross_signal = False
            if current_sma200 and len(sma_50) >= 2 and len(sma_200) >= 2:
                ma_cross_signal = (sma_50.iloc[-1] > sma_200.iloc[-1]) and (sma_50.iloc[-2] <= sma_200.iloc[-2])
            
            indicators["MA"] = {
                "SMA50": float(current_sma50) if pd.notna(current_sma50) else None,
                "SMA200": float(current_sma200) if current_sma200 else None,
                "price_above_sma50": current_price > current_sma50 if pd.notna(current_sma50) else False,
                "price_above_sma200": current_price > current_sma200 if current_sma200 else False,
                "ma_cross_signal": ma_cross_signal,
                "trend": "上升" if (current_sma200 and current_sma50 > current_sma200) or (not current_sma200 and pd.notna(current_sma50)) else "下降" if current_sma200 else "未知"
            }
            
            if ma_cross_signal:
                signals.append("✅ 均线交叉：短期均线上穿长期均线，买入信号")
            
            # 2. RSI指标（使用 pandas 计算）
            try:
                delta = close_prices.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None
                
                if current_rsi is not None:
                    # RSI信号（右侧交易：RSI在50-70区间为强势）
                    rsi_signal = "超买" if current_rsi > 70 else \
                               "超卖" if current_rsi < 30 else \
                               "强势" if 50 <= current_rsi <= 70 else \
                               "弱势" if 30 <= current_rsi < 50 else "正常"
                    
                    indicators["RSI"] = {
                        "value": current_rsi,
                        "signal": rsi_signal
                    }
                    
                    # RSI超卖区回升信号（右侧交易）
                    if current_rsi < 30 and len(rsi) >= 2:
                        prev_rsi = rsi.iloc[-2]
                        if pd.notna(prev_rsi) and current_rsi > prev_rsi:
                            signals.append("✅ RSI超卖区回升：从超卖区反弹，买入信号")
            except Exception as e:
                print(f"  ⚠️ 计算RSI失败: {e}")
            
            # 3. MACD指标（使用 pandas 计算）
            try:
                # 计算EMA
                ema_12 = close_prices.ewm(span=12, adjust=False).mean()
                ema_26 = close_prices.ewm(span=26, adjust=False).mean()
                
                # MACD线 = EMA12 - EMA26
                macd_line = ema_12 - ema_26
                
                # 信号线 = MACD的9日EMA
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                
                # 柱状图 = MACD - 信号线
                histogram = macd_line - signal_line
                
                current_macd = macd_line.iloc[-1]
                current_signal = signal_line.iloc[-1]
                current_histogram = histogram.iloc[-1]
                
                # MACD交叉信号（右侧交易：MACD上穿信号线）
                macd_cross_signal = False
                if len(macd_line) >= 2 and len(signal_line) >= 2:
                    macd_cross_signal = (macd_line.iloc[-1] > signal_line.iloc[-1]) and (macd_line.iloc[-2] <= signal_line.iloc[-2])
                
                indicators["MACD"] = {
                    "macd": float(current_macd) if pd.notna(current_macd) else None,
                    "signal": float(current_signal) if pd.notna(current_signal) else None,
                    "histogram": float(current_histogram) if pd.notna(current_histogram) else None,
                    "macd_cross_signal": macd_cross_signal
                }
                
                if macd_cross_signal:
                    signals.append("✅ MACD交叉：MACD上穿信号线，买入信号")
            except Exception as e:
                print(f"  ⚠️ 计算MACD失败: {e}")
            
            # 4. 布林带（Bollinger Bands）- 使用 pandas 计算
            try:
                # 计算20日移动平均线
                sma_20 = close_prices.rolling(window=20).mean()
                
                # 计算20日标准差
                std_20 = close_prices.rolling(window=20).std()
                
                # 上轨 = SMA20 + 2 * STD
                upper_band = sma_20 + (2 * std_20)
                
                # 下轨 = SMA20 - 2 * STD
                lower_band = sma_20 - (2 * std_20)
                
                current_upper = upper_band.iloc[-1]
                current_lower = lower_band.iloc[-1]
                current_middle = sma_20.iloc[-1]
                
                # 布林带信号（右侧交易：价格突破上轨）
                bb_signal = None
                if pd.notna(current_upper) and pd.notna(current_lower):
                    if current_price > current_upper:
                        bb_signal = "突破上轨"
                    elif current_price < current_lower:
                        bb_signal = "跌破下轨"
                    else:
                        bb_signal = "正常区间"
                
                indicators["BollingerBands"] = {
                    "upper": float(current_upper) if pd.notna(current_upper) else None,
                    "middle": float(current_middle) if pd.notna(current_middle) else None,
                    "lower": float(current_lower) if pd.notna(current_lower) else None,
                    "current_price": float(current_price),
                    "signal": bb_signal
                }
                
                if bb_signal == "突破上轨":
                    signals.append("✅ 布林带突破：价格突破上轨，强势信号")
            except Exception as e:
                print(f"  ⚠️ 计算布林带失败: {e}")
            
            return {
                "symbol": symbol,
                "indicators": indicators,
                "signals": signals,
                "data_points": len(df),
                "source": "akshare"  # 标记数据来源
            }
            
        except Exception as e:
            # 返回错误信息但不影响整体流程
            error_msg = str(e)
            return {"error": f"技术指标计算失败: {error_msg[:200]}"}
    
    async def get_stock_mcp_analysis(self, symbol: str, hist_data=None, fundamentals=None) -> Dict[str, Any]:
        """
        使用 OpenBB MCP 获取股票分析和预测数据
        优先使用 MCP 工具，如果失败则使用 akshare 数据作为 fallback
        
        Args:
            symbol: 股票代码
            hist_data: 可选，已获取的历史数据（来自 akshare）
            fundamentals: 可选，已获取的基本面数据（来自 akshare）
        
        Returns:
            包含 MCP 分析结果的字典
        """
        if not self.analyzer:
            return {"error": "MarketStructureAnalyzer 不可用"}
        
        try:
            import pandas as pd
            
            # 转换 A 股代码格式为 OpenBB 格式（如果需要）
            openbb_symbol = self._convert_to_openbb_symbol(symbol) if len(symbol) == 6 else symbol

            # 纯 A 股六代码：不调用 MCP + yfinance（Yahoo 对 .SS/.SZ 易限流且不稳定）
            use_yfinance_mcp = not (
                symbol
                and len(symbol) == 6
                and symbol.isdigit()
            )

            mcp_result = {
                "symbol": symbol,
                "openbb_symbol": openbb_symbol,
                "prediction": None,
                "valuation": None,
                "financial_metrics": None,
                "buy_signal": None,
                "data_source": "mcp"  # 标记数据来源
            }
            if not use_yfinance_mcp:
                mcp_result["data_source"] = "akshare"
            
            # 优化：如果已有 akshare 数据，直接使用，跳过 MCP 调用以节省时间
            # 或者只尝试第一个工具名称，快速失败
            
            # 1. 尝试获取股票基本信息（估值数据）
            try:
                mcp_valuation_success = False
                
                # 如果已有 akshare 基本面数据，优先使用，跳过 MCP 调用
                if fundamentals and isinstance(fundamentals, dict):
                    # 检查是否有可用的估值数据
                    has_valuation_data = any(key in fundamentals for key in ["市盈率", "PE", "市净率", "PB"])
                    if has_valuation_data:
                        print(f"    📊 直接使用 akshare 基本面数据作为估值数据源（跳过 MCP 调用）...")
                        # 直接使用 akshare 数据，不调用 MCP
                        akshare_valuation = {}
                        if "市盈率" in fundamentals or "PE" in fundamentals:
                            pe = fundamentals.get("市盈率") or fundamentals.get("PE")
                            if pe:
                                akshare_valuation["pe_ratio"] = float(pe) if pd.notna(pe) else None
                        if "市净率" in fundamentals or "PB" in fundamentals:
                            pb = fundamentals.get("市净率") or fundamentals.get("PB")
                            if pb:
                                akshare_valuation["pb_ratio"] = float(pb) if pd.notna(pb) else None
                        if akshare_valuation:
                            mcp_result["valuation"] = akshare_valuation
                            mcp_result["data_source"] = "akshare"
                            mcp_valuation_success = True
                            print(f"    ✅ 从 akshare 获取到估值数据")
                
                # 如果没有 akshare 数据，尝试 MCP（仅非 A 股或显式需要时；A 股跳过 yfinance）
                if not mcp_valuation_success and use_yfinance_mcp:
                    # 只尝试最可能的工具名称，避免长时间等待
                    tool_name = "equity_profile"
                    try:
                        import asyncio
                        # 使用较短的超时（5秒），快速失败
                        profile_result = await asyncio.wait_for(
                            self.analyzer.call_mcp_tool(
                                tool_name,
                                {
                                    "symbol": openbb_symbol or symbol,
                                    "provider": "yfinance"
                                }
                            ),
                            timeout=5.0  # 5秒超时
                        )
                        
                        if profile_result and "error" not in profile_result:
                            # 提取估值数据
                            if "results" in profile_result:
                                profile_data = profile_result["results"]
                                if isinstance(profile_data, list) and len(profile_data) > 0:
                                    profile_data = profile_data[0]
                                
                                mcp_result["valuation"] = {
                                    "market_cap": profile_data.get("market_cap"),
                                    "pe_ratio": profile_data.get("pe_ratio"),
                                    "pb_ratio": profile_data.get("pb_ratio"),
                                    "dividend_yield": profile_data.get("dividend_yield")
                                }
                                mcp_valuation_success = True
                                mcp_result["data_source"] = "mcp"
                    except (asyncio.TimeoutError, Exception) as e:
                        # 快速失败，不尝试其他工具名称
                        print(f"    ⚠️ MCP 估值工具调用失败或超时: {str(e)[:50]}")
                elif not mcp_valuation_success and not use_yfinance_mcp:
                    print(f"    🇨🇳 A 股跳过 MCP/yfinance 估值（避免 Yahoo 限流）")

                # 如果 MCP 获取失败，尝试使用 akshare 基本面数据（作为最后的 fallback）
                if not mcp_valuation_success and fundamentals and isinstance(fundamentals, dict):
                    print(f"    📊 使用 akshare 基本面数据作为估值数据源...")
                    akshare_valuation = {}
                    
                    # 从 akshare 基本面数据中提取估值指标
                    if "市盈率" in fundamentals or "PE" in fundamentals:
                        pe = fundamentals.get("市盈率") or fundamentals.get("PE")
                        if pe:
                            akshare_valuation["pe_ratio"] = float(pe) if pd.notna(pe) else None
                    
                    if "市净率" in fundamentals or "PB" in fundamentals:
                        pb = fundamentals.get("市净率") or fundamentals.get("PB")
                        if pb:
                            akshare_valuation["pb_ratio"] = float(pb) if pd.notna(pb) else None
                    
                    if akshare_valuation:
                        mcp_result["valuation"] = akshare_valuation
                        mcp_result["data_source"] = "akshare"  # 标记数据来源为 akshare
                        print(f"    ✅ 从 akshare 获取到估值数据")
                        
            except Exception as e:
                print(f"    ⚠️ 获取估值数据失败: {str(e)[:100]}")
            
            # 2. 尝试获取财务指标
            # 优化：如果已有 akshare 数据，直接使用，跳过 MCP 调用
            try:
                mcp_metrics_success = False
                
                # 如果已有 akshare 基本面数据，优先使用，跳过 MCP 调用
                if fundamentals and isinstance(fundamentals, dict):
                    # 检查是否有可用的财务指标数据
                    has_metrics_data = any(key in fundamentals for key in ["净资产收益率", "ROE", "每股收益", "EPS", "净利润"])
                    if has_metrics_data:
                        print(f"    📊 直接使用 akshare 基本面数据作为财务指标数据源（跳过 MCP 调用）...")
                        # 直接使用 akshare 数据，不调用 MCP
                        akshare_metrics = {}
                        if "净资产收益率" in fundamentals or "ROE" in fundamentals:
                            roe = fundamentals.get("净资产收益率") or fundamentals.get("ROE")
                            if roe:
                                akshare_metrics["roe"] = float(roe) if pd.notna(roe) else None
                        if "每股收益" in fundamentals or "EPS" in fundamentals:
                            eps = fundamentals.get("每股收益") or fundamentals.get("EPS")
                            if eps:
                                akshare_metrics["eps"] = float(eps) if pd.notna(eps) else None
                        if "净利润" in fundamentals:
                            net_income = fundamentals.get("净利润")
                            if net_income:
                                akshare_metrics["net_income"] = float(net_income) if pd.notna(net_income) else None
                        if akshare_metrics:
                            mcp_result["financial_metrics"] = akshare_metrics
                            if mcp_result["data_source"] == "mcp":
                                mcp_result["data_source"] = "mixed"
                            else:
                                mcp_result["data_source"] = "akshare"
                            mcp_metrics_success = True
                            print(f"    ✅ 从 akshare 获取到财务指标")
                
                # 如果没有 akshare 数据，尝试 MCP（A 股跳过 yfinance）
                if not mcp_metrics_success and use_yfinance_mcp:
                    # 只尝试最可能的工具名称，避免长时间等待
                    tool_name = "equity_fundamental_metrics"
                    try:
                        import asyncio
                        # 使用较短的超时（5秒），快速失败
                        metrics_result = await asyncio.wait_for(
                            self.analyzer.call_mcp_tool(
                                tool_name,
                                {
                                    "symbol": openbb_symbol or symbol,
                                    "provider": "yfinance"
                                }
                            ),
                            timeout=5.0  # 5秒超时
                        )
                        
                        if metrics_result and "error" not in metrics_result:
                            if "results" in metrics_result:
                                metrics_data = metrics_result["results"]
                                if isinstance(metrics_data, list) and len(metrics_data) > 0:
                                    metrics_data = metrics_data[0]
                                
                                mcp_result["financial_metrics"] = {
                                    "revenue_growth": metrics_data.get("revenue_growth"),
                                    "net_income": metrics_data.get("net_income"),
                                    "eps": metrics_data.get("eps"),
                                    "roe": metrics_data.get("roe")
                                }
                                mcp_metrics_success = True
                                if mcp_result["data_source"] == "akshare":
                                    mcp_result["data_source"] = "mixed"
                                else:
                                    mcp_result["data_source"] = "mcp"
                    except (asyncio.TimeoutError, Exception) as e:
                        # 快速失败，不尝试其他工具名称
                        print(f"    ⚠️ MCP 财务指标工具调用失败或超时: {str(e)[:50]}")
                elif not mcp_metrics_success and not use_yfinance_mcp:
                    print(f"    🇨🇳 A 股跳过 MCP/yfinance 财务指标（避免 Yahoo 限流）")

                # 如果 MCP 获取失败，尝试使用 akshare 基本面数据（作为最后的 fallback）
                if not mcp_metrics_success and fundamentals and isinstance(fundamentals, dict):
                    print(f"    📊 使用 akshare 基本面数据作为财务指标数据源...")
                    akshare_metrics = {}
                    
                    # 从 akshare 基本面数据中提取财务指标
                    if "净资产收益率" in fundamentals or "ROE" in fundamentals:
                        roe = fundamentals.get("净资产收益率") or fundamentals.get("ROE")
                        if roe:
                            akshare_metrics["roe"] = float(roe) if pd.notna(roe) else None
                    
                    if "每股收益" in fundamentals or "EPS" in fundamentals:
                        eps = fundamentals.get("每股收益") or fundamentals.get("EPS")
                        if eps:
                            akshare_metrics["eps"] = float(eps) if pd.notna(eps) else None
                    
                    if "净利润" in fundamentals:
                        net_income = fundamentals.get("净利润")
                        if net_income:
                            akshare_metrics["net_income"] = float(net_income) if pd.notna(net_income) else None
                    
                    if akshare_metrics:
                        mcp_result["financial_metrics"] = akshare_metrics
                        if mcp_result["data_source"] == "mcp":
                            mcp_result["data_source"] = "mixed"  # 部分数据来自 akshare
                        else:
                            mcp_result["data_source"] = "akshare"
                        print(f"    ✅ 从 akshare 获取到财务指标")
                        
            except Exception as e:
                print(f"    ⚠️ 获取财务指标失败: {str(e)[:100]}")
            
            # 3. 如果有历史数据，计算预测和买入信号
            if hist_data is not None and not hist_data.empty:
                try:
                    # 计算当前价格和均线
                    if "收盘" in hist_data.columns:
                        close_prices = hist_data["收盘"].astype(float)
                        current_price = close_prices.iloc[-1]
                        sma_50 = close_prices.rolling(window=50).mean().iloc[-1] if len(close_prices) >= 50 else None
                        
                        # 简单的价格预测（基于趋势）
                        if sma_50 and pd.notna(sma_50):
                            price_trend = "上升" if current_price > sma_50 else "下降"
                            predicted_price = current_price * 1.05 if price_trend == "上升" else current_price * 0.95
                            
                            mcp_result["prediction"] = {
                                "current_price": float(current_price),
                                "predicted_price": float(predicted_price),
                                "price_change_pct": float((predicted_price - current_price) / current_price * 100),
                                "trend": price_trend,
                                "confidence": "中等"  # 可以基于更多指标计算
                            }
                            
                            # 生成买入信号（结合 MCP 预测和技术指标）
                            buy_signal = False
                            buy_reasons = []
                            
                            # 条件1: 价格突破50日均线
                            if current_price > sma_50:
                                buy_signal = True
                                buy_reasons.append("价格突破50日均线")
                            
                            # 条件2: MCP 预测价格上涨
                            if predicted_price > current_price:
                                buy_signal = True
                                buy_reasons.append(f"MCP预测价格上涨 {mcp_result['prediction']['price_change_pct']:.2f}%")
                            
                            mcp_result["buy_signal"] = {
                                "signal": buy_signal,
                                "reasons": buy_reasons,
                                "strength": "强" if len(buy_reasons) >= 2 else "中等" if buy_signal else "弱"
                            }
                except Exception as e:
                    print(f"    ⚠️ 计算预测失败: {str(e)[:100]}")
            
            return mcp_result
            
        except Exception as e:
            return {"error": f"MCP 分析失败: {str(e)[:200]}"}
    
    def _convert_to_openbb_symbol(self, symbol: str) -> Optional[str]:
        """
        将A股代码转换为OpenBB格式
        
        Args:
            symbol: A股代码（如 "600519" 或 "000001"）
        
        Returns:
            OpenBB格式代码（如 "600519.SS" 或 "000001.SZ"），如果无法转换返回None
        """
        if not symbol or len(symbol) != 6:
            return None
        
        # 上海股票（6开头）
        if symbol.startswith("6"):
            return f"{symbol}.SS"
        # 深圳股票（0或3开头）
        elif symbol.startswith("0") or symbol.startswith("3"):
            return f"{symbol}.SZ"
        else:
            return None
    
    def get_stock_fundamentals_akshare(self, symbol: str, stock_info=None, hist_data=None) -> Dict[str, Any]:
        """
        使用 akshare 获取股票基本面数据
        
        Args:
            symbol: 股票代码
            stock_info: 可选，已获取的股票基本信息（避免重复获取）
            hist_data: 可选，已获取的历史数据（避免重复获取）
        
        Returns:
            基本面数据
        """
        if not self.akshare:
            return {"error": "AKShare 不可用"}
        
        try:
            # 如果没有提供基本信息，则获取
            if stock_info is None:
                info = self.akshare.get_stock_info(symbol)
            else:
                info = stock_info
            
            # 获取基本面数据
            fundamentals = self.akshare.get_stock_fundamentals(symbol)
            
            # 如果没有提供历史数据，则获取（用于计算）
            if hist_data is None or hist_data.empty:
                end_date = datetime.now().strftime("%Y%m%d")
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
                hist_data = self.akshare.get_stock_historical(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
            
            result = {
                "symbol": symbol,
                "info": info,
                "fundamentals": fundamentals,
                "price_data": {
                    "current": float(hist_data.iloc[-1]["收盘"]) if not hist_data.empty and "收盘" in hist_data.columns else None,
                    "high_52w": float(hist_data["收盘"].max()) if not hist_data.empty and "收盘" in hist_data.columns else None,
                    "low_52w": float(hist_data["收盘"].min()) if not hist_data.empty and "收盘" in hist_data.columns else None
                } if not hist_data.empty else {}
            }
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def _hist_to_price_series(self, hist_data, max_days: int = 120) -> Optional[Dict[str, Any]]:
        """从历史 K 线提取最近若干交易日的日期与收盘价，供前端绘制走势小图。"""
        try:
            import pandas as pd

            if hist_data is None or hist_data.empty:
                return None
            df = hist_data.tail(max_days).copy()
            date_col = next((c for c in ("日期", "date", "Date") if c in df.columns), None)
            close_col = next((c for c in ("收盘", "close", "Close") if c in df.columns), None)
            if not date_col or not close_col:
                return None
            dt = pd.to_datetime(df[date_col], errors="coerce")
            closes = df[close_col]
            dates_out: List[str] = []
            closes_out: List[float] = []
            for d, c in zip(dt, closes):
                if pd.isna(d) or pd.isna(c):
                    continue
                dates_out.append(d.strftime("%Y-%m-%d"))
                closes_out.append(float(c))
            if len(closes_out) < 2:
                return None
            return {"dates": dates_out, "close": closes_out}
        except Exception:
            return None

    async def analyze_custom_stocks(
        self,
        stock_symbols: List[str],
        market_type: str = "A股"
    ) -> Dict[str, Any]:
        """
        分析用户提供的股票列表
        
        Args:
            stock_symbols: 股票代码列表
            market_type: 市场类型
        
        Returns:
            分析结果
        """
        print(f"\n{'='*60}")
        print(f"📊 分析 {len(stock_symbols)} 只自定义股票")
        print(f"{'='*60}\n")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "market_type": market_type,
            "stocks": []
        }
        
        # 并行处理多只股票（优化性能）
        # 使用 asyncio.gather 并行处理，但限制并发数避免API限流
        async def analyze_single_stock(symbol: str, index: int, total: int) -> Dict[str, Any]:
            """分析单只股票的异步函数"""
            try:
                print(f"[{index}/{total}] 分析 {symbol}...")
                
                stock_analysis = {
                    "symbol": symbol,
                    "timing": {},
                    "fundamentals": {},
                    "profile": {}
                }
                
                # ========== 第一步：获取所有数据 ==========
                # 先获取所有需要的数据，然后再进行计算，确保计算使用最新、最完整的数据
                hist_data = None
                stock_info = None
                realtime_data = None
                fundamentals = None
                
                if self.akshare:
                    # 1. 获取历史数据（所有分析方法都需要）
                    end_date = datetime.now().strftime("%Y%m%d")
                    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
                    print(f"  📥 获取历史数据...")
                    hist_data = self.akshare.get_stock_historical(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        period="daily",
                        adjust="qfq"
                    )
                    if not hist_data.empty:
                        print(f"    ✅ 获取到 {len(hist_data)} 条历史数据")
                    
                    # 2. 获取基本信息（只获取一次）
                    print(f"  📋 获取股票基本信息...")
                    stock_info = self.akshare.get_stock_info(symbol)
                    if stock_info:
                        print(f"    ✅ 获取到基本信息")
                        stock_analysis["profile"] = {
                            "info": stock_info,
                            "name": stock_info.get("股票简称", stock_info.get("名称", symbol)),
                            "industry": stock_info.get("所属行业", stock_info.get("行业", "N/A")),
                            "concept": stock_info.get("概念板块", "N/A")
                        }
                        print(f"    股票名称: {stock_analysis['profile'].get('name', 'N/A')}")
                        print(f"    所属行业: {stock_analysis['profile'].get('industry', 'N/A')}")
                    
                    # 3. 获取实时行情（在计算之前获取，确保计算使用最新价格）
                    if self.akshare.itick_available:
                        print(f"  📡 获取实时行情...")
                        try:
                            realtime_data = self.akshare._get_realtime_from_itick(symbol)
                            if realtime_data:
                                print(f"    ✅ 获取到实时行情数据")
                            else:
                                print(f"    ⚠️ 实时行情数据为空")
                        except Exception as e:
                            print(f"    ⚠️ 获取实时行情失败: {str(e)[:100]}")
                    
                    # 4. 获取基本面数据（包含财务指标，也可能包含实时行情）
                    print(f"  📈 获取基本面数据...")
                    fundamentals = self.get_stock_fundamentals_akshare(symbol, stock_info=stock_info, hist_data=hist_data)
                    stock_analysis["fundamentals"] = fundamentals
                    
                    # 如果基本面数据中包含了实时行情，合并到 realtime_data
                    if fundamentals and isinstance(fundamentals, dict):
                        # 检查是否有实时行情数据（iTick API 可能在 get_stock_fundamentals 中已调用）
                        if not realtime_data and any(key in fundamentals for key in ['current_price', '最新价', 'price', '实时价格']):
                            realtime_data = {k: v for k, v in fundamentals.items() 
                                           if k in ['current_price', '最新价', 'price', '实时价格', '涨跌幅', 'change_percent', '成交量', 'volume']}
                
                # ========== 第二步：使用完整数据进行计算 ==========
                # 现在所有数据都已获取，可以进行计算了
                
                # 1. 时机分析（使用完整数据：历史数据 + 实时行情）
                if self.akshare and hist_data is not None and not hist_data.empty:
                    print(f"  ⏰ 分析买入时机（使用完整数据）...")
                    timing = self.get_stock_timing_analysis(symbol, hist_data=hist_data)
                    stock_analysis["timing"] = timing
                elif self.akshare:
                    print(f"  ⏰ 分析买入时机...")
                    timing = self.get_stock_timing_analysis(symbol)
                    stock_analysis["timing"] = timing
                    
                # 2. 技术指标分析（使用完整数据：历史数据 + 实时行情）
                if self.akshare and hist_data is not None and not hist_data.empty:
                    print(f"  📊 计算技术指标（MACD、布林带等，使用完整数据）...")
                    technical_analysis = self.get_stock_technical_indicators_openbb(symbol, hist_data=hist_data)
                    if "error" not in technical_analysis:
                        stock_analysis["openbb_indicators"] = technical_analysis  # 保持字段名兼容
                        if technical_analysis.get("signals"):
                            print(f"    发现 {len(technical_analysis['signals'])} 个交易信号")
                    else:
                        print(f"    ⚠️ 技术指标计算失败: {technical_analysis.get('error')}")
                elif self.akshare:
                    print(f"  📊 计算技术指标（MACD、布林带等）...")
                    technical_analysis = self.get_stock_technical_indicators_openbb(symbol)
                    if "error" not in technical_analysis:
                        stock_analysis["openbb_indicators"] = technical_analysis
                        if technical_analysis.get("signals"):
                            print(f"    发现 {len(technical_analysis['signals'])} 个交易信号")
                    else:
                        print(f"    ⚠️ 技术指标计算失败: {technical_analysis.get('error')}")
                
                # 显示时机分析结果
                timing = stock_analysis.get("timing", {})
                if "timing" in timing:
                    rec = timing["timing"]["recommendation"]
                    score = timing["timing"]["score"]
                    print(f"    时机评分: {score}, 建议: {rec}")
                    
                    # 显示详细的技术指标
                    indicators = timing.get("indicators", {})
                    if indicators:
                        print(f"    📊 技术指标:")
                        
                        # 均线指标
                        if "MA" in indicators:
                            ma = indicators["MA"]
                            ma_str = f"      均线: MA5={ma.get('MA5', 0):.2f}, MA20={ma.get('MA20', 0):.2f}"
                            if ma.get('MA60'):
                                ma_str += f", MA60={ma.get('MA60', 0):.2f}"
                            ma_str += f", 趋势={ma.get('trend', 'N/A')}"
                            if ma.get('bullish_arrangement'):
                                ma_str += " ✅多头排列"
                            if ma.get('price_above_ma'):
                                ma_str += " ✅价格在均线之上"
                            print(ma_str)
                        
                        # RSI指标
                        if "RSI" in indicators:
                            rsi = indicators["RSI"]
                            rsi_value = rsi.get('value', 0)
                            rsi_signal = rsi.get('signal', 'N/A')
                            print(f"      RSI: {rsi_value:.2f} ({rsi_signal})")
                        
                        # 价格位置
                        if "PricePosition" in indicators:
                            pos = indicators["PricePosition"]
                            position_pct = pos.get('position_percent', 0)
                            pos_signal = pos.get('signal', 'N/A')
                            current_price = pos.get('current', 0)
                            print(f"      价格位置: {current_price:.2f} ({position_pct:.1f}%, {pos_signal})")
                        
                        # 突破分析
                        if "Breakthrough" in indicators:
                            bt = indicators["Breakthrough"]
                            if bt.get('breakthrough_60d'):
                                print(f"      突破: ✅突破60日高点")
                            elif bt.get('breakthrough_20d'):
                                print(f"      突破: ✅突破20日高点")
                            else:
                                print(f"      突破: 未突破近期高点")
                        
                        # 动量指标
                        if "Momentum" in indicators:
                            mom = indicators["Momentum"]
                            momentum_5d = mom.get('momentum_5d', 0)
                            momentum_20d = mom.get('momentum_20d', 0)
                            mom_signal = mom.get('signal', 'N/A')
                            print(f"      动量: 5日={momentum_5d:.2f}%, 20日={momentum_20d:.2f}% ({mom_signal})")
                        
                        # 成交量
                        if "Volume" in indicators:
                            vol = indicators["Volume"]
                            volume_ratio = vol.get('ratio', 1)
                            vol_signal = vol.get('signal', 'N/A')
                            print(f"      成交量: 量比={volume_ratio:.2f} ({vol_signal})")
                    
                    elif "error" in timing:
                        print(f"    ⚠️ 时机分析失败: {timing['error']}")
                
                # 3. OpenBB MCP 分析（如果 MCP 可用，集成 akshare 数据）
                if self.analyzer and hasattr(self.analyzer, 'call_mcp_tool'):
                    print(f"  🤖 OpenBB MCP 分析（集成 akshare 数据）...")
                    try:
                        # 传递 akshare 获取的基本面数据，作为 MCP 的 fallback
                        mcp_analysis = await self.get_stock_mcp_analysis(
                            symbol, 
                            hist_data=hist_data,
                            fundamentals=fundamentals
                        )
                        if mcp_analysis and "error" not in mcp_analysis:
                            stock_analysis["mcp_analysis"] = mcp_analysis
                            data_source = mcp_analysis.get("data_source", "unknown")
                            if mcp_analysis.get("prediction"):
                                print(f"    ✅ 获取到预测数据（数据源: {data_source}）")
                            if mcp_analysis.get("valuation"):
                                print(f"    ✅ 获取到估值数据（数据源: {data_source}）")
                            if mcp_analysis.get("financial_metrics"):
                                print(f"    ✅ 获取到财务指标（数据源: {data_source}）")
                        else:
                            print(f"    ⚠️ MCP 分析失败: {mcp_analysis.get('error', '未知错误') if mcp_analysis else '无响应'}")
                    except Exception as e:
                        print(f"    ⚠️ MCP 分析异常: {str(e)[:100]}")
            
                if hist_data is not None and not hist_data.empty:
                    ps = self._hist_to_price_series(hist_data, max_days=120)
                    if ps:
                        stock_analysis["price_series"] = ps

                print()
                return stock_analysis
            except Exception as e:
                print(f"  ❌ 分析 {symbol} 时出错: {str(e)[:200]}")
                return {
                    "symbol": symbol,
                    "error": str(e),
                    "timing": {},
                    "fundamentals": {},
                    "profile": {}
                }
        
        # 并行处理股票列表（限制并发数为3，避免API限流）
        max_concurrent = 3  # 同时分析3只股票
        
        # 分批并行处理，每批最多3只股票
        for batch_start in range(0, len(stock_symbols), max_concurrent):
            batch_symbols = stock_symbols[batch_start:batch_start + max_concurrent]
            batch_indices = range(batch_start + 1, batch_start + len(batch_symbols) + 1)
            
            # 创建任务
            tasks = [
                analyze_single_stock(symbol, idx, len(stock_symbols))
                for symbol, idx in zip(batch_symbols, batch_indices)
            ]
            
            # 并行执行
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"  ⚠️ 分析出错: {str(result)[:100]}")
                    results["stocks"].append({
                        "symbol": "UNKNOWN",
                        "error": str(result),
                        "timing": {},
                        "fundamentals": {},
                        "profile": {}
                    })
                else:
                    results["stocks"].append(result)
        
        return results
    
    def format_custom_analysis_report(self, analysis: Dict[str, Any]) -> str:
        """
        格式化自定义股票分析报告
        
        Args:
            analysis: 分析结果
        
        Returns:
            格式化的报告文本
        """
        print("  📝 开始生成报告...")
        report = []
        report.append("="*60)
        report.append("自定义股票分析报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("="*60)
        report.append("")
        
        stocks = analysis.get("stocks", [])
        print(f"  📊 处理 {len(stocks)} 只股票的报告...")
        
        for i, stock in enumerate(stocks, 1):
            if i % 5 == 0:  # 每5只股票显示一次进度
                print(f"    处理进度: {i}/{len(stocks)}")
            symbol = stock.get("symbol", "N/A")
            
            # 获取股票基本信息
            profile = stock.get("profile", {})
            stock_name = profile.get("name", symbol) if isinstance(profile, dict) else symbol
            industry = profile.get("industry", "N/A") if isinstance(profile, dict) else "N/A"
            
            report.append(f"\n股票代码: {symbol}")
            if stock_name and stock_name != symbol:
                report.append(f"股票名称: {stock_name}")
            if industry and industry != "N/A":
                report.append(f"所属行业: {industry}")
            report.append("-"*60)
            
            # 时机分析
            timing = stock.get("timing", {})
            if timing:
                if "timing" in timing:
                    timing_info = timing["timing"]
                    report.append(f"\n⏰ 买入时机分析:")
                    report.append(f"  综合评分: {timing_info.get('score', 0)}")
                    report.append(f"  建议: {timing_info.get('recommendation', 'N/A')}")
                    
                    # 关键因素
                    factors = timing_info.get("factors", [])
                    if factors:
                        report.append(f"\n  关键因素:")
                        for factor in factors:
                            report.append(f"    {factor}")
                    else:
                        report.append(f"\n  关键因素: 暂无")
                    
                    # 技术指标（右侧交易风格）
                    indicators = timing.get("indicators", {})
                    if indicators:
                        report.append(f"\n  技术指标（右侧交易）:")
                        if "MA" in indicators:
                            ma = indicators["MA"]
                            ma_str = f"    均线: MA5={ma.get('MA5', 0):.2f}, MA20={ma.get('MA20', 0):.2f}"
                            if ma.get('MA60'):
                                ma_str += f", MA60={ma.get('MA60', 0):.2f}"
                            ma_str += f", 趋势={ma.get('trend', 'N/A')}"
                            if ma.get('bullish_arrangement'):
                                ma_str += ", 多头排列✅"
                            if ma.get('price_above_ma'):
                                ma_str += ", 价格在均线之上✅"
                            report.append(ma_str)
                        if "RSI" in indicators:
                            rsi = indicators["RSI"]
                            rsi_value = rsi.get('value')
                            if rsi_value is not None:
                                report.append(f"    RSI: {rsi_value:.2f} ({rsi.get('signal', 'N/A')})")
                        if "PricePosition" in indicators:
                            pos = indicators["PricePosition"]
                            position_pct = pos.get('position_percent')
                            if position_pct is not None:
                                report.append(f"    价格位置: {position_pct:.1f}% ({pos.get('signal', 'N/A')})")
                        if "Breakthrough" in indicators:
                            bt = indicators["Breakthrough"]
                            bt_str = "    突破: "
                            if bt.get('breakthrough_60d'):
                                bt_str += "突破60日高点✅"
                            elif bt.get('breakthrough_20d'):
                                bt_str += "突破20日高点✅"
                            else:
                                bt_str += "未突破近期高点"
                            report.append(bt_str)
                        # 动量指标（在技术指标部分之前获取，以便后续使用）
                        momentum_5d = None
                        momentum_20d = None
                        mom_signal = None
                        if "Momentum" in indicators:
                            mom = indicators["Momentum"]
                            momentum_5d = mom.get('momentum_5d')
                            momentum_20d = mom.get('momentum_20d')
                            mom_signal = mom.get('signal', 'N/A')
                        
                        # 动量指标显示（在 timing indicators 部分）
                        if momentum_5d is not None and momentum_20d is not None:
                            report.append(f"    动量: 5日={momentum_5d:.2f}%, 20日={momentum_20d:.2f}% ({mom_signal or 'N/A'})")
                        
                        # 成交量（从 timing indicators 中获取）
                        if "Volume" in indicators:
                            vol = indicators["Volume"]
                            volume_ratio = vol.get('ratio')
                            if volume_ratio is not None:
                                report.append(f"    成交量: 量比={volume_ratio:.2f} ({vol.get('signal', 'N/A')})")
                    
                    # 技术指标（MACD、布林带等，使用 akshare 数据计算）
                    openbb_indicators = stock.get("openbb_indicators", {})
                    if openbb_indicators and "indicators" in openbb_indicators:
                        report.append(f"\n  📊 技术指标（MACD、布林带等）:")
                        tech_indicators = openbb_indicators["indicators"]
                        
                        # MACD
                        if "MACD" in tech_indicators:
                            macd = tech_indicators["MACD"]
                            macd_str = f"    MACD: {macd.get('macd', 0):.4f}, 信号线: {macd.get('signal', 0):.4f}"
                            if macd.get('macd_cross_signal'):
                                macd_str += " ✅MACD上穿信号线"
                            report.append(macd_str)
                        
                        # 布林带
                        if "BollingerBands" in tech_indicators:
                            bb = tech_indicators["BollingerBands"]
                            bb_str = f"    布林带: 上轨={bb.get('upper', 0):.2f}, 中轨={bb.get('middle', 0):.2f}, 下轨={bb.get('lower', 0):.2f}, 当前={bb.get('current_price', 0):.2f}"
                            if bb.get('signal') == "突破上轨":
                                bb_str += " ✅突破上轨"
                            report.append(bb_str)
                        
                        # 均线（SMA50/SMA200）
                        if "MA" in tech_indicators:
                            tech_ma = tech_indicators["MA"]
                            ma_str = f"    均线: SMA50={tech_ma.get('SMA50', 0):.2f}"
                            if tech_ma.get('SMA200'):
                                ma_str += f", SMA200={tech_ma.get('SMA200', 0):.2f}"
                            if tech_ma.get('ma_cross_signal'):
                                ma_str += " ✅均线交叉"
                            report.append(ma_str)
                        
                        # 交易信号
                        if openbb_indicators.get("signals"):
                            report.append(f"\n  🎯 交易信号:")
                            for signal in openbb_indicators["signals"]:
                                report.append(f"    {signal}")
                    else:
                        report.append(f"\n  技术指标: 数据获取失败")
            
            # OpenBB MCP 分析结果
            mcp_analysis = stock.get("mcp_analysis", {})
            if mcp_analysis and "error" not in mcp_analysis:
                report.append(f"\n  🤖 OpenBB MCP 分析:")
                
                # MCP 预测
                if mcp_analysis.get("prediction"):
                    pred = mcp_analysis["prediction"]
                    report.append(f"    价格预测:")
                    report.append(f"      当前价格: {pred.get('current_price', 0):.2f}")
                    report.append(f"      预测价格: {pred.get('predicted_price', 0):.2f}")
                    report.append(f"      预期涨跌幅: {pred.get('price_change_pct', 0):.2f}%")
                    report.append(f"      趋势: {pred.get('trend', 'N/A')}")
                    report.append(f"      置信度: {pred.get('confidence', 'N/A')}")
                
                # 估值数据
                if mcp_analysis.get("valuation"):
                    val = mcp_analysis["valuation"]
                    report.append(f"    估值指标:")
                    if val.get("pe_ratio"):
                        report.append(f"      市盈率(PE): {val.get('pe_ratio'):.2f}")
                    if val.get("pb_ratio"):
                        report.append(f"      市净率(PB): {val.get('pb_ratio'):.2f}")
                    if val.get("market_cap"):
                        report.append(f"      市值: {val.get('market_cap'):,.0f}")
                    if val.get("dividend_yield"):
                        report.append(f"      股息率: {val.get('dividend_yield'):.2f}%")
                
                # 财务指标
                if mcp_analysis.get("financial_metrics"):
                    metrics = mcp_analysis["financial_metrics"]
                    report.append(f"    财务指标:")
                    if metrics.get("revenue_growth") is not None:
                        report.append(f"      营收增长率: {metrics.get('revenue_growth'):.2f}%")
                    if metrics.get("net_income"):
                        report.append(f"      净利润: {metrics.get('net_income'):,.0f}")
                    if metrics.get("eps"):
                        report.append(f"      每股收益(EPS): {metrics.get('eps'):.2f}")
                    if metrics.get("roe"):
                        report.append(f"      净资产收益率(ROE): {metrics.get('roe'):.2f}%")
                
                # MCP 买入信号
                if mcp_analysis.get("buy_signal"):
                    signal = mcp_analysis["buy_signal"]
                    if signal.get("signal"):
                        report.append(f"    🎯 MCP 买入信号: ✅ {signal.get('strength', '中等')}")
                        if signal.get("reasons"):
                            for reason in signal.get("reasons", []):
                                report.append(f"      • {reason}")
                    else:
                        report.append(f"    🎯 MCP 买入信号: ❌ 无买入信号")
            
            # 如果时机分析有错误，显示错误信息（独立检查，不依赖 MCP 分析）
            if timing and "error" in timing:
                report.append(f"\n⏰ 买入时机分析:")
                report.append(f"  ⚠️ 分析失败: {timing.get('error', '未知错误')}")
            elif not timing or "timing" not in timing:
                report.append(f"\n⏰ 买入时机分析:")
                report.append(f"  ⚠️ 数据不完整，无法进行分析")
            
            # 价格信息
            fundamentals = stock.get("fundamentals", {})
            if fundamentals and "price_data" in fundamentals:
                price_data = fundamentals["price_data"]
                if price_data and price_data.get("current"):
                    report.append(f"\n💰 价格信息:")
                    current_price = price_data.get("current")
                    if current_price:
                        report.append(f"    当前价: {current_price:.2f}")
                    if price_data.get("high_52w"):
                        report.append(f"    52周最高: {price_data.get('high_52w', 0):.2f}")
                    if price_data.get("low_52w"):
                        report.append(f"    52周最低: {price_data.get('low_52w', 0):.2f}")
            
            report.append("")
        
        # 添加策略推荐和风险提示
        print("  📋 生成策略推荐...")
        report.append("="*60)
        report.append("5. 策略推荐（趋势/反转）")
        report.append("-"*60)
        try:
            report.append(self._format_strategy_recommendation_for_stocks(analysis.get("stocks", [])))
        except Exception as e:
            print(f"    ⚠️ 生成策略推荐失败: {str(e)[:100]}")
            report.append(f"策略推荐生成失败: {str(e)[:100]}")
        report.append("")
        
        print("  ⚠️ 生成风险提示...")
        report.append("6. 风险提示与触发点")
        report.append("-"*60)
        report.append(self._format_risk_warnings())
        report.append("")
        
        # 添加买入理由汇总（右侧交易策略筛选）
        print("  🎯 生成买入理由汇总...")
        report.append("="*60)
        report.append("7. 买入理由汇总（右侧交易策略 + OpenBB MCP 分析）")
        report.append("-"*60)
        try:
            buy_reasons = self._format_buy_reasons_summary(analysis.get("stocks", []))
            report.append(buy_reasons)
        except Exception as e:
            print(f"    ⚠️ 生成买入理由汇总失败: {str(e)[:100]}")
            report.append(f"买入理由汇总生成失败: {str(e)[:100]}")
        report.append("")
        
        report.append("="*60)
        report.append("报告结束")
        report.append("="*60)
        
        print("  ✅ 报告生成完成")
        return "\n".join(report)
    
    def _format_strategy_recommendation_for_stocks(self, stocks: List[Dict[str, Any]]) -> str:
        """
        基于股票分析结果生成策略推荐
        
        Args:
            stocks: 股票分析结果列表
        
        Returns:
            策略推荐文本
        """
        if not stocks:
            return "待分析（需要指定股票进行策略回测）"
        
        # 分析所有股票的时机评分，判断整体市场状态
        total_score = 0
        buy_count = 0
        watch_count = 0
        caution_count = 0
        
        # 收集买入建议股票的信息
        buy_stocks_info = []  # 存储买入股票的代码和关键因素
        
        for stock in stocks:
            timing = stock.get("timing", {})
            if timing and "timing" in timing:
                timing_info = timing["timing"]
                score = timing_info.get("score", 0)
                recommendation = timing_info.get("recommendation", "观望")
                
                total_score += score
                if recommendation == "买入":
                    buy_count += 1
                    symbol = stock.get("symbol", "N/A")
                    factors = timing_info.get("factors", [])
                    # 记录买入股票的代码和关键因素
                    buy_stocks_info.append({
                        "symbol": symbol,
                        "factors": factors,
                        "score": score
                    })
                elif recommendation == "观望":
                    watch_count += 1
                else:
                    caution_count += 1
        
        # 判断市场状态
        avg_score = total_score / len(stocks) if stocks else 0
        
        if avg_score >= 3:
            market_regime = "趋势市场"
            recommended_strategy = "趋势策略（MA交叉）"
            strategy_explanation = """
趋势策略分析：
- 当前市场呈现上升趋势特征
- 建议使用移动平均线（MA）交叉策略
- 当快线上穿慢线时产生买入信号
- 当快线下穿慢线时产生卖出信号
- 适合当前市场环境
"""
        elif avg_score <= -1:
            market_regime = "震荡市场"
            recommended_strategy = "反转策略（均值回归）"
            strategy_explanation = """
反转策略分析：
- 当前市场呈现震荡特征
- 建议使用均值回归（MR）策略
- 当价格偏离均值超过阈值时入场
- 当价格回归到均值附近时出场
- 适合当前市场环境
"""
        else:
            market_regime = "混合市场"
            recommended_strategy = "混合策略"
            strategy_explanation = """
混合策略分析：
- 当前市场状态不明确，建议采用混合策略
- 可以结合趋势和反转策略
- 根据个股具体情况选择合适策略
- 注意风险控制
"""
        
        result = f"市场状态: {market_regime}\n"
        result += f"推荐策略: {recommended_strategy}\n"
        result += f"\n股票分析统计:\n"
        result += f"  买入建议: {buy_count} 只"
        
        # 如果有买入建议的股票，显示每只股票的代码和对应的关键因素
        if buy_count > 0 and buy_stocks_info:
            for stock_info in buy_stocks_info:
                symbol = stock_info["symbol"]
                factors = stock_info["factors"]
                score = stock_info["score"]
                result += f"\n    {symbol} (评分: {score}):"
                if factors:
                    for factor in factors:
                        result += f"\n      - {factor}"
                else:
                    result += "\n      - 无关键因素"
        
        result += f"\n  观望建议: {watch_count} 只\n"
        result += f"  谨慎建议: {caution_count} 只\n"
        result += f"  平均评分: {avg_score:.2f}\n"
        result += strategy_explanation
        
        return result
    
    def _format_buy_reasons_summary(self, stocks: List[Dict[str, Any]]) -> str:
        """
        生成买入理由汇总（右侧交易策略筛选 + OpenBB MCP 分析）
        
        Args:
            stocks: 股票分析结果列表
        
        Returns:
            买入理由汇总文本
        """
        buy_stocks = []
        
        for stock in stocks:
            symbol = stock.get("symbol", "")
            profile = stock.get("profile", {})
            stock_name = profile.get("name", symbol) if isinstance(profile, dict) else symbol
            
            # 收集买入理由
            buy_reasons = []
            timing_score = 0
            
            # 1. 时机分析评分
            timing = stock.get("timing", {})
            if "timing" in timing:
                timing_info = timing["timing"]
                timing_score = timing_info.get("score", 0)
                recommendation = timing_info.get("recommendation", "")
                
                if recommendation == "买入" and timing_score >= 6:
                    buy_reasons.append(f"时机评分: {timing_score} (买入建议)")
                    
                    # 添加关键因素
                    factors = timing_info.get("factors", [])
                    for factor in factors:
                        if "✅" in factor or "强势" in factor or "突破" in factor:
                            buy_reasons.append(factor)
            
            # 2. OpenBB 技术指标信号
            openbb_indicators = stock.get("openbb_indicators", {})
            if openbb_indicators and "signals" in openbb_indicators:
                for signal in openbb_indicators["signals"]:
                    if "✅" in signal:
                        buy_reasons.append(f"OpenBB信号: {signal}")
            
            # 2.5. OpenBB MCP 分析信号
            mcp_analysis = stock.get("mcp_analysis", {})
            if mcp_analysis and "error" not in mcp_analysis:
                # MCP 买入信号
                if mcp_analysis.get("buy_signal") and mcp_analysis["buy_signal"].get("signal"):
                    signal = mcp_analysis["buy_signal"]
                    if signal.get("reasons"):
                        for reason in signal.get("reasons", []):
                            buy_reasons.append(f"✅ MCP信号: {reason}")
                
                # MCP 价格预测
                if mcp_analysis.get("prediction"):
                    pred = mcp_analysis["prediction"]
                    if pred.get("price_change_pct", 0) > 0:
                        buy_reasons.append(f"✅ MCP预测: 预期上涨 {pred.get('price_change_pct', 0):.2f}%")
                
                # MCP 估值指标
                if mcp_analysis.get("valuation"):
                    val = mcp_analysis["valuation"]
                    if val.get("pe_ratio") and val.get("pe_ratio") < 30:  # PE 较低可能被低估
                        buy_reasons.append(f"✅ MCP估值: PE={val.get('pe_ratio'):.2f} (可能被低估)")
            
            # 3. 右侧交易策略筛选条件
            # 条件1: 均线多头排列
            ma_bullish = False
            if "timing" in timing and "indicators" in timing:
                ma_data = timing["indicators"].get("MA", {})
                if ma_data.get("bullish_arrangement", False):
                    ma_bullish = True
                    buy_reasons.append("✅ 均线多头排列")
            
            # 条件2: 价格在均线之上
            price_above_ma = False
            if "timing" in timing and "indicators" in timing:
                ma_data = timing["indicators"].get("MA", {})
                if ma_data.get("price_above_ma", False):
                    price_above_ma = True
                    buy_reasons.append("✅ 价格位于均线之上")
            
            # 条件3: RSI强势（50-70区间）
            rsi_strong = False
            if "timing" in timing and "indicators" in timing:
                rsi_data = timing["indicators"].get("RSI", {})
                rsi_value = rsi_data.get("value")
                if rsi_value and 50 <= rsi_value <= 70:
                    rsi_strong = True
                    buy_reasons.append(f"✅ RSI处于强势区间 ({rsi_value:.2f})")
            
            # 条件4: 价格位置中高位（50%-85%）
            price_position_ok = False
            if "timing" in timing and "indicators" in timing:
                pos_data = timing["indicators"].get("PricePosition", {})
                position_percent = pos_data.get("position_percent", 0)
                if 50 <= position_percent <= 85:
                    price_position_ok = True
                    buy_reasons.append(f"✅ 价格处于中高位 ({position_percent:.1f}%)")
            
            # 条件5: 突破信号
            breakthrough = False
            if "timing" in timing and "indicators" in timing:
                bt_data = timing["indicators"].get("Breakthrough", {})
                if bt_data.get("breakthrough_60d", False) or bt_data.get("breakthrough_20d", False):
                    breakthrough = True
                    if bt_data.get("breakthrough_60d"):
                        buy_reasons.append("✅ 突破60日高点")
                    elif bt_data.get("breakthrough_20d"):
                        buy_reasons.append("✅ 突破20日高点")
            
            # 条件6: 动量强劲
            momentum_strong = False
            if "timing" in timing and "indicators" in timing:
                mom_data = timing["indicators"].get("Momentum", {})
                if mom_data.get("signal") == "强势":
                    momentum_strong = True
                    momentum_5d = mom_data.get("momentum_5d")
                    momentum_20d = mom_data.get("momentum_20d")
                    # 确保值不为 None
                    if momentum_5d is not None and momentum_20d is not None:
                        buy_reasons.append(f"✅ 动量强劲 (5日: {momentum_5d:.2f}%, 20日: {momentum_20d:.2f}%)")
                    else:
                        buy_reasons.append("✅ 动量强劲")
            
            # 条件7: 成交量放大
            volume_ok = False
            volume_ratio = 1.0  # 初始化默认值
            if "timing" in timing and "indicators" in timing:
                vol_data = timing["indicators"].get("Volume", {})
                volume_ratio = vol_data.get("ratio")
                if volume_ratio is None:
                    volume_ratio = 1.0
                if volume_ratio > 1.5:
                    volume_ok = True
                    buy_reasons.append(f"✅ 成交量放大 ({volume_ratio:.2f}倍)")
            
            # 右侧交易策略筛选：至少满足3个条件，且时机评分>=6
            right_side_conditions = sum([
                ma_bullish,
                price_above_ma,
                rsi_strong,
                price_position_ok,
                breakthrough,
                momentum_strong,
                volume_ok
            ])
            
            if right_side_conditions >= 3 and timing_score >= 6:
                buy_stocks.append({
                    "symbol": symbol,
                    "name": stock_name,
                    "reasons": buy_reasons,
                    "score": timing_score,
                    "conditions_met": right_side_conditions
                })
        
        # 格式化输出
        if not buy_stocks:
            return "暂无符合右侧交易策略的股票。\n\n右侧交易策略筛选条件：\n" \
                   "- 均线多头排列\n" \
                   "- 价格位于均线之上\n" \
                   "- RSI处于强势区间（50-70）\n" \
                   "- 价格处于中高位（50%-85%）\n" \
                   "- 突破近期高点\n" \
                   "- 动量强劲\n" \
                   "- 成交量放大\n" \
                   "- OpenBB MCP 买入信号（可选）\n" \
                   "- MCP 价格预测上涨（可选）\n" \
                   "- 时机评分 >= 6\n" \
                   "- 至少满足3个条件"
        
        result = f"共筛选出 {len(buy_stocks)} 只符合右侧交易策略的股票：\n\n"
        
        for i, stock in enumerate(buy_stocks, 1):
            result += f"{i}. {stock['symbol']} ({stock['name']})\n"
            result += f"   时机评分: {stock['score']}, 满足条件数: {stock['conditions_met']}/7\n"
            result += f"   买入理由:\n"
            for reason in stock['reasons']:
                result += f"     {reason}\n"
            result += "\n"
        
        return result
    
    def _format_risk_warnings(self) -> str:
        """
        格式化风险提示与触发点
        
        Returns:
            风险提示文本
        """
        return """风险提示：
1. 市场波动风险：注意市场环境变化，及时调整策略
2. 行业轮动风险：强势行业可能回调，关注行业轮动信号
3. 个股风险：关注基本面变化，定期审查持仓股票
4. 策略风险：不同市场环境适用不同策略，避免策略僵化
5. 流动性风险：注意市场流动性变化，避免在极端市场条件下操作

触发点：
- 市场状态改变时重新评估策略和持仓
- 行业表现反转时及时调整持仓结构
- 个股基本面恶化时及时止损，避免损失扩大
- 技术指标出现明显反转信号时考虑减仓
- 市场出现系统性风险时降低仓位，保护本金"""
    
    def _save_buy_recommendations(self, stocks: List[Dict[str, Any]]) -> None:
        """
        将符合右侧交易策略的买入股票保存到 Buy.txt 文件（追加模式）
        
        Args:
            stocks: 股票分析结果列表
        """
        if not stocks:
            return
        
        # 收集符合右侧交易策略的买入股票信息
        buy_stocks_info = []
        filtered_stocks = []  # 记录被过滤的股票及其原因
        
        try:
            for stock in stocks:
                try:
                    # 安全获取股票代码
                    symbol = str(stock.get("symbol", "")).strip()
                    if not symbol:
                        continue
                    
                    # 安全获取股票名称
                    profile = stock.get("profile", {})
                    if isinstance(profile, dict):
                        stock_name = str(profile.get("name", symbol)).strip()
                    else:
                        stock_name = str(symbol).strip()
                    
                    if not stock_name:
                        stock_name = symbol
                    
                    timing = stock.get("timing", {})
                    if not timing or "timing" not in timing:
                        continue
                    
                    timing_info = timing["timing"]
                    if not isinstance(timing_info, dict):
                        continue
                    
                    # 安全获取时机评分，确保是数字类型
                    timing_score = timing_info.get("score")
                    if timing_score is None:
                        timing_score = 0
                    try:
                        timing_score = float(timing_score)
                    except (ValueError, TypeError):
                        timing_score = 0
                    
                    # 右侧交易策略筛选条件
                    ma_bullish = False
                    price_above_ma = False
                    rsi_strong = False
                    price_position_ok = False
                    breakthrough = False
                    momentum_strong = False
                    volume_ok = False
                    volume_ratio = 1.0  # 初始化默认值
                    rsi_value = None
                    position_percent = None
                    bt_data = {}
                    mom_data = {}
                    vol_data = {}
                    
                    if "indicators" in timing and isinstance(timing["indicators"], dict):
                        indicators = timing["indicators"]
                        
                        # 检查各项条件
                        ma_data = indicators.get("MA", {})
                        if isinstance(ma_data, dict):
                            ma_bullish = bool(ma_data.get("bullish_arrangement", False))
                            price_above_ma = bool(ma_data.get("price_above_ma", False))
                        
                        rsi_data = indicators.get("RSI", {})
                        if isinstance(rsi_data, dict):
                            rsi_value = rsi_data.get("value")
                            # 安全比较：确保 rsi_value 是数字类型
                            if rsi_value is not None:
                                try:
                                    rsi_value = float(rsi_value)
                                    rsi_strong = 50 <= rsi_value <= 70
                                except (ValueError, TypeError):
                                    rsi_value = None
                                    rsi_strong = False
                            else:
                                rsi_strong = False
                        
                        pos_data = indicators.get("PricePosition", {})
                        if isinstance(pos_data, dict):
                            position_percent = pos_data.get("position_percent")
                            if position_percent is not None:
                                try:
                                    position_percent = float(position_percent)
                                    price_position_ok = 50 <= position_percent <= 85
                                except (ValueError, TypeError):
                                    position_percent = None
                                    price_position_ok = False
                            else:
                                price_position_ok = False
                        
                        bt_data = indicators.get("Breakthrough", {})
                        if isinstance(bt_data, dict):
                            breakthrough = bool(bt_data.get("breakthrough_60d", False)) or bool(bt_data.get("breakthrough_20d", False))
                        
                        mom_data = indicators.get("Momentum", {})
                        if isinstance(mom_data, dict):
                            momentum_strong = str(mom_data.get("signal", "")) == "强势"
                        
                        vol_data = indicators.get("Volume", {})
                        if isinstance(vol_data, dict):
                            volume_ratio = vol_data.get("ratio")
                            if volume_ratio is None:
                                volume_ratio = 1.0
                            else:
                                try:
                                    volume_ratio = float(volume_ratio)
                                except (ValueError, TypeError):
                                    volume_ratio = 1.0
                            volume_ok = volume_ratio > 1.5
                    
                    # 右侧交易策略筛选：至少满足3个条件，且时机评分>=6
                    # 确保所有值都是布尔类型，避免 None 值导致计算错误
                    right_side_conditions = sum([
                        bool(ma_bullish),
                        bool(price_above_ma),
                        bool(rsi_strong),
                        bool(price_position_ok),
                        bool(breakthrough),
                        bool(momentum_strong),
                        bool(volume_ok)
                    ])
                    
                    # 记录筛选信息（用于调试）
                    filter_reasons = []
                    if right_side_conditions < 3:
                        filter_reasons.append(f"右侧交易条件不足（{right_side_conditions}/7，需要>=3）")
                    if timing_score < 6:
                        filter_reasons.append(f"时机评分不足（{timing_score}，需要>=6）")
                    
                    # 只保存符合右侧交易策略的股票
                    if right_side_conditions >= 3 and timing_score >= 6:
                        # 收集买入理由
                        buy_reasons = []
                        if ma_bullish:
                            buy_reasons.append("均线多头排列")
                        if price_above_ma:
                            buy_reasons.append("价格位于均线之上")
                        if rsi_strong and rsi_value is not None:
                            try:
                                buy_reasons.append(f"RSI处于强势区间 ({rsi_value:.2f})")
                            except (ValueError, TypeError):
                                buy_reasons.append("RSI处于强势区间")
                        if price_position_ok and position_percent is not None:
                            try:
                                buy_reasons.append(f"价格处于中高位 ({position_percent:.1f}%)")
                            except (ValueError, TypeError):
                                buy_reasons.append("价格处于中高位")
                        if breakthrough:
                            if isinstance(bt_data, dict):
                                if bt_data.get("breakthrough_60d"):
                                    buy_reasons.append("突破60日高点")
                                elif bt_data.get("breakthrough_20d"):
                                    buy_reasons.append("突破20日高点")
                        if momentum_strong:
                            if isinstance(mom_data, dict):
                                momentum_5d = mom_data.get("momentum_5d")
                                momentum_20d = mom_data.get("momentum_20d")
                                if momentum_5d is not None and momentum_20d is not None:
                                    try:
                                        momentum_5d = float(momentum_5d)
                                        momentum_20d = float(momentum_20d)
                                        buy_reasons.append(f"动量强劲 (5日: {momentum_5d:.2f}%, 20日: {momentum_20d:.2f}%)")
                                    except (ValueError, TypeError):
                                        buy_reasons.append("动量强劲")
                                else:
                                    buy_reasons.append("动量强劲")
                            else:
                                buy_reasons.append("动量强劲")
                        if volume_ok:
                            # volume_ratio 已在上面初始化，确保不为 None
                            if volume_ratio is None:
                                volume_ratio = 1.0
                            try:
                                volume_ratio = float(volume_ratio)
                                buy_reasons.append(f"成交量放大 ({volume_ratio:.2f}倍)")
                            except (ValueError, TypeError):
                                buy_reasons.append("成交量放大")
                        
                        buy_stocks_info.append({
                            "symbol": symbol,
                            "name": stock_name,
                            "score": timing_score,
                            "reasons": buy_reasons,
                            "conditions_met": right_side_conditions
                        })
                    else:
                        # 记录被过滤的股票信息
                        filtered_stocks.append({
                            "symbol": symbol,
                            "name": stock_name,
                            "score": timing_score,
                            "conditions_met": right_side_conditions,
                            "filter_reasons": filter_reasons,
                            "details": {
                                "ma_bullish": ma_bullish,
                                "price_above_ma": price_above_ma,
                                "rsi_strong": rsi_strong,
                                "price_position_ok": price_position_ok,
                                "breakthrough": breakthrough,
                                "momentum_strong": momentum_strong,
                                "volume_ok": volume_ok
                            }
                        })
                except Exception as stock_error:
                    # 单只股票处理失败不影响其他股票
                    print(f"  ⚠️ 处理股票 {stock.get('symbol', 'UNKNOWN')} 时出错: {str(stock_error)[:100]}")
                    continue
        
        except Exception as e:
            print(f"  ⚠️ 收集买入建议时出错: {str(e)[:200]}")
            return
        
        # 输出调试信息
        if filtered_stocks:
            print(f"  📊 筛选统计: 共分析 {len(stocks)} 只股票")
            print(f"    符合条件: {len(buy_stocks_info)} 只")
            print(f"    被过滤: {len(filtered_stocks)} 只")
            # 显示前5只被过滤的股票信息
            for i, filtered in enumerate(filtered_stocks[:5], 1):
                print(f"      {i}. {filtered['symbol']} (评分: {filtered['score']}, 条件: {filtered['conditions_met']}/7)")
                for reason in filtered['filter_reasons']:
                    print(f"         - {reason}")
            if len(filtered_stocks) > 5:
                print(f"      ... 还有 {len(filtered_stocks) - 5} 只股票被过滤")
        
        # 保存到 Buy.txt 文件（追加模式）
        if buy_stocks_info:
            try:
                with open("Buy.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"买入股票记录 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"{'='*60}\n\n")
                    
                    for stock_info in buy_stocks_info:
                        try:
                            # 安全转换所有值为字符串
                            symbol_str = str(stock_info.get('symbol', 'N/A'))
                            name_str = str(stock_info.get('name', symbol_str))
                            score = stock_info.get('score', 0)
                            try:
                                score_str = str(int(score)) if isinstance(score, (int, float)) else str(score)
                            except (ValueError, TypeError):
                                score_str = "0"
                            
                            conditions_met = stock_info.get('conditions_met', 0)
                            try:
                                conditions_str = str(int(conditions_met)) if isinstance(conditions_met, (int, float)) else str(conditions_met)
                            except (ValueError, TypeError):
                                conditions_str = "0"
                            
                            f.write(f"股票代码: {symbol_str}\n")
                            f.write(f"股票名称: {name_str}\n")
                            f.write(f"时机评分: {score_str}\n")
                            f.write(f"满足条件数: {conditions_str}/7\n")
                            f.write(f"买入理由:\n")
                            
                            reasons = stock_info.get('reasons', [])
                            if isinstance(reasons, list):
                                for reason in reasons:
                                    reason_str = str(reason) if reason else ""
                                    if reason_str:
                                        f.write(f"  - {reason_str}\n")
                            f.write("\n")
                        except Exception as write_error:
                            # 单条记录写入失败不影响其他记录
                            print(f"  ⚠️ 写入股票 {stock_info.get('symbol', 'UNKNOWN')} 信息时出错: {str(write_error)[:100]}")
                            continue
                    
                    f.write(f"{'='*60}\n\n")
                
                print(f"  ✅ 已将 {len(buy_stocks_info)} 只符合右侧交易策略的股票追加到 Buy.txt")
            except IOError as io_error:
                print(f"  ⚠️ 文件写入失败（IO错误）: {str(io_error)[:200]}")
            except PermissionError as perm_error:
                print(f"  ⚠️ 文件写入失败（权限错误）: {str(perm_error)[:200]}")
            except Exception as e:
                print(f"  ⚠️ 保存买入建议失败: {str(e)[:200]}")
                import traceback
                print(f"  详细错误: {traceback.format_exc()[:500]}")
        else:
            # 如果没有符合严格条件的股票，尝试保存所有"买入"建议的股票
            print(f"  ⚠️ 没有股票完全符合右侧交易策略（需要评分>=6且条件>=3）")
            print(f"  📋 尝试保存所有'买入'建议的股票...")
            
            buy_recommendations = []
            for stock in stocks:
                try:
                    symbol = str(stock.get("symbol", "")).strip()
                    if not symbol:
                        continue
                    
                    profile = stock.get("profile", {})
                    if isinstance(profile, dict):
                        stock_name = str(profile.get("name", symbol)).strip()
                    else:
                        stock_name = str(symbol).strip()
                    
                    if not stock_name:
                        stock_name = symbol
                    
                    timing = stock.get("timing", {})
                    if not timing or "timing" not in timing:
                        continue
                    
                    timing_info = timing["timing"]
                    if not isinstance(timing_info, dict):
                        continue
                    
                    recommendation = timing_info.get("recommendation", "")
                    timing_score = timing_info.get("score", 0)
                    
                    try:
                        timing_score = float(timing_score)
                    except (ValueError, TypeError):
                        timing_score = 0
                    
                    # 如果建议是"买入"，即使不完全符合右侧交易策略也保存
                    if recommendation == "买入":
                        factors = timing_info.get("factors", [])
                        buy_recommendations.append({
                            "symbol": symbol,
                            "name": stock_name,
                            "score": timing_score,
                            "factors": factors
                        })
                except Exception:
                    continue
            
            # 保存所有"买入"建议的股票
            if buy_recommendations:
                try:
                    with open("Buy.txt", "a", encoding="utf-8") as f:
                        f.write(f"\n{'='*60}\n")
                        f.write(f"买入建议统计 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"{'='*60}\n")
                        f.write(f"买入建议: {len(buy_recommendations)} 只\n\n")
                        
                        for rec in buy_recommendations:
                            f.write(f"{rec['symbol']} (评分: {int(rec['score'])}):\n")
                            for factor in rec.get('factors', [])[:10]:  # 最多显示10个因素
                                f.write(f"  - {factor}\n")
                            f.write("\n")
                        
                        f.write(f"{'='*60}\n")
                    
                    print(f"  ✅ 已将 {len(buy_recommendations)} 只'买入'建议的股票追加到 Buy.txt")
                except IOError as io_error:
                    print(f"  ⚠️ 文件写入失败（IO错误）: {str(io_error)[:200]}")
                except PermissionError as perm_error:
                    print(f"  ⚠️ 文件写入失败（权限错误）: {str(perm_error)[:200]}")
                except Exception as e:
                    print(f"  ⚠️ 保存买入建议失败: {str(e)[:200]}")
                    import traceback
                    print(f"  详细错误: {traceback.format_exc()[:500]}")
            else:
                print(f"  ⚠️ 没有找到任何'买入'建议的股票")
    
    async def interactive_workflow(self):
        """
        交互式工作流
        允许用户输入股票代码或使用外部工具
        """
        print("\n" + "="*60)
        print("🎯 交互式市场分析系统")
        print("="*60)
        print("\n请选择分析模式:")
        print("1. 输入股票代码列表（手动输入）")
        print("2. 从文件读取股票代码")
        print("3. 使用 OpenBB 应用端获取股票列表（需要手动输入）")
        print("4. 运行完整市场分析（自动筛选）")
        print("5. 退出")
        
        choice = input("\n请选择 (1-5): ").strip()
        
        stock_symbols = []
        
        if choice == "1":
            # 手动输入
            print("\n请输入股票代码（用逗号或空格分隔，如: 600519,000001 或 600519 000001）:")
            input_str = input().strip()
            stock_symbols = [s.strip() for s in input_str.replace(",", " ").split() if s.strip()]
        
        elif choice == "2":
            # 从文件读取
            filename = input("\n请输入文件路径（每行一个股票代码）: ").strip()
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    stock_symbols = [line.strip() for line in f if line.strip()]
            except Exception as e:
                print(f"❌ 读取文件失败: {e}")
                return
        
        elif choice == "3":
            # 外部工具协作
            print("\n" + "="*60)
            print("📋 外部工具协作模式")
            print("="*60)
            print("\n请使用以下方式获取股票列表:")
            print("1. 使用 OpenBB 应用端筛选股票")
            print("2. 使用其他工具（如 Excel、网页筛选器等）")
            print("3. 手动输入从外部工具获取的股票代码")
            print("\n请输入股票代码（用逗号或空格分隔）:")
            input_str = input().strip()
            stock_symbols = [s.strip() for s in input_str.replace(",", " ").split() if s.strip()]
        
        elif choice == "4":
            # 完整市场分析（仅分析到强势行业，不筛选个股）
            print("\n运行完整市场分析（仅分析到强势行业）...")
            result = await self.analyzer.run_full_analysis(
                index_query="China",
                market_type="A股",
                skip_stock_screening=True  # 跳过个股筛选和报告生成
            )
            return result
        
        elif choice == "5":
            print("退出")
            return None
        
        else:
            print("❌ 无效选择")
            return None
        
        if not stock_symbols:
            print("❌ 未输入股票代码")
            return None
        
        # 分析自定义股票
        print(f"\n✅ 将分析 {len(stock_symbols)} 只股票: {', '.join(stock_symbols)}")
        analysis = await self.analyze_custom_stocks(stock_symbols, market_type="A股")
        
        # 生成报告
        report = self.format_custom_analysis_report(analysis)
        print("\n" + report)
        
        # 保存报告（纯数字日期格式，重复时加序号）
        filename = self._generate_report_filename("custom_stock_analysis")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n✅ 报告已保存到: {filename}")
        
        # 保存 JSON 数据（使用相同的文件名，但扩展名为.json）
        json_filename = filename.replace(".txt", ".json")
        try:
            # 自定义 JSON encoder 来处理 NaN 和 Infinity
            import math
            
            def clean_for_json(obj):
                """递归清理对象，将 NaN 和 Infinity 转换为 None"""
                if isinstance(obj, dict):
                    return {key: clean_for_json(value) for key, value in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [clean_for_json(item) for item in obj]
                elif isinstance(obj, float):
                    if math.isnan(obj) or math.isinf(obj):
                        return None
                    return obj
                elif hasattr(obj, '__dict__'):
                    # 处理对象
                    return clean_for_json(obj.__dict__)
                else:
                    return obj
            
            # 清理数据中的 NaN 和 Infinity
            cleaned_analysis = clean_for_json(analysis)
            
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(cleaned_analysis, f, ensure_ascii=False, indent=2)
            print(f"✅ 数据已保存到: {json_filename}")
        except Exception as json_error:
            print(f"⚠️ 保存 JSON 数据失败: {str(json_error)[:200]}")
            import traceback
            print(f"  详细错误: {traceback.format_exc()[:500]}")
        
        # 保存买入建议统计到 Buy.txt（追加模式）
        self._save_buy_recommendations(analysis.get("stocks", []))
        
        return analysis
    
    async def close(self):
        """关闭分析器"""
        await self.analyzer.close()


async def main():
    """主函数"""
    analyzer = InteractiveMarketAnalyzer(use_akshare=True)
    
    try:
        await analyzer.interactive_workflow()
    finally:
        await analyzer.close()


if __name__ == "__main__":
    asyncio.run(main())

