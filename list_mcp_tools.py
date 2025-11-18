"""
列出MCP服务器可用的工具
帮助确定正确的工具名称格式
"""

import asyncio
import httpx
import json

async def list_mcp_tools():
    """列出所有可用的MCP工具"""
    base_url = "http://127.0.0.1:8002"
    endpoint = f"{base_url}/mcp"
    session_id = None
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # 步骤1: 初始化session
            print("🔧 初始化MCP会话...")
            init_response = await client.post(
                endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "tool-lister",
                            "version": "1.0.0"
                        }
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            )
            
            if "mcp-session-id" in init_response.headers:
                session_id = init_response.headers["mcp-session-id"]
                print(f"✅ Session ID: {session_id}")
            
            # 步骤2: 获取工具列表
            print("\n📋 获取工具列表...")
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            
            if session_id:
                headers["Mcp-Session-Id"] = session_id
            
            response = await client.post(
                endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list"
                },
                headers=headers
            )
            
            print(f"状态码: {response.status_code}")
            
            # 解析SSE响应
            response_text = response.text
            tools_data = None
            
            if "event:" in response_text:
                lines = response_text.split('\n')
                for line in lines:
                    if line.startswith('data:'):
                        json_str = line[5:].strip()
                        try:
                            tools_data = json.loads(json_str)
                            break
                        except json.JSONDecodeError:
                            continue
            else:
                try:
                    tools_data = response.json()
                except:
                    pass
            
            if tools_data and "result" in tools_data:
                tools = tools_data["result"].get("tools", [])
                
                print(f"\n✅ 找到 {len(tools)} 个工具\n")
                print("="*80)
                print("可用工具列表:")
                print("="*80)
                
                # 按类别分组
                tools_by_category = {}
                for tool in tools:
                    name = tool.get("name", "unknown")
                    description = tool.get("description", "无描述")
                    
                    # 尝试从名称推断类别
                    category = "其他"
                    if "_" in name:
                        parts = name.split("_")
                        if len(parts) >= 2:
                            category = parts[0]
                    
                    if category not in tools_by_category:
                        tools_by_category[category] = []
                    
                    tools_by_category[category].append({
                        "name": name,
                        "description": description
                    })
                
                # 打印按类别分组的工具
                for category in sorted(tools_by_category.keys()):
                    print(f"\n📁 {category.upper()}:")
                    print("-" * 80)
                    for tool in sorted(tools_by_category[category], key=lambda x: x["name"]):
                        print(f"  • {tool['name']}")
                        if tool['description']:
                            desc = tool['description'][:60] + "..." if len(tool['description']) > 60 else tool['description']
                            print(f"    {desc}")
                
                # 查找相关的工具
                print("\n" + "="*80)
                print("相关工具（可能用于市场分析）:")
                print("="*80)
                
                relevant_keywords = ["index", "equity", "sector", "economy", "search", "compare"]
                relevant_tools = []
                for tool in tools:
                    name = tool.get("name", "").lower()
                    if any(keyword in name for keyword in relevant_keywords):
                        relevant_tools.append(tool)
                
                for tool in relevant_tools:
                    print(f"  • {tool.get('name')}")
                    print(f"    {tool.get('description', '无描述')[:80]}")
                
                # 保存到文件
                with open("mcp_tools_list.json", "w", encoding="utf-8") as f:
                    json.dump({
                        "total": len(tools),
                        "tools": tools,
                        "by_category": tools_by_category
                    }, f, ensure_ascii=False, indent=2)
                
                print(f"\n✅ 工具列表已保存到 mcp_tools_list.json")
                
                return tools
            else:
                print("❌ 无法获取工具列表")
                print(f"响应内容: {response_text[:500]}")
                return []
                
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return []

if __name__ == "__main__":
    tools = asyncio.run(list_mcp_tools())

