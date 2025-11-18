"""
MCP 工具直接调用助手
用于直接调用 MCP 工具获取数据，然后与程序协作生成完整报告
"""

import asyncio
import httpx
import json
from typing import Dict, List, Any, Optional


class MCPToolHelper:
    """MCP 工具调用助手"""
    
    def __init__(self, mcp_url: str = "http://127.0.0.1:8002/mcp"):
        """
        初始化 MCP 工具助手
        
        Args:
            mcp_url: MCP 服务器地址
        """
        self.mcp_url = mcp_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.session_id = None
        self._session_initialized = False
    
    async def initialize_session(self) -> bool:
        """初始化 MCP 会话"""
        if self._session_initialized:
            return True
        
        try:
            response = await self.client.post(
                self.mcp_url.rstrip('/'),
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "mcp-tool-helper",
                            "version": "1.0.0"
                        }
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                follow_redirects=True
            )
            
            if "mcp-session-id" in response.headers:
                self.session_id = response.headers["mcp-session-id"]
                self._session_initialized = True
                print(f"✅ MCP 会话已初始化: {self.session_id[:20]}...")
                return True
            else:
                print("⚠️ 未获取到 session ID，但继续尝试...")
                self._session_initialized = True
                return True
        except Exception as e:
            print(f"⚠️ 初始化会话失败: {e}")
            return False
    
    async def call_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称（如 "equity_screener"）
            arguments: 工具参数
        
        Returns:
            工具返回结果
        """
        # 确保会话已初始化
        if not self._session_initialized:
            await self.initialize_session()
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            url = self.mcp_url.rstrip('/')
            response = await self.client.post(
                url,
                json=payload,
                headers=headers,
                follow_redirects=True
            )
            
            response.raise_for_status()
            
            # 解析响应（可能是 SSE 格式或纯 JSON）
            response_text = response.text
            result = None
            
            if "event:" in response_text or response_text.startswith("event:"):
                # 解析 SSE 格式
                lines = response_text.split('\n')
                for line in lines:
                    if line.startswith('data:'):
                        json_str = line[5:].strip()
                        try:
                            result = json.loads(json_str)
                            break
                        except json.JSONDecodeError:
                            continue
            else:
                # 直接解析 JSON
                try:
                    result = response.json()
                except json.JSONDecodeError:
                    return {"error": "无法解析响应", "raw": response_text[:200]}
            
            if not result:
                return {"error": "无法从响应中提取数据", "raw": response_text[:200]}
            
            # 处理 MCP 响应格式
            if "result" in result:
                if "content" in result["result"]:
                    # 如果返回的是文本内容，尝试解析 JSON
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
            error_detail = ""
            try:
                if hasattr(e, 'response') and e.response:
                    error_detail = e.response.text[:200]
            except:
                pass
            return {"error": str(e), "detail": error_detail}
        except Exception as e:
            return {"error": str(e)}
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有可用的 MCP 工具"""
        if not self._session_initialized:
            await self.initialize_session()
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        
        try:
            response = await self.client.post(
                self.mcp_url.rstrip('/'),
                json=payload,
                headers=headers,
                follow_redirects=True
            )
            
            response.raise_for_status()
            
            # 解析响应
            response_text = response.text
            result = None
            
            if "event:" in response_text:
                lines = response_text.split('\n')
                for line in lines:
                    if line.startswith('data:'):
                        json_str = line[5:].strip()
                        try:
                            result = json.loads(json_str)
                            break
                        except json.JSONDecodeError:
                            continue
            else:
                result = response.json()
            
            if result and "result" in result:
                return result["result"].get("tools", [])
            
            return []
        except Exception as e:
            print(f"⚠️ 获取工具列表失败: {e}")
            return []
    
    async def screen_stocks(
        self,
        industry: str = None,
        sector: str = None,
        country: str = "CN",
        mktcap_min: float = None,
        limit: int = 20,
        provider: str = "yfinance"
    ) -> List[Dict[str, Any]]:
        """
        筛选股票（通过 MCP 工具）
        
        Args:
            industry: 行业名称
            sector: 板块名称
            country: 国家代码（CN 表示中国）
            mktcap_min: 最小市值
            limit: 返回数量限制
            provider: 数据提供商
        
        Returns:
            股票列表
        """
        # 尝试多个可能的工具名称
        tool_names = [
            "equity_screener",
            "equity/screener",
            "equity_screen",
            "equity_screener_general"
        ]
        
        arguments = {
            "provider": provider,
            "limit": limit
        }
        
        if country:
            arguments["country"] = country
        if industry:
            arguments["industry"] = industry
        if sector:
            arguments["sector"] = sector
        if mktcap_min:
            arguments["mktcap_min"] = int(mktcap_min)
        
        for tool_name in tool_names:
            print(f"🔍 尝试使用工具: {tool_name}")
            result = await self.call_tool(tool_name, arguments)
            
            if "error" not in result:
                # 提取股票列表
                stocks = []
                if "results" in result:
                    stocks = result["results"]
                elif isinstance(result, list):
                    stocks = result
                elif "data" in result:
                    stocks = result["data"]
                
                if stocks:
                    print(f"✅ 通过 {tool_name} 获取到 {len(stocks)} 只股票")
                    return stocks
            else:
                print(f"⚠️ {tool_name} 失败: {result.get('error', '未知错误')}")
        
        return []
    
    async def get_sector_performance(
        self,
        group: str = "sector",
        metric: str = "performance",
        provider: str = "finviz"
    ) -> Dict[str, Any]:
        """
        获取行业表现数据（通过 MCP 工具）
        
        Args:
            group: 分组方式（sector/industry/country）
            metric: 指标类型（performance/valuation）
            provider: 数据提供商
        
        Returns:
            行业表现数据
        """
        tool_names = [
            "equity_compare_groups",
            "equity/compare/groups",
            "equity_compare_groups_general"
        ]
        
        arguments = {
            "group": group,
            "metric": metric,
            "provider": provider
        }
        
        for tool_name in tool_names:
            print(f"🔍 尝试使用工具: {tool_name}")
            result = await self.call_tool(tool_name, arguments)
            
            if "error" not in result:
                print(f"✅ 通过 {tool_name} 获取到行业数据")
                return result
            else:
                print(f"⚠️ {tool_name} 失败: {result.get('error', '未知错误')}")
        
        return {}
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 使用示例
async def example_usage():
    """使用示例"""
    helper = MCPToolHelper()
    
    try:
        # 1. 列出所有可用工具
        print("="*60)
        print("📋 步骤1: 列出所有可用工具")
        print("="*60)
        tools = await helper.list_tools()
        print(f"找到 {len(tools)} 个工具")
        
        # 2. 筛选股票
        print("\n" + "="*60)
        print("📊 步骤2: 筛选股票（计算机行业）")
        print("="*60)
        stocks = await helper.screen_stocks(
            industry="计算机",
            country="CN",
            mktcap_min=1e9,
            limit=10,
            provider="yfinance"
        )
        
        if stocks:
            print(f"\n✅ 获取到 {len(stocks)} 只股票:")
            for i, stock in enumerate(stocks[:5], 1):
                symbol = stock.get("symbol", "N/A")
                name = stock.get("name", "N/A")
                print(f"  {i}. {symbol} - {name}")
        else:
            print("⚠️ 未获取到股票数据")
        
        # 3. 获取行业表现
        print("\n" + "="*60)
        print("📈 步骤3: 获取行业表现数据")
        print("="*60)
        sector_data = await helper.get_sector_performance(
            group="sector",
            metric="performance",
            provider="finviz"
        )
        
        if sector_data:
            print("✅ 获取到行业数据")
            print(f"数据键: {list(sector_data.keys())}")
        else:
            print("⚠️ 未获取到行业数据")
        
    finally:
        await helper.close()


if __name__ == "__main__":
    asyncio.run(example_usage())

