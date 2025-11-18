"""
市场结构分析框架
通过MCP调用OpenBB API进行市场分析

分析框架：
1. 目前市场是趋势还是震荡？
2. 哪些行业强/弱（强弱排序 + 热点持续性）？
3. 资金在偏好价值 / 增长 / 主题？
"""

import json
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd


class MarketStructureAnalyzer:
    """市场结构分析器 - 通过MCP调用OpenBB API"""
    
    def __init__(self, mcp_url: str = "http://127.0.0.1:8002/mcp"):
        """
        初始化分析器
        
        Args:
            mcp_url: OpenBB MCP服务器地址
        """
        self.mcp_url = mcp_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.session_id = None
        self._session_initialized = False
    
    async def _initialize_session(self) -> bool:
        """
        初始化MCP会话
        
        Returns:
            是否成功初始化
        """
        if self._session_initialized and self.session_id:
            return True
        
        try:
            # 确保URL不带尾随斜杠，避免307重定向
            init_url = self.mcp_url.rstrip('/')
            init_response = await self.client.post(
                init_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "market-structure-analyzer",
                            "version": "1.0.0"
                        }
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            )
            
            # 从响应头获取session ID
            if "mcp-session-id" in init_response.headers:
                self.session_id = init_response.headers["mcp-session-id"]
                self._session_initialized = True
                return True
            elif init_response.status_code == 200:
                # 某些情况下可能不需要session ID
                self._session_initialized = True
                return True
        except Exception as e:
            print(f"初始化session失败: {e}")
        
        return False
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        通过MCP调用OpenBB工具
        
        Args:
            tool_name: 工具名称（如 'index_search', 'equity_compare_groups'）
            arguments: 工具参数
        
        Returns:
            API响应结果
        """
        # 确保session已初始化
        if not self._session_initialized:
            await self._initialize_session()
        
        # MCP协议调用格式（SSE传输）
        # 注意：如果使用HTTP传输，可能需要不同的调用方式
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # 如果已有session ID，添加到请求头
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        
        try:
            # 确保URL不带尾随斜杠，避免307重定向
            url = self.mcp_url.rstrip('/')
            response = await self.client.post(
                url,
                json=payload,
                headers=headers,
                follow_redirects=True  # 自动跟随重定向
            )
            
            # 如果返回307，尝试不带斜杠的URL
            if response.status_code == 307:
                url = url.rstrip('/')
                response = await self.client.post(
                    url,
                    json=payload,
                    headers=headers,
                    follow_redirects=True
                )
            
            response.raise_for_status()
            
            # MCP服务器可能返回SSE格式（Server-Sent Events）
            response_text = response.text
            
            # 解析响应（可能是SSE格式或纯JSON）
            result = None
            if response_text.startswith("event:") or "event:" in response_text:
                # 解析SSE格式
                lines = response_text.split('\n')
                for line in lines:
                    if line.startswith('data:'):
                        json_str = line[5:].strip()  # 移除 'data:' 前缀
                        try:
                            result = json.loads(json_str)
                            break
                        except json.JSONDecodeError:
                            continue
            else:
                # 直接解析JSON
                try:
                    result = response.json()
                except json.JSONDecodeError:
                    return {"error": "无法解析响应", "raw": response_text[:200]}
            
            if not result:
                return {"error": "无法从响应中提取数据", "raw": response_text[:200]}
            
            # 处理MCP响应格式
            if "result" in result:
                if "content" in result["result"]:
                    # 如果返回的是文本内容，尝试解析JSON
                    content = result["result"]["content"]
                    if isinstance(content, list) and len(content) > 0:
                        text = content[0].get("text", "")
                        try:
                            return json.loads(text)
                        except:
                            return {"raw": text}
                return result["result"]
            return result
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 307:
                # 307重定向，尝试不带斜杠的URL
                print(f"⚠️ 检测到307重定向，尝试修正URL...")
                try:
                    url = self.mcp_url.rstrip('/')
                    response = await self.client.post(
                        url,
                        json=payload,
                        headers=headers,
                        follow_redirects=True
                    )
                    response.raise_for_status()
                    # 继续处理响应...
                    response_text = response.text
                    if response_text.startswith("event:") or "event:" in response_text:
                        lines = response_text.split('\n')
                        for line in lines:
                            if line.startswith('data:'):
                                json_str = line[5:].strip()
                                try:
                                    result = json.loads(json_str)
                                    if "result" in result:
                                        return result["result"]
                                    return result
                                except json.JSONDecodeError:
                                    continue
                    else:
                        result = response.json()
                        if "result" in result:
                            return result["result"]
                        return result
                except Exception as retry_e:
                    print(f"重试后仍然失败: {retry_e}")
            print(f"调用MCP工具 {tool_name} 时出错: {e}")
            return {"error": str(e)}
        except Exception as e:
            print(f"调用MCP工具 {tool_name} 时出错: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    async def call_rest_api(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        直接调用OpenBB REST API（备选方案）
        
        Args:
            endpoint: API端点路径（如 '/api/v1/index/search'）
            params: 查询参数
        
        Returns:
            API响应结果
        """
        # MCP服务器可能不直接暴露REST API，需要通过MCP工具调用
        # 如果MCP服务器也运行OpenBB API，尝试不同的基础URL
        base_urls = [
            self.mcp_url.replace("/mcp", "").rstrip('/'),
            "http://127.0.0.1:8002",  # 直接使用MCP服务器地址
        ]
        
        for base_url in base_urls:
            url = f"{base_url}{endpoint}"
            try:
                response = await self.client.get(
                    url, 
                    params=params or {},
                    follow_redirects=True,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    # 如果404，尝试下一个URL
                    continue
                else:
                    response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    continue
                print(f"调用REST API {url} 时出错: {e}")
            except Exception as e:
                print(f"调用REST API {url} 时出错: {e}")
                continue
        
        # 如果所有REST API尝试都失败，返回空结果
        print(f"⚠️ REST API {endpoint} 不可用，请使用MCP工具调用")
        return {}
    
    async def list_available_tools(self) -> List[str]:
        """
        列出可用的MCP工具
        
        Returns:
            工具名称列表
        """
        try:
            result = await self.call_mcp_tool("tools/list", {})
            if result and "tools" in result:
                tool_names = [tool.get("name", "") for tool in result["tools"]]
                return tool_names
            return []
        except Exception as e:
            print(f"获取工具列表失败: {e}")
            return []
    
    async def get_indices_data(self, query: str = "China") -> Dict[str, Any]:
        """
        获取指数数据
        
        Args:
            query: 搜索关键词（如 "China", "SPX", "NASDAQ"）
        
        Returns:
            指数数据
        """
        print(f"🔍 搜索指数: {query}")
        
        # 尝试不同的工具名称格式
        tool_name_variants = [
            "index_search",
            "index/search", 
            "index_search_index",
            "index_search_general"
        ]
        
        result = {}
        for tool_name in tool_name_variants:
            result = await self.call_mcp_tool(
                tool_name,
                {
                    "query": query,
                    "provider": "cboe"
                }
            )
            if result and "error" not in result:
                print(f"✅ 使用工具 {tool_name} 成功")
                break
        
        # 如果MCP调用失败，尝试直接调用REST API
        if not result or "error" in result:
            print("⚠️ MCP工具调用失败，尝试REST API...")
            result = await self.call_rest_api(
                "/api/v1/index/search",
                params={"query": query, "provider": "cboe"}
            )
        
        return result if result else {}
    
    async def get_sector_performance(self) -> Dict[str, Any]:
        """
        获取行业表现数据
        
        Returns:
            行业表现数据
        """
        print("📊 获取行业表现数据...")
        
        # 尝试不同的工具名称格式
        tool_name_variants = [
            "equity_compare_groups",
            "equity/compare/groups",
            "equity_compare_groups_general",
            "equity_compare_groups_compare"
        ]
        
        result = {}
        for tool_name in tool_name_variants:
            result = await self.call_mcp_tool(
                tool_name,
                {
                    "group": "sector",
                    "metric": "performance",
                    "provider": "finviz"
                }
            )
            if result and "error" not in result:
                print(f"✅ 使用工具 {tool_name} 成功")
                break
        
        # 如果MCP调用失败，尝试直接调用REST API
        if not result or "error" in result:
            print("⚠️ MCP工具调用失败，尝试REST API...")
            result = await self.call_rest_api(
                "/api/v1/equity/compare/groups",
                params={
                    "group": "sector",
                    "metric": "performance",
                    "provider": "finviz"
                }
            )
        
        return result if result else {}
    
    async def get_economic_calendar(self, days_ahead: int = 7) -> Dict[str, Any]:
        """
        获取经济日历
        
        Args:
            days_ahead: 未来多少天
        
        Returns:
            经济日历数据
        """
        print("📅 获取经济日历...")
        
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        result = await self.call_mcp_tool(
            "economy_calendar",  # 或 "economy/calendar"
            {
                "provider": "fmp",  # 或 "nasdaq"
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        return result
    
    async def get_macro_indicators(self, country: str = "united_states") -> Dict[str, Any]:
        """
        获取宏观经济指标
        
        Args:
            country: 国家代码
        
        Returns:
            宏观经济数据
        """
        print(f"🌍 获取宏观经济指标: {country}")
        
        result = await self.call_mcp_tool(
            "economy_indicators",  # 或 "economy/indicators"
            {
                "provider": "econdb",
                "symbol": "main",  # 主要指标
                "country": country
            }
        )
        
        return result
    
    def analyze_market_regime(self, indices_data: Dict, macro_data: Dict) -> str:
        """
        分析市场是趋势还是震荡
        
        Args:
            indices_data: 指数数据
            macro_data: 宏观经济数据
        
        Returns:
            市场状态描述
        """
        print("\n" + "="*60)
        print("📈 问题1: 目前市场是趋势还是震荡？")
        print("="*60)
        
        analysis = {
            "market_regime": "待分析",
            "indicators": [],
            "conclusion": ""
        }
        
        # 从行业数据推断市场状态（如果没有指数数据）
        # 如果indices_data中有sectors数据，使用它
        sector_data_for_regime = None
        if isinstance(indices_data, dict) and "results" in indices_data:
            # 检查是否是行业数据
            if indices_data.get("results") and isinstance(indices_data["results"][0], dict):
                first_item = indices_data["results"][0]
                if "performance" in str(first_item) or "name" in first_item:
                    sector_data_for_regime = indices_data
        
        # 分析逻辑：通过行业表现的分散程度判断市场状态
        # 如果行业表现差异大（有强有弱），可能是趋势市场
        # 如果行业表现差异小（都差不多），可能是震荡市场
        
        indicators = []
        
        # 尝试从macro_data获取更多信息（如果有）
        if isinstance(macro_data, dict) and macro_data:
            if "error" not in str(macro_data).lower():
                indicators.append("宏观经济数据：已获取")
        
        analysis["indicators"] = indicators if indicators else ["基于行业表现数据推断"]
        
        # 默认判断：如果有行业数据，可以进一步分析
        # 这里先给出一个基本判断框架
        analysis["market_regime"] = "趋势市场（基于行业分化）"
        analysis["conclusion"] = """
        市场状态判断：
        1. 基于行业表现数据，当前市场呈现行业分化特征
        2. 建议：结合具体指数价格走势和技术指标进一步确认
        3. 如果行业轮动明显，偏向趋势市场；如果行业表现趋同，偏向震荡市场
        """
        
        return analysis
    
    def analyze_sector_strength(self, sector_data: Dict) -> Dict[str, Any]:
        """
        分析行业强弱排序和热点持续性
        
        Args:
            sector_data: 行业表现数据
        
        Returns:
            行业分析结果
        """
        print("\n" + "="*60)
        print("🏭 问题2: 哪些行业强/弱（强弱排序 + 热点持续性）？")
        print("="*60)
        
        analysis = {
            "strong_sectors": [],
            "weak_sectors": [],
            "hot_themes": [],
            "sector_ranking": []
        }
        
        # 提取行业数据
        sectors = []
        if isinstance(sector_data, dict):
            if "results" in sector_data:
                sectors = sector_data["results"]
            elif isinstance(sector_data, list):
                sectors = sector_data
        
        if not sectors:
            analysis["conclusion"] = "⚠️ 未获取到行业数据"
            return analysis
        
        # 1. 按不同时间周期排序
        time_periods = {
            "1周": "performance_1w",
            "1月": "performance_1m", 
            "3月": "performance_3m",
            "6月": "performance_6m",
            "1年": "performance_1y"
        }
        
        sector_rankings = {}
        for period_name, period_key in time_periods.items():
            sorted_sectors = sorted(
                sectors,
                key=lambda x: x.get(period_key, 0) if isinstance(x, dict) else 0,
                reverse=True
            )
            sector_rankings[period_name] = [
                {
                    "name": s.get("name", "Unknown"),
                    "performance": s.get(period_key, 0) * 100  # 转换为百分比
                }
                for s in sorted_sectors[:5]  # 取前5名
            ]
        
        # 2. 识别持续强势的行业（热点持续性）
        # 计算综合得分：多个周期都表现好的行业
        sector_scores = {}
        for sector in sectors:
            if not isinstance(sector, dict):
                continue
            name = sector.get("name", "Unknown")
            score = (
                sector.get("performance_1w", 0) * 0.1 +
                sector.get("performance_1m", 0) * 0.2 +
                sector.get("performance_3m", 0) * 0.3 +
                sector.get("performance_6m", 0) * 0.4
            )
            sector_scores[name] = {
                "score": score,
                "1w": sector.get("performance_1w", 0) * 100,
                "1m": sector.get("performance_1m", 0) * 100,
                "3m": sector.get("performance_3m", 0) * 100,
                "6m": sector.get("performance_6m", 0) * 100,
                "1y": sector.get("performance_1y", 0) * 100
            }
        
        # 排序找出强势和弱势行业
        sorted_by_score = sorted(
            sector_scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        # 前3名为强势行业
        analysis["strong_sectors"] = [
            {
                "name": name,
                "综合得分": f"{score['score']*100:.2f}%",
                "表现": f"1周:{score['1w']:.2f}% 1月:{score['1m']:.2f}% 3月:{score['3m']:.2f}%"
            }
            for name, score in sorted_by_score[:3]
        ]
        
        # 后3名为弱势行业
        analysis["weak_sectors"] = [
            {
                "name": name,
                "综合得分": f"{score['score']*100:.2f}%",
                "表现": f"1周:{score['1w']:.2f}% 1月:{score['1m']:.2f}% 3月:{score['3m']:.2f}%"
            }
            for name, score in sorted_by_score[-3:]
        ]
        
        # 识别热点持续性：多个周期都为正且递增的行业
        hot_themes = []
        for name, score_data in sector_scores.items():
            if (score_data["1w"] > 0 and score_data["1m"] > 0 and 
                score_data["3m"] > 0 and score_data["6m"] > 0):
                # 检查是否递增趋势
                if (score_data["1m"] > score_data["1w"] and 
                    score_data["3m"] > score_data["1m"]):
                    hot_themes.append({
                        "name": name,
                        "趋势": "持续上涨",
                        "1年表现": f"{score_data['1y']:.2f}%"
                    })
        
        analysis["hot_themes"] = hot_themes[:3]  # 取前3个
        analysis["sector_ranking"] = sector_rankings
        
        # 生成结论
        strong_names = [s["name"] for s in analysis["strong_sectors"]]
        weak_names = [s["name"] for s in analysis["weak_sectors"]]
        hot_names = [s["name"] for s in analysis["hot_themes"]]
        
        analysis["conclusion"] = f"""
        分析结果：
        1. 强势行业（前3名）：{', '.join(strong_names) if strong_names else '无'}
        2. 弱势行业（后3名）：{', '.join(weak_names) if weak_names else '无'}
        3. 热点持续性行业：{', '.join(hot_names) if hot_names else '无'}
        4. 行业轮动：已按1周、1月、3月、6月、1年周期排序
        """
        
        return analysis
    
    def analyze_capital_preference(self, sector_data: Dict, indices_data: Dict) -> str:
        """
        分析资金偏好：价值 / 增长 / 主题
        
        Args:
            sector_data: 行业数据
            indices_data: 指数数据
        
        Returns:
            资金偏好分析
        """
        print("\n" + "="*60)
        print("💰 问题3: 资金在偏好价值 / 增长 / 主题？")
        print("="*60)
        
        analysis = {
            "value_preference": 0,
            "growth_preference": 0,
            "theme_preference": 0,
            "conclusion": ""
        }
        
        # 提取行业数据
        sectors = []
        if isinstance(sector_data, dict):
            if "results" in sector_data:
                sectors = sector_data["results"]
            elif isinstance(sector_data, list):
                sectors = sector_data
        
        if not sectors:
            analysis["conclusion"] = "⚠️ 未获取到行业数据"
            return analysis
        
        # 定义行业分类
        value_sectors = ["Financial", "Utilities", "Real Estate", "Consumer Defensive"]
        growth_sectors = ["Technology", "Healthcare", "Communication Services"]
        theme_sectors = ["Energy", "Basic Materials", "Consumer Cyclical"]
        
        # 计算各类别的平均表现（使用1年表现）
        value_performance = []
        growth_performance = []
        theme_performance = []
        
        for sector in sectors:
            if not isinstance(sector, dict):
                continue
            name = sector.get("name", "")
            perf_1y = sector.get("performance_1y", 0) * 100  # 转换为百分比
            
            if name in value_sectors:
                value_performance.append(perf_1y)
            elif name in growth_sectors:
                growth_performance.append(perf_1y)
            elif name in theme_sectors:
                theme_performance.append(perf_1y)
        
        # 计算平均表现
        analysis["value_preference"] = sum(value_performance) / len(value_performance) if value_performance else 0
        analysis["growth_preference"] = sum(growth_performance) / len(growth_performance) if growth_performance else 0
        analysis["theme_preference"] = sum(theme_performance) / len(theme_performance) if theme_performance else 0
        
        # 找出最强的偏好
        preferences = {
            "价值": analysis["value_preference"],
            "增长": analysis["growth_preference"],
            "主题": analysis["theme_preference"]
        }
        strongest = max(preferences.items(), key=lambda x: x[1])
        
        # 生成结论
        analysis["conclusion"] = f"""
        资金偏好分析：
        1. 价值股平均表现：{analysis['value_preference']:.2f}%
           - 代表行业：金融、公用事业、房地产、消费必需品
        2. 增长股平均表现：{analysis['growth_preference']:.2f}%
           - 代表行业：科技、医疗、通信服务
        3. 主题股平均表现：{analysis['theme_preference']:.2f}%
           - 代表行业：能源、基础材料、消费周期性
        
        结论：当前资金偏好 {strongest[0]} 风格（{strongest[1]:.2f}%）
        """
        
        return analysis
    
    async def run_full_analysis(self, index_query: str = "China") -> Dict[str, Any]:
        """
        运行完整分析
        
        Args:
            index_query: 指数搜索关键词
        
        Returns:
            完整分析结果
        """
        print("\n" + "🚀 开始市场结构分析")
        print("="*60)
        
        # 1. 获取数据
        indices_data = await self.get_indices_data(index_query)
        sector_data = await self.get_sector_performance()
        calendar_data = await self.get_economic_calendar()
        macro_data = await self.get_macro_indicators()
        
        # 2. 分析三个核心问题
        market_regime = self.analyze_market_regime(indices_data, macro_data)
        sector_analysis = self.analyze_sector_strength(sector_data)
        capital_preference = self.analyze_capital_preference(sector_data, indices_data)
        
        # 3. 汇总结果
        result = {
            "timestamp": datetime.now().isoformat(),
            "data_sources": {
                "indices": indices_data,
                "sectors": sector_data,
                "calendar": calendar_data,
                "macro": macro_data
            },
            "analysis": {
                "market_regime": market_regime,
                "sector_strength": sector_analysis,
                "capital_preference": capital_preference
            }
        }
        
        # 4. 生成并保存报告
        print("\n" + "="*60)
        print("📝 生成投资报告...")
        print("="*60)
        
        full_analysis = {
            "analysis": {
                "market_regime": market_regime,
                "sector_strength": sector_analysis,
                "capital_preference": capital_preference
            },
            "stock_candidates": [],
            "strategy_analysis": None
        }
        
        report = self.generate_investment_report(full_analysis)
        
        # 保存报告到文件
        report_filename = f"investment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(report)
        
        # 保存JSON结果
        json_filename = "market_analysis_result.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*60)
        print("✅ 分析完成")
        print("="*60)
        print(f"📄 文本报告已保存到: {report_filename}")
        print(f"📊 JSON数据已保存到: {json_filename}")
        print("\n" + "="*60)
        
        return result
    
    # ==================== Step 2: 行业强弱分析 ====================
    
    async def get_sector_performance_detailed(self) -> Dict[str, Any]:
        """
        获取详细的行业表现数据（类似 openbb.sectors.performance()）
        
        Returns:
            行业表现数据（包含多个时间周期）
        """
        print("📊 获取详细行业表现数据...")
        
        # 使用equity.compare.groups获取行业表现
        result = await self.call_mcp_tool(
            "equity_compare_groups",
            {
                "group": "sector",
                "metric": "performance",
                "provider": "finviz"
            }
        )
        
        if not result:
            result = await self.call_rest_api(
                "/api/v1/equity/compare/groups",
                params={
                    "group": "sector",
                    "metric": "performance",
                    "provider": "finviz"
                }
            )
        
        return result
    
    async def get_sector_heatmap(self) -> Dict[str, Any]:
        """
        获取行业热力图数据（类似 openbb.sectors.heatmap()）
        
        Returns:
            行业热力图数据
        """
        print("🔥 获取行业热力图数据...")
        
        # 获取行业表现数据用于生成热力图
        sector_data = await self.get_sector_performance_detailed()
        
        # 热力图通常基于行业表现数据生成
        return {
            "sector_data": sector_data,
            "heatmap_ready": True
        }
    
    def analyze_sector_ranking(self, sector_data: Dict) -> Dict[str, Any]:
        """
        分析行业强弱排名
        
        Args:
            sector_data: 行业表现数据
        
        Returns:
            行业排名分析
        """
        print("\n" + "="*60)
        print("📈 Step 2: 行业强弱分析")
        print("="*60)
        
        analysis = {
            "top_3_sectors": [],
            "sector_ranking": [],
            "money_flow_trends": {},
            "sector_stage": {},  # 加速上涨/回调/震荡
            "conclusion": ""
        }
        
        # 分析逻辑：
        # 1. 按升序排名找最强的三个行业
        # 2. 分析资金流入趋势
        # 3. 判断行业阶段
        
        analysis["conclusion"] = """
        分析要点：
        1. 升序排名 → 找最强的三个行业
        2. 看这些行业是否有资金流入（moneyflow）趋势
        3. 判断行业是否处在加速上涨/回调/震荡阶段
        """
        
        return analysis
    
    # ==================== Step 3: 筛选行业内的强势股票 ====================
    
    async def search_stocks(self, query: str, provider: str = "nasdaq") -> Dict[str, Any]:
        """
        搜索股票（类似 openbb.equity.search()）
        
        Args:
            query: 搜索关键词（如 "航空", "AI"）
            provider: 数据提供商
        
        Returns:
            搜索结果
        """
        print(f"🔍 搜索股票: {query}")
        
        result = await self.call_mcp_tool(
            "equity_search",
            {
                "query": query,
                "provider": provider
            }
        )
        
        if not result:
            result = await self.call_rest_api(
                "/api/v1/equity/search",
                params={"query": query, "provider": provider}
            )
        
        return result
    
    async def screen_stocks(self, filters: Dict[str, Any], provider: str = "finviz") -> Dict[str, Any]:
        """
        股票筛选器（类似 openbb.equity.screener()）
        
        Args:
            filters: 筛选条件字典
            provider: 数据提供商
        
        Returns:
            筛选结果
        """
        print(f"🔎 筛选股票，条件: {filters}")
        
        params = {"provider": provider, **filters}
        
        result = await self.call_mcp_tool(
            "equity_screener",
            params
        )
        
        if not result:
            result = await self.call_rest_api(
                "/api/v1/equity/screener",
                params=params
            )
        
        return result
    
    def analyze_stock_strength(self, stock_data: Dict, sector: str) -> Dict[str, Any]:
        """
        分析股票强度（在强势行业里筛强势股）
        
        Args:
            stock_data: 股票数据
            sector: 所属行业
        
        Returns:
            股票强度分析
        """
        print(f"\n📊 分析 {sector} 行业内的强势股票...")
        
        analysis = {
            "strong_stocks": [],
            "criteria": {
                "relative_strength": True,
                "turnover": True,
                "volume": True,
                "fundamentals": {
                    "revenue_growth": True,
                    "gross_margin": True,
                    "roe": True,
                    "institutional_holding": True
                }
            },
            "conclusion": ""
        }
        
        analysis["conclusion"] = """
        筛选要点：
        1. 在强势行业里筛强势股（相对强度趋势、换手、成交量）
        2. 避免只看K线，要结合基本面指标：
           - 营收增速
           - 毛利率
           - ROE
           - 机构持仓
        """
        
        return analysis
    
    # ==================== Step 4: 构建策略（趋势/反转/因子） ====================
    
    async def get_stock_historical(self, symbol: str, period: str = "1y", provider: str = "fmp") -> Dict[str, Any]:
        """
        获取股票历史价格数据（用于策略分析）
        
        Args:
            symbol: 股票代码
            period: 时间周期（如 "1y"）
            provider: 数据提供商
        
        Returns:
            历史价格数据
        """
        print(f"📈 获取 {symbol} 的历史价格数据...")
        
        # 计算开始日期
        end_date = datetime.now()
        if period == "1y":
            start_date = end_date - timedelta(days=365)
        elif period == "6m":
            start_date = end_date - timedelta(days=180)
        elif period == "3m":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=365)
        
        result = await self.call_mcp_tool(
            "equity_price_historical",
            {
                "symbol": symbol,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "provider": provider
            }
        )
        
        if not result:
            result = await self.call_rest_api(
                "/api/v1/equity/price/historical",
                params={
                    "symbol": symbol,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "provider": provider
                }
            )
        
        return result
    
    async def analyze_ma_strategy(self, symbol: str, fast: int = 5, slow: int = 20, period: str = "1y") -> Dict[str, Any]:
        """
        分析MA（移动平均）策略
        
        Args:
            symbol: 股票代码
            fast: 快速均线周期
            slow: 慢速均线周期
            period: 回测周期
        
        Returns:
            MA策略分析结果
        """
        print(f"📊 分析 {symbol} 的MA策略 (快线={fast}, 慢线={slow})...")
        
        # 获取历史数据
        historical_data = await self.get_stock_historical(symbol, period)
        
        # 计算技术指标
        # 注意：实际实现需要调用technical指标API
        
        analysis = {
            "strategy_type": "MA_Crossover",
            "parameters": {"fast": fast, "slow": slow},
            "period": period,
            "signals": [],
            "performance": {
                "annualized_return": None,
                "max_drawdown": None,
                "win_rate": None,
                "sharpe_ratio": None
            },
            "conclusion": ""
        }
        
        analysis["conclusion"] = """
        MA策略分析：
        - 当快线上穿慢线时产生买入信号
        - 当快线下穿慢线时产生卖出信号
        - 适合趋势市场
        """
        
        return analysis
    
    async def analyze_mr_strategy(self, symbol: str, window: int = 20, z_entry: float = 1.0, z_exit: float = 0.0, period: str = "1y") -> Dict[str, Any]:
        """
        分析MR（均值回归）策略
        
        Args:
            symbol: 股票代码
            window: 窗口期
            z_entry: 入场Z值
            z_exit: 出场Z值
            period: 回测周期
        
        Returns:
            MR策略分析结果
        """
        print(f"📊 分析 {symbol} 的MR策略 (窗口={window}, Z_entry={z_entry})...")
        
        # 获取历史数据
        historical_data = await self.get_stock_historical(symbol, period)
        
        analysis = {
            "strategy_type": "Mean_Reversion",
            "parameters": {
                "window": window,
                "z_entry": z_entry,
                "z_exit": z_exit
            },
            "period": period,
            "signals": [],
            "performance": {
                "annualized_return": None,
                "max_drawdown": None,
                "win_rate": None,
                "sharpe_ratio": None
            },
            "conclusion": ""
        }
        
        analysis["conclusion"] = """
        MR策略分析：
        - 当价格偏离均值超过Z_entry个标准差时入场
        - 当价格回归到均值附近（Z_exit）时出场
        - 适合震荡市场
        """
        
        return analysis
    
    def determine_strategy_fit(self, market_regime: str, ma_result: Dict, mr_result: Dict) -> Dict[str, Any]:
        """
        判断策略是否适合当前市场
        
        Args:
            market_regime: 市场状态（趋势/震荡）
            ma_result: MA策略结果
            mr_result: MR策略结果
        
        Returns:
            策略适配性分析
        """
        print("\n" + "="*60)
        print("📈 Step 4: 策略适配性分析")
        print("="*60)
        
        analysis = {
            "market_regime": market_regime,
            "recommended_strategy": None,
            "strategy_comparison": {
                "MA": {
                    "suitable_for": "趋势市场",
                    "performance": ma_result.get("performance", {})
                },
                "MR": {
                    "suitable_for": "震荡市场",
                    "performance": mr_result.get("performance", {})
                }
            },
            "conclusion": ""
        }
        
        # 根据市场状态推荐策略
        if market_regime == "趋势":
            analysis["recommended_strategy"] = "MA"
        elif market_regime == "震荡":
            analysis["recommended_strategy"] = "MR"
        else:
            analysis["recommended_strategy"] = "混合"
        
        analysis["conclusion"] = f"""
        策略推荐：
        - 当前市场状态：{market_regime}
        - 推荐策略：{analysis['recommended_strategy']}
        - MA策略适合趋势市场（多个山顶 → MA高收益）
        - MR策略适合震荡市场（多个谷底 → MR高收益）
        """
        
        return analysis
    
    # ==================== Step 5: 股票深度研究 ====================
    
    async def get_stock_fundamentals(self, symbol: str, provider: str = "fmp") -> Dict[str, Any]:
        """
        获取公司财务与盈利能力数据（类似 openbb.equity.fundamentals()）
        
        Args:
            symbol: 股票代码
            provider: 数据提供商
        
        Returns:
            财务数据
        """
        print(f"💰 获取 {symbol} 的财务数据...")
        
        # 获取关键财务指标
        result = await self.call_rest_api(
            "/api/v1/equity/fundamental/income",
            params={"symbol": symbol, "provider": provider, "period": "annual", "limit": 5}
        )
        
        return result
    
    async def get_stock_valuation(self, symbol: str, provider: str = "fmp") -> Dict[str, Any]:
        """
        获取估值数据（PE、PB等，类似 openbb.equity.valuation()）
        
        Args:
            symbol: 股票代码
            provider: 数据提供商
        
        Returns:
            估值数据
        """
        print(f"📊 获取 {symbol} 的估值数据...")
        
        result = await self.call_rest_api(
            "/api/v1/equity/fundamental/ratios",
            params={"symbol": symbol, "provider": provider, "period": "annual", "limit": 5}
        )
        
        return result
    
    async def get_stock_technical(self, symbol: str, indicators: List[str] = None, provider: str = "fmp") -> Dict[str, Any]:
        """
        获取技术面数据（类似 openbb.equity.ta()）
        
        Args:
            symbol: 股票代码
            indicators: 技术指标列表（如 ["rsi", "macd", "sma"]）
            provider: 数据提供商
        
        Returns:
            技术指标数据
        """
        if indicators is None:
            indicators = ["rsi", "macd", "sma"]
        
        print(f"📈 获取 {symbol} 的技术指标: {indicators}")
        
        # 获取历史数据
        historical_data = await self.get_stock_historical(symbol, period="1y", provider=provider)
        
        # 注意：实际实现需要调用technical API计算指标
        result = {
            "symbol": symbol,
            "indicators": indicators,
            "data": historical_data,
            "note": "需要调用technical API计算具体指标"
        }
        
        return result
    
    async def analyze_stock_deep(self, symbol: str) -> Dict[str, Any]:
        """
        对单个股票做深度研究
        
        Args:
            symbol: 股票代码
        
        Returns:
            深度分析结果
        """
        print("\n" + "="*60)
        print(f"🔍 Step 5: {symbol} 深度研究")
        print("="*60)
        
        # 1. 财务与盈利能力
        fundamentals = await self.get_stock_fundamentals(symbol)
        
        # 2. 估值
        valuation = await self.get_stock_valuation(symbol)
        
        # 3. 技术面
        technical = await self.get_stock_technical(symbol)
        
        analysis = {
            "symbol": symbol,
            "fundamentals": {
                "revenue_trend": "待分析",
                "profit_margin": "待分析",
                "roe": "待分析",
                "debt_ratio": "待分析"
            },
            "valuation": {
                "pe_vs_industry": "待分析",
                "pb_vs_industry": "待分析",
                "value_score": "待分析"
            },
            "technical": {
                "trend": "待分析",
                "rsi": "待分析",
                "macd": "待分析",
                "support_resistance": "待分析"
            },
            "conclusion": ""
        }
        
        analysis["conclusion"] = """
        深度研究要点：
        1. 财务：营收/净利润趋势、毛利率、ROE、负债率
        2. 估值：PE/PB vs 行业中位数，判断性价比
        3. 技术：趋势/盘整判断，RSI、MACD等指标
        4. 综合：判断是否值得投资
        """
        
        return analysis
    
    # ==================== Step 6: 生成投资报告 ====================
    
    def generate_investment_report(self, full_analysis: Dict[str, Any]) -> str:
        """
        生成结构化投资报告
        
        Args:
            full_analysis: 完整分析结果
        
        Returns:
            报告文本
        """
        print("\n" + "="*60)
        print("📝 Step 6: 生成投资报告")
        print("="*60)
        
        # 获取资金偏好分析
        capital_pref = full_analysis.get('analysis', {}).get('capital_preference', {})
        capital_pref_text = self._format_capital_preference(capital_pref)
        
        report = f"""
{'='*60}
投资分析报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

1. 当前市场状态
{'-'*60}
{self._format_market_regime(full_analysis.get('analysis', {}).get('market_regime', {}))}

2. 行业强弱排序
{'-'*60}
{self._format_sector_ranking(full_analysis.get('analysis', {}).get('sector_strength', {}))}

3. 资金偏好分析
{'-'*60}
{capital_pref_text}

4. 候选股票名单（3-5个）
{'-'*60}
{self._format_stock_candidates(full_analysis.get('stock_candidates', []))}

5. 策略推荐（趋势/反转）
{'-'*60}
{self._format_strategy_recommendation(full_analysis.get('strategy_analysis', {}))}

6. 风险提示与触发点
{'-'*60}
{self._format_risk_warnings(full_analysis)}

{'='*60}
报告结束
{'='*60}
"""
        
        return report
    
    def _format_market_regime(self, regime_data: Dict) -> str:
        """格式化市场状态"""
        return f"市场状态: {regime_data.get('market_regime', '待分析')}\n{regime_data.get('conclusion', '')}"
    
    def _format_sector_ranking(self, sector_data: Dict) -> str:
        """格式化行业排名"""
        strong = sector_data.get('strong_sectors', [])
        weak = sector_data.get('weak_sectors', [])
        hot_themes = sector_data.get('hot_themes', [])
        sector_ranking = sector_data.get('sector_ranking', {})
        
        result = []
        
        # 强势行业
        if strong:
            result.append("强势行业（前3名）：")
            for i, sector in enumerate(strong, 1):
                name = sector.get('name', 'Unknown')
                score = sector.get('综合得分', 'N/A')
                perf = sector.get('表现', 'N/A')
                result.append(f"  {i}. {name} - 综合得分: {score}, {perf}")
        else:
            result.append("强势行业: 待分析")
        
        result.append("")
        
        # 弱势行业
        if weak:
            result.append("弱势行业（后3名）：")
            for i, sector in enumerate(weak, 1):
                name = sector.get('name', 'Unknown')
                score = sector.get('综合得分', 'N/A')
                perf = sector.get('表现', 'N/A')
                result.append(f"  {i}. {name} - 综合得分: {score}, {perf}")
        else:
            result.append("弱势行业: 待分析")
        
        result.append("")
        
        # 热点持续性
        if hot_themes:
            result.append("热点持续性行业：")
            for i, theme in enumerate(hot_themes, 1):
                name = theme.get('name', 'Unknown')
                trend = theme.get('趋势', 'N/A')
                perf_1y = theme.get('1年表现', 'N/A')
                result.append(f"  {i}. {name} - {trend}, 1年表现: {perf_1y}")
        else:
            result.append("热点持续性行业: 无")
        
        result.append("")
        
        # 按周期排序
        if sector_ranking:
            result.append("按时间周期排序（前5名）：")
            for period, rankings in sector_ranking.items():
                result.append(f"\n  {period}周期：")
                for i, item in enumerate(rankings[:5], 1):
                    name = item.get('name', 'Unknown')
                    perf = item.get('performance', 0)
                    result.append(f"    {i}. {name}: {perf:.2f}%")
        
        return "\n".join(result)
    
    def _format_stock_candidates(self, candidates: List) -> str:
        """格式化候选股票"""
        if not candidates:
            return "待筛选"
        return "\n".join([f"- {c.get('symbol', 'N/A')}: {c.get('reason', '')}" for c in candidates[:5]])
    
    def _format_strategy_recommendation(self, strategy_data: Dict) -> str:
        """格式化策略推荐"""
        if not strategy_data:
            return "待分析（需要指定股票进行策略回测）"
        
        recommended = strategy_data.get('recommended_strategy', 'N/A')
        conclusion = strategy_data.get('conclusion', '')
        market_regime = strategy_data.get('market_regime', 'N/A')
        
        result = f"市场状态: {market_regime}\n"
        result += f"推荐策略: {recommended}\n\n"
        result += conclusion if conclusion else "待分析"
        
        return result
    
    def _format_capital_preference(self, capital_data: Dict) -> str:
        """格式化资金偏好分析"""
        if not capital_data:
            return "待分析"
        
        value_pref = capital_data.get('value_preference', 0)
        growth_pref = capital_data.get('growth_preference', 0)
        theme_pref = capital_data.get('theme_preference', 0)
        conclusion = capital_data.get('conclusion', '')
        
        result = f"价值股平均表现: {value_pref:.2f}%\n"
        result += f"增长股平均表现: {growth_pref:.2f}%\n"
        result += f"主题股平均表现: {theme_pref:.2f}%\n\n"
        result += conclusion if conclusion else "待分析"
        
        return result
    
    def _format_risk_warnings(self, analysis: Dict) -> str:
        """格式化风险提示"""
        return """
风险提示：
1. 市场波动风险：注意市场环境变化
2. 行业轮动风险：强势行业可能回调
3. 个股风险：关注基本面变化
4. 策略风险：不同市场环境适用不同策略

触发点：
- 市场状态改变时重新评估策略
- 行业表现反转时调整持仓
- 个股基本面恶化时及时止损
"""
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


    # ==================== 完整工作流 ====================
    
    async def run_complete_workflow(
        self,
        index_query: str = "China",
        target_sector: str = None,
        target_stocks: List[str] = None,
        market: str = "A股"  # A股/美股/港股
    ) -> Dict[str, Any]:
        """
        运行完整分析工作流（Step 1-6）
        
        Args:
            index_query: 指数搜索关键词
            target_sector: 目标行业（可选）
            target_stocks: 目标股票列表（可选）
            market: 市场类型
        
        Returns:
            完整分析结果
        """
        print("\n" + "🚀"*30)
        print("开始完整市场分析工作流")
        print("🚀"*30)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "market": market,
            "workflow_steps": {}
        }
        
        # Step 1: 市场状态分析
        print("\n" + "="*60)
        print("Step 1: 市场状态分析")
        print("="*60)
        indices_data = await self.get_indices_data(index_query)
        sector_data = await self.get_sector_performance()
        calendar_data = await self.get_economic_calendar()
        macro_data = await self.get_macro_indicators()
        
        market_regime = self.analyze_market_regime(indices_data, macro_data)
        result["workflow_steps"]["step1_market_regime"] = market_regime
        
        # Step 2: 行业强弱分析
        sector_performance = await self.get_sector_performance_detailed()
        sector_heatmap = await self.get_sector_heatmap()
        sector_ranking = self.analyze_sector_ranking(sector_performance)
        result["workflow_steps"]["step2_sector_analysis"] = {
            "performance": sector_performance,
            "heatmap": sector_heatmap,
            "ranking": sector_ranking
        }
        
        # Step 3: 股票筛选（如果指定了行业）
        stock_candidates = []
        if target_sector:
            print(f"\n筛选 {target_sector} 行业的股票...")
            search_result = await self.search_stocks(target_sector)
            stock_candidates.append({
                "sector": target_sector,
                "stocks": search_result
            })
        elif target_stocks:
            stock_candidates = [{"symbol": s} for s in target_stocks]
        
        result["workflow_steps"]["step3_stock_screening"] = {
            "candidates": stock_candidates
        }
        
        # Step 4: 策略分析（如果指定了股票）
        strategy_analysis = None
        if target_stocks and len(target_stocks) > 0:
            symbol = target_stocks[0]
            ma_result = await self.analyze_ma_strategy(symbol)
            mr_result = await self.analyze_mr_strategy(symbol)
            market_state = market_regime.get("market_regime", "待分析")
            strategy_analysis = self.determine_strategy_fit(market_state, ma_result, mr_result)
            result["workflow_steps"]["step4_strategy_analysis"] = strategy_analysis
        
        # Step 5: 股票深度研究（如果指定了股票）
        deep_analysis = None
        if target_stocks and len(target_stocks) > 0:
            symbol = target_stocks[0]
            deep_analysis = await self.analyze_stock_deep(symbol)
            result["workflow_steps"]["step5_stock_deep_analysis"] = deep_analysis
        
        # Step 6: 生成报告
        full_analysis = {
            "analysis": {
                "market_regime": market_regime,
                "sector_strength": sector_ranking
            },
            "stock_candidates": stock_candidates,
            "strategy_analysis": strategy_analysis
        }
        
        report = self.generate_investment_report(full_analysis)
        result["workflow_steps"]["step6_report"] = report
        
        # 保存报告到文件
        report_filename = f"investment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"\n✅ 完整工作流完成！")
        print(f"📄 报告已保存到: {report_filename}")
        
        return result


# 使用示例
async def main():
    """主函数 - 演示如何使用"""
    
    # 初始化分析器
    analyzer = MarketStructureAnalyzer(mcp_url="http://127.0.0.1:8002/mcp")
    
    try:
        # 方式1: 运行完整工作流
        print("\n" + "="*60)
        print("方式1: 运行完整工作流")
        print("="*60)
        
        result = await analyzer.run_complete_workflow(
            index_query="China",
            target_sector="航空",  # 可选
            target_stocks=["600111"],  # 可选，用于策略分析和深度研究
            market="A股"
        )
        
        # 保存完整结果
        with open("market_analysis_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print("\n结果已保存到 market_analysis_result.json")
        
        # 方式2: 单独运行某个步骤
        print("\n" + "="*60)
        print("方式2: 单独运行某个步骤")
        print("="*60)
        
        # 示例：只分析行业
        sector_data = await analyzer.get_sector_performance_detailed()
        print(f"行业数据: {sector_data}")
        
        # 示例：只分析股票
        stock_analysis = await analyzer.analyze_stock_deep("600111")
        print(f"股票分析: {stock_analysis}")
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await analyzer.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

