# MCP连接调试指南

## 🔍 问题诊断

如果遇到 `JSONDecodeError` 或其他连接错误，按以下步骤排查：

### 步骤1: 确认MCP服务器正在运行

```bash
# Windows
OpenBB - MCP.bat

# 或直接运行
python -m openbb_mcp_server.app.app --port 8002
```

**检查点**：
- 服务器应该显示类似以下信息：
  ```
  INFO     Starting MCP server 'OpenBB MCP' with transport 'streamable-http' on http://127.0.0.1:8002/mcp
  ```
- 如果看到端口占用错误，尝试更换端口（如8003）

### 步骤2: 测试连接

运行测试脚本：

```bash
python china_market.py
```

这个脚本会：
1. 尝试多个可能的端点路径
2. 显示详细的错误信息
3. 测试REST API作为备选方案

### 步骤3: 检查常见问题

#### 问题1: 连接被拒绝
```
❌ 连接失败: 无法连接到 http://127.0.0.1:8002/mcp
```

**解决方案**：
- 确认MCP服务器正在运行
- 检查防火墙设置
- 确认端口号正确（默认8002）

#### 问题2: 400 Bad Request - Missing session ID
```
状态码: 400
错误: "Bad Request: Missing session ID"
```

**原因**：
- MCP服务器需要先初始化session才能使用
- 需要在请求头中包含 `Mcp-Session-Id`

**解决方案**：
1. 先发送 `initialize` 请求来获取session ID：
```python
init_response = await client.post(
    endpoint,
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "client", "version": "1.0.0"}
        }
    },
    headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
)

# 从响应头获取session ID
session_id = init_response.headers.get("mcp-session-id")
```

2. 在后续请求中使用session ID：
```python
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Mcp-Session-Id": session_id  # 添加session ID
}
```

#### 问题3: 406 Not Acceptable 错误
```
状态码: 406
错误: "Not Acceptable: Client must accept both application/json and text/event-stream"
```

**原因**：
- MCP服务器需要客户端在请求头中同时接受 `application/json` 和 `text/event-stream` 两种内容类型

**解决方案**：
在请求头中添加 `Accept` 头：
```python
headers={
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"  # 必须同时接受两种格式
}
```

#### 问题4: SSE格式响应（Server-Sent Events）
```
响应不是有效的JSON
响应内容: event: message
data: {"jsonrpc": "2.0", ...}
```

**原因**：
- MCP服务器使用`streamable-http`传输协议，返回SSE格式
- 响应格式是 `event: message\ndata: {json}` 而不是纯JSON

**解决方案**：
解析SSE格式，从`data:`行提取JSON：
```python
response_text = response.text
if "event:" in response_text:
    lines = response_text.split('\n')
    for line in lines:
        if line.startswith('data:'):
            json_str = line[5:].strip()  # 移除 'data:' 前缀
            result = json.loads(json_str)
            break
```

#### 问题5: JSON解码错误
```
JSONDecodeError: Expecting value
```

**可能原因**：
- 服务器返回了HTML错误页面（404/500）
- 端点路径不正确
- 服务器未正确启动

**解决方案**：
1. 查看服务器日志，确认启动成功
2. 检查响应内容（测试脚本会显示）
3. 尝试使用REST API作为备选方案

#### 问题6: 响应不是JSON格式

如果响应是HTML（如404页面），说明端点路径不对。

**解决方案**：
- 查看MCP服务器启动日志，确认实际端点
- 根据OpenBB MCP文档调整端点路径
- 使用REST API直接调用（`/api/v1/...`）

## 🔧 正确的调用方式

### 方式1: MCP协议（如果支持）

```python
import httpx

async def call_mcp():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8002/mcp",  # 或 /mcp/
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"  # 重要：必须包含此头
            }
        )
        return response.json()
```

### 方式2: REST API（推荐，更可靠）

```python
import httpx

async def call_rest_api():
    async with httpx.AsyncClient() as client:
        # 直接调用OpenBB REST API
        response = await client.get(
            "http://127.0.0.1:8002/api/v1/index/search",
            params={"query": "China", "provider": "cboe"}
        )
        return response.json()
```

## 📝 修改分析脚本使用REST API

如果MCP协议不可用，可以修改 `market_structure_analysis.py` 优先使用REST API：

```python
# 在 call_mcp_tool 方法中，优先尝试REST API
async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    # 首先尝试REST API（更可靠）
    rest_endpoint = self._mcp_tool_to_rest_endpoint(tool_name)
    if rest_endpoint:
        result = await self.call_rest_api(rest_endpoint, arguments)
        if result:
            return result
    
    # 如果REST API失败，再尝试MCP协议
    # ... MCP协议调用代码 ...
```

## 🚀 快速修复

如果MCP协议不工作，可以直接使用REST API：

1. **修改 `market_structure_analysis.py`**：
   - 在 `call_mcp_tool` 方法中，优先使用 `call_rest_api`
   - 或者直接使用REST API端点

2. **使用REST API端点映射**：
   ```python
   # MCP工具名称 -> REST API端点映射
   TOOL_TO_ENDPOINT = {
       "index_search": "/api/v1/index/search",
       "equity_compare_groups": "/api/v1/equity/compare/groups",
       "economy_calendar": "/api/v1/economy/calendar",
       "economy_indicators": "/api/v1/economy/indicators",
       "equity_search": "/api/v1/equity/search",
       "equity_screener": "/api/v1/equity/screener",
       "equity_price_historical": "/api/v1/equity/price/historical",
   }
   ```

## 📚 参考

- [OpenBB MCP服务器文档](README.md)
- [市场分析指南](MARKET_ANALYSIS_GUIDE.md)
- [扩展功能指南](EXTENDED_FEATURES_GUIDE.md)

## 💡 提示

1. **优先使用REST API**：REST API通常比MCP协议更稳定可靠
2. **检查服务器日志**：MCP服务器启动时会显示实际端点
3. **使用测试脚本**：`china_market.py` 会自动尝试多种连接方式
4. **查看响应内容**：如果JSON解析失败，查看原始响应内容有助于诊断问题

