"""
交互式市场分析系统
支持用户输入股票代码、外部工具协作、时机判断等功能
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
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
                ma5 = close_prices.tail(5).mean()
                ma20 = close_prices.tail(20).mean()
                ma60 = close_prices.tail(60).mean() if len(close_prices) >= 60 else None
                
                analysis["indicators"]["MA"] = {
                    "MA5": float(ma5),
                    "MA20": float(ma20),
                    "MA60": float(ma60) if ma60 else None,
                    "trend": "上升" if ma5 > ma20 else "下降"
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
                
                analysis["indicators"]["RSI"] = {
                    "value": current_rsi,
                    "signal": "超买" if current_rsi and current_rsi > 70 else 
                             "超卖" if current_rsi and current_rsi < 30 else "正常"
                }
            
            # 3. 价格位置（相对于52周高低点）
            if "收盘" in hist_data.columns:
                close_prices = hist_data["收盘"].astype(float)
                high_52w = close_prices.max()
                low_52w = close_prices.min()
                current = close_prices.iloc[-1]
                position = (current - low_52w) / (high_52w - low_52w) * 100 if high_52w != low_52w else 50
                
                analysis["indicators"]["PricePosition"] = {
                    "high_52w": float(high_52w),
                    "low_52w": float(low_52w),
                    "current": float(current),
                    "position_percent": float(position),
                    "signal": "高位" if position > 80 else "低位" if position < 20 else "中位"
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
            
            # 综合时机判断
            timing_score = 0
            timing_factors = []
            
            # MA趋势
            if analysis["indicators"]["MA"]["trend"] == "上升":
                timing_score += 2
                timing_factors.append("✅ 均线呈上升趋势")
            else:
                timing_factors.append("⚠️ 均线呈下降趋势")
            
            # RSI信号
            rsi_signal = analysis["indicators"]["RSI"]["signal"]
            if rsi_signal == "超卖":
                timing_score += 2
                timing_factors.append("✅ RSI显示超卖，可能反弹")
            elif rsi_signal == "超买":
                timing_score -= 2
                timing_factors.append("⚠️ RSI显示超买，注意风险")
            
            # 价格位置
            price_signal = analysis["indicators"]["PricePosition"]["signal"]
            if price_signal == "低位":
                timing_score += 2
                timing_factors.append("✅ 价格处于52周低位")
            elif price_signal == "高位":
                timing_score -= 1
                timing_factors.append("⚠️ 价格处于52周高位")
            
            # 成交量
            volume_signal = analysis["indicators"]["Volume"]["signal"]
            if volume_signal == "放量":
                timing_score += 1
                timing_factors.append("✅ 成交量放大，资金关注")
            
            analysis["timing"] = {
                "score": timing_score,
                "recommendation": "买入" if timing_score >= 3 else "观望" if timing_score >= 0 else "谨慎",
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
            
            # 2. 基本面分析
            if self.akshare:
                print(f"  📈 获取基本面数据...")
                fundamentals = self.get_stock_fundamentals_akshare(symbol)
                stock_analysis["fundamentals"] = fundamentals
            
            # 3. 获取股票简介
            try:
                profile = await self.analyzer.get_stock_profile(
                    symbol,
                    provider="yfinance" if market_type == "A股" else "fmp",
                    market_type=market_type
                )
                stock_analysis["profile"] = profile
            except:
                pass
            
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
                
                # 技术指标
                indicators = timing.get("indicators", {})
                if indicators:
                    report.append(f"\n  技术指标:")
                    if "MA" in indicators:
                        ma = indicators["MA"]
                        report.append(f"    均线: MA5={ma.get('MA5', 0):.2f}, MA20={ma.get('MA20', 0):.2f}, 趋势={ma.get('trend', 'N/A')}")
                    if "RSI" in indicators:
                        rsi = indicators["RSI"]
                        report.append(f"    RSI: {rsi.get('value', 0):.2f} ({rsi.get('signal', 'N/A')})")
                    if "PricePosition" in indicators:
                        pos = indicators["PricePosition"]
                        report.append(f"    价格位置: {pos.get('position_percent', 0):.1f}% ({pos.get('signal', 'N/A')})")
            
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
        
        report.append("="*60)
        report.append("报告结束")
        report.append("="*60)
        
        return "\n".join(report)
    
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
            # 完整市场分析
            print("\n运行完整市场分析...")
            result = await self.analyzer.run_full_analysis(
                index_query="China",
                market_type="A股"
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

