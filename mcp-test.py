import httpx
import json

async def test_mcp_connection():
    """测试MCP服务器连接"""
    base_url = "http://127.0.0.1:8002"
    session_id = None
    
    # 尝试不同的端点路径
    endpoints_to_try = [
        f"{base_url}/mcp",
        f"{base_url}/mcp/",
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for endpoint in endpoints_to_try:
            print(f"\n尝试端点: {endpoint}")
            try:
                # 步骤1: 先初始化session（如果需要）
                # 尝试发送一个初始化请求来获取session ID
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
                                "name": "python-test-client",
                                "version": "1.0.0"
                            }
                        }
                    },
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"
                    }
                )
                
                print(f"初始化请求状态码: {init_response.status_code}")
                
                # 从响应头获取session ID
                if "mcp-session-id" in init_response.headers:
                    session_id = init_response.headers["mcp-session-id"]
                    print(f"✅ 获取到Session ID: {session_id}")
                elif init_response.status_code == 200:
                    # 如果初始化成功但没有session ID，尝试从响应中获取
                    try:
                        init_result = init_response.json()
                        print(f"初始化响应: {init_result}")
                    except:
                        pass
                
                # 步骤2: 使用session ID发送实际请求
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
                print(f"响应头: {dict(response.headers)}")
                
                # 检查响应内容
                # MCP服务器可能返回SSE格式（Server-Sent Events）
                response_text = response.text
                
                # 检查是否是SSE格式
                if response_text.startswith("event:") or "event:" in response_text:
                    print("📡 检测到SSE格式响应，正在解析...")
                    # 解析SSE格式
                    lines = response_text.split('\n')
                    json_data = None
                    for line in lines:
                        if line.startswith('data:'):
                            json_str = line[5:].strip()  # 移除 'data:' 前缀
                            try:
                                json_data = json.loads(json_str)
                                break
                            except json.JSONDecodeError:
                                continue
                    
                    if json_data:
                        print(f"✅ SSE响应解析成功:")
                        print(json.dumps(json_data, indent=2, ensure_ascii=False))
                        return json_data
                    else:
                        print(f"❌ 无法从SSE响应中提取JSON")
                        print(f"响应内容 (前500字符): {response_text[:500]}")
                else:
                    # 尝试直接解析JSON
                    try:
                        result = response.json()
                        print(f"✅ JSON响应成功:")
                        print(json.dumps(result, indent=2, ensure_ascii=False))
                        return result
                    except json.JSONDecodeError:
                        print(f"❌ 响应不是有效的JSON")
                        print(f"响应内容 (前500字符): {response_text[:500]}")
                    
            except httpx.ConnectError:
                print(f"❌ 连接失败: 无法连接到 {endpoint}")
                print("   请确保MCP服务器正在运行 (运行 OpenBB - MCP.bat)")
            except httpx.TimeoutException:
                print(f"❌ 请求超时: {endpoint}")
            except Exception as e:
                print(f"❌ 错误: {type(e).__name__}: {e}")
        
        # 如果MCP协议失败，尝试直接调用REST API
        print("\n" + "="*60)
        print("尝试直接调用REST API...")
        print("="*60)
        
        try:
            # 测试REST API端点
            rest_endpoints = [
                f"{base_url}/api/v1/index/search?query=China&provider=cboe",
                f"{base_url}/api/v1/equity/compare/groups?group=sector&metric=performance&provider=finviz",
            ]
            
            for rest_url in rest_endpoints:
                print(f"\n测试REST API: {rest_url}")
                try:
                    response = await client.get(rest_url, timeout=10.0)
                    print(f"状态码: {response.status_code}")
                    if response.status_code == 200:
                        result = response.json()
                        print(f"✅ REST API响应成功")
                        print(json.dumps(result, indent=2, ensure_ascii=False)[:500])
                        return result
                    else:
                        print(f"响应内容: {response.text[:200]}")
                except Exception as e:
                    print(f"❌ 错误: {e}")
        except Exception as e:
            print(f"❌ REST API测试失败: {e}")
    
    print("\n" + "="*60)
    print("所有连接尝试都失败了")
    print("="*60)
    print("\n建议:")
    print("1. 确保MCP服务器正在运行: python -m openbb_mcp_server.app.app --port 8002")
    print("2. 检查服务器日志，确认服务器已启动")
    print("3. 确认端口8002没有被其他程序占用")
    print("4. 查看MCP服务器文档了解正确的端点路径")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_mcp_connection())