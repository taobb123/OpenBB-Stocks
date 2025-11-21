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


class InteractiveMarketAnalyzer:
    """交互式市场分析器"""
    
    def __init__(self, mcp_url: str = "http://127.0.0.1:8002/mcp", use_akshare: bool = True):
        """
        初始化交互式分析器
        
        Args:
            mcp_url: MCP服务器地址
            use_akshare: 是否使用 akshare
        """
        self.analyzer = MarketStructureAnalyzer(mcp_url=mcp_url, use_akshare=use_akshare)
        self.akshare = self.analyzer.akshare if use_akshare and AKSHARE_AVAILABLE else None
    
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
    
    def get_stock_timing_analysis(self, symbol: str) -> Dict[str, Any]:
        """
        分析股票买入时机
        
        Args:
            symbol: 股票代码
        
        Returns:
            时机分析结果
        """
        if not self.akshare:
            return {"error": "AKShare 不可用"}
        
        try:
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
            
            # 计算技术指标
            analysis = {
                "symbol": symbol,
                "current_price": float(hist_data.iloc[-1]["收盘"]) if "收盘" in hist_data.columns else 0,
                "indicators": {}
            }
            
            # 1. 移动平均线
            if "收盘" in hist_data.columns:
                close_prices = hist_data["收盘"].astype(float)
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
            if "收盘" in hist_data.columns:
                close_prices = hist_data["收盘"].astype(float)
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
            if "收盘" in hist_data.columns:
                close_prices = hist_data["收盘"].astype(float)
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
            if "收盘" in hist_data.columns:
                close_prices = hist_data["收盘"].astype(float)
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
            if "收盘" in hist_data.columns:
                close_prices = hist_data["收盘"].astype(float)
                # 计算5日、20日价格变化率
                momentum_5d = ((close_prices.iloc[-1] - close_prices.iloc[-6]) / close_prices.iloc[-6] * 100) if len(close_prices) >= 6 else 0
                momentum_20d = ((close_prices.iloc[-1] - close_prices.iloc[-21]) / close_prices.iloc[-21] * 100) if len(close_prices) >= 21 else 0
                
                analysis["indicators"]["Momentum"] = {
                    "momentum_5d": float(momentum_5d),
                    "momentum_20d": float(momentum_20d),
                    "signal": "强势" if momentum_5d > 3 and momentum_20d > 5 else 
                             "弱势" if momentum_5d < -3 or momentum_20d < -5 else "正常"
                }
            
            # 4. 成交量分析
            if "成交量" in hist_data.columns:
                volumes = hist_data["成交量"].astype(float)
                avg_volume = volumes.tail(20).mean()
                current_volume = volumes.iloc[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                
                analysis["indicators"]["Volume"] = {
                    "current": float(current_volume),
                    "avg_20d": float(avg_volume),
                    "ratio": float(volume_ratio),
                    "signal": "放量" if volume_ratio > 1.5 else "缩量" if volume_ratio < 0.7 else "正常"
                }
            
            # 综合时机判断（右侧交易风格：追涨杀跌）
            timing_score = 0
            timing_factors = []
            
            # 1. 均线多头排列（右侧交易核心指标）
            ma_data = analysis["indicators"]["MA"]
            if ma_data.get("bullish_arrangement", False):
                timing_score += 3
                timing_factors.append("✅ 均线多头排列，趋势强劲")
            elif ma_data.get("trend") == "上升":
                timing_score += 1
                timing_factors.append("✅ 均线呈上升趋势")
            else:
                timing_score -= 2
                timing_factors.append("❌ 均线呈下降趋势，不适合右侧交易")
            
            # 2. 价格在均线之上
            if ma_data.get("price_above_ma", False):
                timing_score += 2
                timing_factors.append("✅ 价格位于均线之上，处于上升通道")
            else:
                timing_score -= 1
                timing_factors.append("⚠️ 价格位于均线之下，趋势偏弱")
            
            # 3. RSI信号（右侧交易偏好强势但不超买）
            rsi_signal = analysis["indicators"]["RSI"]["signal"]
            rsi_value = analysis["indicators"]["RSI"]["value"]
            if rsi_signal == "强势" and rsi_value and 50 <= rsi_value <= 70:
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
            price_signal = analysis["indicators"]["PricePosition"]["signal"]
            position_percent = analysis["indicators"]["PricePosition"]["position_percent"]
            if price_signal in ["中高位", "高位"] and 50 <= position_percent <= 85:
                timing_score += 2
                timing_factors.append("✅ 价格处于中高位，符合右侧交易")
            elif price_signal == "极高" and position_percent > 85:
                timing_score -= 1
                timing_factors.append("⚠️ 价格处于极高位置，追高风险较大")
            elif price_signal in ["低位", "中低位"]:
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
            
            # 7. 成交量（右侧交易需要放量确认）
            volume_signal = analysis["indicators"]["Volume"]["signal"]
            volume_ratio = analysis["indicators"]["Volume"]["ratio"]
            if volume_signal == "放量" and volume_ratio > 1.5:
                timing_score += 2
                timing_factors.append(f"✅ 成交量放大{volume_ratio:.2f}倍，资金积极介入")
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
    
    def get_stock_fundamentals_akshare(self, symbol: str) -> Dict[str, Any]:
        """
        使用 akshare 获取股票基本面数据
        
        Args:
            symbol: 股票代码
        
        Returns:
            基本面数据
        """
        if not self.akshare:
            return {"error": "AKShare 不可用"}
        
        try:
            # 获取基本信息
            info = self.akshare.get_stock_info(symbol)
            
            # 获取基本面数据
            fundamentals = self.akshare.get_stock_fundamentals(symbol)
            
            # 获取历史数据用于计算
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
        
        for i, symbol in enumerate(stock_symbols, 1):
            print(f"[{i}/{len(stock_symbols)}] 分析 {symbol}...")
            
            stock_analysis = {
                "symbol": symbol,
                "timing": {},
                "fundamentals": {},
                "profile": {}
            }
            
            # 1. 时机分析
            if self.akshare:
                print(f"  ⏰ 分析买入时机...")
                timing = self.get_stock_timing_analysis(symbol)
                stock_analysis["timing"] = timing
                
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
            
            # 2. 基本面分析
            if self.akshare:
                print(f"  📈 获取基本面数据...")
                fundamentals = self.get_stock_fundamentals_akshare(symbol)
                stock_analysis["fundamentals"] = fundamentals
            
            # 3. 获取股票简介（已忽略，跳过获取概念板块信息）
            # 注意：此步骤已禁用，不再获取股票简介和概念板块信息
            # try:
            #     profile = await self.analyzer.get_stock_profile(
            #         symbol,
            #         provider="yfinance" if market_type == "A股" else "fmp",
            #         market_type=market_type
            #     )
            #     stock_analysis["profile"] = profile
            # except:
            #     pass
            stock_analysis["profile"] = {}  # 设置为空字典，保持数据结构一致
            
            results["stocks"].append(stock_analysis)
            print()
        
        return results
    
    def format_custom_analysis_report(self, analysis: Dict[str, Any]) -> str:
        """
        格式化自定义股票分析报告
        
        Args:
            analysis: 分析结果
        
        Returns:
            格式化的报告文本
        """
        report = []
        report.append("="*60)
        report.append("自定义股票分析报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("="*60)
        report.append("")
        
        for stock in analysis.get("stocks", []):
            symbol = stock.get("symbol", "N/A")
            report.append(f"\n股票代码: {symbol}")
            report.append("-"*60)
            
            # 时机分析
            timing = stock.get("timing", {})
            if timing and "timing" in timing:
                timing_info = timing["timing"]
                report.append(f"\n⏰ 买入时机分析:")
                report.append(f"  综合评分: {timing_info.get('score', 0)}")
                report.append(f"  建议: {timing_info.get('recommendation', 'N/A')}")
                report.append(f"\n  关键因素:")
                for factor in timing_info.get("factors", []):
                    report.append(f"    {factor}")
                
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
                        report.append(f"    RSI: {rsi.get('value', 0):.2f} ({rsi.get('signal', 'N/A')})")
                    if "PricePosition" in indicators:
                        pos = indicators["PricePosition"]
                        report.append(f"    价格位置: {pos.get('position_percent', 0):.1f}% ({pos.get('signal', 'N/A')})")
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
                    if "Momentum" in indicators:
                        mom = indicators["Momentum"]
                        report.append(f"    动量: 5日={mom.get('momentum_5d', 0):.2f}%, 20日={mom.get('momentum_20d', 0):.2f}% ({mom.get('signal', 'N/A')})")
                    if "Volume" in indicators:
                        vol = indicators["Volume"]
                        report.append(f"    成交量: 量比={vol.get('ratio', 1):.2f} ({vol.get('signal', 'N/A')})")
            
            # 基本面
            fundamentals = stock.get("fundamentals", {})
            if fundamentals and "fundamentals" in fundamentals:
                fund_data = fundamentals["fundamentals"]
                report.append(f"\n📊 基本面数据:")
                for key, value in fund_data.items():
                    if value:
                        report.append(f"    {key}: {value}")
            
            # 价格信息
            if fundamentals and "price_data" in fundamentals:
                price_data = fundamentals["price_data"]
                if price_data.get("current"):
                    report.append(f"\n💰 价格信息:")
                    report.append(f"    当前价: {price_data.get('current', 0):.2f}")
                    if price_data.get("high_52w"):
                        report.append(f"    52周最高: {price_data.get('high_52w', 0):.2f}")
                    if price_data.get("low_52w"):
                        report.append(f"    52周最低: {price_data.get('low_52w', 0):.2f}")
            
            report.append("")
        
        # 添加策略推荐和风险提示
        report.append("="*60)
        report.append("5. 策略推荐（趋势/反转）")
        report.append("-"*60)
        report.append(self._format_strategy_recommendation_for_stocks(analysis.get("stocks", [])))
        report.append("")
        
        report.append("6. 风险提示与触发点")
        report.append("-"*60)
        report.append(self._format_risk_warnings())
        report.append("")
        
        report.append("="*60)
        report.append("报告结束")
        report.append("="*60)
        
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
        将买入建议的分析统计保存到 Buy.txt 文件（追加模式）
        
        Args:
            stocks: 股票分析结果列表
        """
        if not stocks:
            return
        
        # 收集买入建议股票的信息
        buy_stocks_info = []
        
        for stock in stocks:
            timing = stock.get("timing", {})
            if timing and "timing" in timing:
                timing_info = timing["timing"]
                recommendation = timing_info.get("recommendation", "观望")
                
                if recommendation == "买入":
                    symbol = stock.get("symbol", "N/A")
                    factors = timing_info.get("factors", [])
                    score = timing_info.get("score", 0)
                    buy_stocks_info.append({
                        "symbol": symbol,
                        "factors": factors,
                        "score": score
                    })
        
        # 如果没有买入建议，不保存
        if not buy_stocks_info:
            return
        
        # 格式化买入建议信息
        buy_info = []
        buy_info.append("="*60)
        buy_info.append(f"买入建议统计 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        buy_info.append("="*60)
        buy_info.append(f"买入建议: {len(buy_stocks_info)} 只\n")
        
        for stock_info in buy_stocks_info:
            symbol = stock_info["symbol"]
            factors = stock_info["factors"]
            score = stock_info["score"]
            buy_info.append(f"{symbol} (评分: {score}):")
            if factors:
                for factor in factors:
                    buy_info.append(f"  - {factor}")
            else:
                buy_info.append("  - 无关键因素")
            buy_info.append("")
        
        buy_info.append("="*60)
        buy_info.append("")
        
        # 追加保存到 Buy.txt 文件（保存在项目根目录）
        try:
            # 获取项目根目录（interactive_analysis.py 所在目录）
            project_root = os.path.dirname(os.path.abspath(__file__))
            buy_file_path = os.path.join(project_root, "Buy.txt")
            
            with open(buy_file_path, "a", encoding="utf-8") as f:
                f.write("\n".join(buy_info))
            print(f"✅ 买入建议已追加保存到: {buy_file_path}")
        except Exception as e:
            print(f"⚠️ 保存买入建议到 Buy.txt 时出错: {e}")
    
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
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print(f"✅ 数据已保存到: {json_filename}")
        
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

