# 市场结构分析框架 - 实现指南

## 📋 概述

本框架通过MCP调用OpenBB API，实现**行业 → 因子 → 策略假设**的高层分析框架，回答三个核心宏观问题。

## 🎯 三个核心问题

### 1. 目前市场是趋势还是震荡？
- **分析维度**：
  - 主要指数波动率水平
  - 价格趋势的持续性（ADX等指标）
  - 宏观经济指标变化
  - 市场情绪指标

### 2. 哪些行业强/弱（强弱排序 + 热点持续性）？
- **分析维度**：
  - 按不同时间周期排序行业表现（1周、1月、3月、1年）
  - 识别连续多期表现强势的行业（热点持续性）
  - 分析行业轮动情况
  - 识别弱势行业和潜在反转机会

### 3. 资金在偏好价值 / 增长 / 主题？
- **分析维度**：
  - **价值股**：金融、公用事业等传统低PE、高股息率行业
  - **增长股**：科技、生物医药等高增长预期行业
  - **主题股**：AI、新能源、消费等主题板块
  - 通过行业轮动判断资金流向

## 🔧 实现步骤

### 步骤1：启动OpenBB MCP服务器

确保MCP服务器正在运行：

```bash
# 使用批处理文件启动（Windows）
OpenBB - MCP.bat

# 或直接使用命令
python -m openbb_mcp_server.app.app --port 8002
```

服务器将在 `http://127.0.0.1:8002/mcp` 上运行。

### 步骤2：安装依赖

```bash
pip install httpx pandas
```

### 步骤3：使用分析脚本

#### 方式1：直接运行Python脚本

```python
import asyncio
from market_structure_analysis import MarketStructureAnalyzer

async def main():
    analyzer = MarketStructureAnalyzer(mcp_url="http://127.0.0.1:8002/mcp")
    result = await analyzer.run_full_analysis(index_query="China")
    await analyzer.close()
    return result

# 运行
result = asyncio.run(main())
```

#### 方式2：通过MCP客户端调用

如果你使用的是支持MCP的客户端（如Cursor、Claude Desktop），可以直接调用MCP工具。

### 步骤4：查看分析结果

分析结果会保存到 `market_analysis_result.json` 文件中，包含：

```json
{
  "timestamp": "2024-01-01T12:00:00",
  "data_sources": {
    "indices": {...},
    "sectors": {...},
    "calendar": {...},
    "macro": {...}
  },
  "analysis": {
    "market_regime": {...},
    "sector_strength": {...},
    "capital_preference": {...}
  }
}
```

## 📊 使用的OpenBB API端点

### 1. 指数搜索
```python
# MCP工具名称: index_search
# 参数:
{
    "query": "China",  # 搜索关键词
    "provider": "cboe"  # 数据提供商
}
```

### 2. 行业表现
```python
# MCP工具名称: equity_compare_groups
# 参数:
{
    "group": "sector",      # 分组方式: sector/industry/country
    "metric": "performance", # 指标类型: performance/valuation
    "provider": "finviz"
}
```

### 3. 经济日历
```python
# MCP工具名称: economy_calendar
# 参数:
{
    "provider": "fmp",  # 或 "nasdaq"
    "start_date": "2024-01-01",
    "end_date": "2024-01-08"
}
```

### 4. 宏观经济指标
```python
# MCP工具名称: economy_indicators
# 参数:
{
    "provider": "econdb",
    "symbol": "main",  # 主要指标
    "country": "united_states"  # 国家代码
}
```

## ⚠️ 注意事项

### 1. MCP工具名称
实际MCP服务器暴露的工具名称可能与示例不同。需要：

1. **查看可用工具列表**：
   ```python
   # 调用MCP的 tools/list 方法
   payload = {
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list"
   }
   ```

2. **根据实际工具名称调整**：
   - 工具名称可能是 `index/search` 而不是 `index_search`
   - 可能是 `equity/compare/groups` 而不是 `equity_compare_groups`
   - 需要查看MCP服务器的实际工具列表

### 2. 数据提供商
不同的数据提供商可能有不同的参数要求：
- `provider` 参数需要根据已安装的OpenBB扩展调整
- 某些provider可能需要API密钥

### 3. 错误处理
- 网络请求可能失败，需要适当的重试机制
- MCP服务器可能返回错误，需要检查响应状态

## 🔍 调试建议

### 1. 测试MCP连接
```python
import httpx

async def test_mcp_connection():
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

import asyncio
asyncio.run(test_mcp_connection())
```

### 2. 查看可用工具
运行上述代码，查看MCP服务器实际暴露的工具列表，然后调整脚本中的工具名称。

### 3. 测试单个工具
```python
# 测试单个工具调用
analyzer = MarketStructureAnalyzer()
result = await analyzer.get_indices_data("China")
print(result)
```

## 📈 扩展建议

### 1. 添加更多分析维度
- 技术指标分析（RSI、MACD等）
- 资金流向分析
- 情绪指标分析

### 2. 数据可视化
- 使用matplotlib或plotly绘制行业表现图表
- 创建市场状态仪表板

### 3. 自动化报告
- 定期运行分析
- 生成PDF或HTML报告
- 发送邮件通知

### 4. 策略建议
- 基于分析结果生成交易策略建议
- 风险评估和仓位建议

## 🚀 快速开始

1. **启动MCP服务器**：
   ```bash
   OpenBB - MCP.bat
   ```

2. **运行分析脚本**：
   ```bash
   python market_structure_analysis.py
   ```

3. **查看结果**：
   - 控制台输出分析结果
   - `market_analysis_result.json` 文件包含完整数据

## 📚 相关资源

- [OpenBB文档](https://docs.openbb.co)
- [MCP协议文档](https://modelcontextprotocol.io)
- [OpenBB MCP服务器文档](README.md)

## ❓ 常见问题

### Q: MCP工具名称不匹配怎么办？
A: 使用 `tools/list` 方法查看实际可用的工具名称，然后调整脚本。

### Q: 如何添加更多数据源？
A: 在 `MarketStructureAnalyzer` 类中添加新的方法，调用相应的MCP工具。

### Q: 分析结果如何保存？
A: 当前保存为JSON文件，可以扩展为保存到数据库或生成可视化报告。

