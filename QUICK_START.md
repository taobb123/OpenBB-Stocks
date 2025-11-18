# 快速开始 - 市场结构分析框架

## 🎯 目标

通过MCP调用OpenBB API，实现**行业 → 因子 → 策略假设**的分析框架，回答三个核心问题：

1. **目前市场是趋势还是震荡？**
2. **哪些行业强/弱（强弱排序 + 热点持续性）？**
3. **资金在偏好价值 / 增长 / 主题？**

## 📋 实现步骤

### 步骤1：启动OpenBB MCP服务器

```bash
# Windows
OpenBB - MCP.bat

# 或直接运行
python -m openbb_mcp_server.app.app --port 8002
```

服务器将在 `http://127.0.0.1:8002/mcp` 运行。

### 步骤2：安装依赖

```bash
pip install httpx pandas
```

### 步骤3：运行分析脚本

```bash
python market_structure_analysis.py
```

## 🔧 使用的OpenBB API

### 1. 指数搜索
```python
# MCP工具: index_search
# REST API: GET /api/v1/index/search
# 参数: {"query": "China", "provider": "cboe"}
```

### 2. 行业表现
```python
# MCP工具: equity_compare_groups
# REST API: GET /api/v1/equity/compare/groups
# 参数: {
#   "group": "sector",
#   "metric": "performance",
#   "provider": "finviz"
# }
```

### 3. 经济日历
```python
# MCP工具: economy_calendar
# REST API: GET /api/v1/economy/calendar
# 参数: {
#   "provider": "fmp",
#   "start_date": "2024-01-01",
#   "end_date": "2024-01-08"
# }
```

### 4. 宏观经济指标
```python
# MCP工具: economy_indicators
# REST API: GET /api/v1/economy/indicators
# 参数: {
#   "provider": "econdb",
#   "symbol": "main",
#   "country": "united_states"
# }
```

## 📊 分析框架

### 问题1：市场是趋势还是震荡？

**分析维度**：
- 主要指数波动率
- 价格趋势持续性
- 宏观经济指标变化

### 问题2：行业强弱排序

**分析维度**：
- 按时间周期排序（1周、1月、3月、1年）
- 识别持续强势行业
- 分析行业轮动

### 问题3：资金偏好

**分析维度**：
- **价值股**：金融、公用事业（低PE、高股息）
- **增长股**：科技、生物医药（高增长预期）
- **主题股**：AI、新能源、消费等主题板块

## ⚠️ 注意事项

1. **MCP工具名称**：实际工具名称可能不同，需要查看MCP服务器暴露的工具列表
2. **数据提供商**：某些provider可能需要API密钥
3. **错误处理**：脚本包含MCP和REST API两种调用方式作为备选

## 🔍 调试

### 查看可用MCP工具
```python
import httpx
import asyncio

async def list_tools():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8002/mcp/",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
        )
        print(response.json())

asyncio.run(list_tools())
```

### 测试单个API调用
```python
from market_structure_analysis import MarketStructureAnalyzer
import asyncio

async def test():
    analyzer = MarketStructureAnalyzer()
    result = await analyzer.get_indices_data("China")
    print(result)
    await analyzer.close()

asyncio.run(test())
```

## 📚 详细文档

查看 [MARKET_ANALYSIS_GUIDE.md](MARKET_ANALYSIS_GUIDE.md) 获取完整实现指南。

## 🚀 下一步

1. 根据实际MCP工具名称调整脚本
2. 完善分析逻辑，添加更多技术指标
3. 实现数据可视化
4. 生成自动化报告

