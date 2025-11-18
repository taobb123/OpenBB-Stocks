# MCP 工具直接使用指南

## 📋 概述

本指南说明如何直接使用 MCP 工具获取数据，然后与程序协作生成完整的分析报告。

## 🎯 为什么需要直接使用 MCP 工具？

从日志可以看到：
- REST API `/api/v1/equity/screener` 不可用
- 所有 OpenBB provider 都失败
- **但 MCP 工具应该可用！**

直接使用 MCP 工具的优势：
1. ✅ 绕过 REST API 限制
2. ✅ 更直接的数据获取方式
3. ✅ 更好的错误处理
4. ✅ 可以手动调试和测试

## 🛠️ 使用方法

### 方法1：使用 MCPToolHelper（推荐）

```python
import asyncio
from mcp_tool_helper import MCPToolHelper

async def main():
    helper = MCPToolHelper()
    
    try:
        # 1. 列出所有可用工具
        tools = await helper.list_tools()
        print(f"找到 {len(tools)} 个工具")
        
        # 2. 筛选股票
        stocks = await helper.screen_stocks(
            industry="计算机",
            country="CN",
            mktcap_min=1e9,
            limit=10,
            provider="yfinance"
        )
        
        print(f"获取到 {len(stocks)} 只股票")
        for stock in stocks:
            print(f"{stock.get('symbol')} - {stock.get('name')}")
        
        # 3. 获取行业表现
        sector_data = await helper.get_sector_performance(
            group="sector",
            metric="performance",
            provider="finviz"
        )
        
    finally:
        await helper.close()

asyncio.run(main())
```

### 方法2：在分析器中使用（已集成）

`MarketStructureAnalyzer` 已经集成了 MCP 工具调用，会自动尝试：

```python
from market_structure_analysis import MarketStructureAnalyzer

analyzer = MarketStructureAnalyzer()
result = await analyzer.run_full_analysis(
    index_query="China",
    market_type="A股"
)
```

系统会自动：
1. 尝试 MCP 工具（多个工具名称）
2. 如果失败，尝试 OpenBB Platform API
3. 如果失败，尝试 AKShare
4. 如果失败，尝试 yfinance

## 📊 完整的协作流程

### 步骤1：直接调用 MCP 工具获取数据

```python
from mcp_tool_helper import MCPToolHelper

helper = MCPToolHelper()

# 获取强势行业的股票
strong_sectors = ["计算机", "电子", "非银金融"]
all_stocks = []

for sector in strong_sectors:
    stocks = await helper.screen_stocks(
        industry=sector,
        country="CN",
        mktcap_min=1e9,
        limit=10,
        provider="yfinance"
    )
    all_stocks.extend(stocks)
    print(f"{sector}: {len(stocks)} 只股票")

await helper.close()
```

### 步骤2：将数据传递给分析器

```python
from market_structure_analysis import MarketStructureAnalyzer

analyzer = MarketStructureAnalyzer()

# 使用 MCP 工具获取的数据
# 方式1：直接使用分析器的 MCP 工具调用（已集成）
result = await analyzer.run_full_analysis(
    index_query="China",
    market_type="A股"
)

# 方式2：手动获取数据后传递给分析器
# （需要修改分析器以支持外部数据输入）
```

### 步骤3：生成完整报告

```python
# 分析器会自动生成报告
report = analyzer.generate_investment_report(result)
print(report)

# 报告已保存到文件
# investment_report_YYYYMMDD_HHMMSS.txt
```

## 🔍 可用的 MCP 工具

### 股票筛选相关

| 工具名称 | 说明 | 参数示例 |
|---------|------|---------|
| `equity_screener` | 股票筛选器 | `{"provider": "yfinance", "country": "CN", "industry": "计算机"}` |
| `equity/screener` | 股票筛选器（另一种格式） | 同上 |
| `equity_screen` | 股票筛选器（简化版） | 同上 |

### 行业分析相关

| 工具名称 | 说明 | 参数示例 |
|---------|------|---------|
| `equity_compare_groups` | 行业对比 | `{"group": "sector", "metric": "performance", "provider": "finviz"}` |
| `equity/compare/groups` | 行业对比（另一种格式） | 同上 |

### 指数搜索相关

| 工具名称 | 说明 | 参数示例 |
|---------|------|---------|
| `index_search` | 指数搜索 | `{"query": "China", "provider": "cboe"}` |
| `index/search` | 指数搜索（另一种格式） | 同上 |

## 📝 实际使用示例

### 示例1：获取计算机行业股票

```python
import asyncio
from mcp_tool_helper import MCPToolHelper

async def get_computer_stocks():
    helper = MCPToolHelper()
    
    try:
        stocks = await helper.screen_stocks(
            industry="计算机",
            country="CN",
            mktcap_min=1000000000,  # 10亿人民币
            limit=20,
            provider="yfinance"
        )
        
        print(f"获取到 {len(stocks)} 只计算机行业股票:")
        for i, stock in enumerate(stocks, 1):
            symbol = stock.get("symbol", "N/A")
            name = stock.get("name", "N/A")
            mktcap = stock.get("market_cap", 0)
            print(f"{i}. {symbol} - {name} (市值: {mktcap/1e8:.2f}亿)")
        
        return stocks
    finally:
        await helper.close()

stocks = asyncio.run(get_computer_stocks())
```

### 示例2：获取行业表现数据

```python
import asyncio
from mcp_tool_helper import MCPToolHelper

async def get_sector_performance():
    helper = MCPToolHelper()
    
    try:
        # 尝试多个 provider
        providers = ["finviz", "yfinance", "fmp"]
        
        for provider in providers:
            print(f"\n尝试使用 {provider}...")
            data = await helper.get_sector_performance(
                group="sector",
                metric="performance",
                provider=provider
            )
            
            if data and "error" not in data:
                print(f"✅ {provider} 成功")
                if "results" in data:
                    sectors = data["results"]
                    print(f"获取到 {len(sectors)} 个行业")
                    for sector in sectors[:5]:
                        name = sector.get("name", "N/A")
                        perf = sector.get("performance_1m", 0)
                        print(f"  {name}: {perf:.2f}%")
                break
            else:
                print(f"⚠️ {provider} 失败")
        
    finally:
        await helper.close()

asyncio.run(get_sector_performance())
```

### 示例3：完整分析流程

```python
import asyncio
from mcp_tool_helper import MCPToolHelper
from market_structure_analysis import MarketStructureAnalyzer

async def full_analysis_with_mcp():
    # 步骤1：使用 MCP 工具获取数据
    helper = MCPToolHelper()
    
    try:
        # 获取强势行业
        strong_sectors = ["计算机", "电子", "非银金融"]
        all_stocks = {}
        
        for sector in strong_sectors:
            print(f"\n获取 {sector} 行业股票...")
            stocks = await helper.screen_stocks(
                industry=sector,
                country="CN",
                mktcap_min=1e9,
                limit=10,
                provider="yfinance"
            )
            all_stocks[sector] = stocks
            print(f"  ✅ {sector}: {len(stocks)} 只股票")
        
        # 步骤2：使用分析器生成报告
        analyzer = MarketStructureAnalyzer()
        
        # 运行完整分析（会自动使用 MCP 工具）
        result = await analyzer.run_full_analysis(
            index_query="China",
            market_type="A股"
        )
        
        # 生成报告
        report = analyzer.generate_investment_report(result)
        print("\n" + "="*60)
        print("完整分析报告")
        print("="*60)
        print(report)
        
        await analyzer.close()
        
    finally:
        await helper.close()

asyncio.run(full_analysis_with_mcp())
```

## 🔧 故障排除

### 问题1：MCP 工具调用失败

**现象**：`⚠️ equity_screener 失败`

**解决方案**：
1. 检查 MCP 服务器是否运行：`python -m openbb_mcp_server.app.app --port 8002`
2. 检查工具名称是否正确（尝试多个可能的名称）
3. 检查参数格式是否正确

### 问题2：Session ID 问题

**现象**：`400 Bad Request - Missing session ID`

**解决方案**：
- `MCPToolHelper` 会自动初始化会话
- 如果仍然失败，检查 MCP 服务器配置

### 问题3：工具返回空数据

**现象**：工具调用成功但返回空列表

**可能原因**：
- 筛选条件太严格
- Provider 不支持该参数
- 数据源暂时不可用

**解决方案**：
- 放宽筛选条件（如降低市值要求）
- 尝试不同的 provider
- 检查网络连接

## 📚 相关文件

- `mcp_tool_helper.py`：MCP 工具调用助手
- `market_structure_analysis.py`：主分析器（已集成 MCP 工具调用）
- `list_mcp_tools.py`：列出所有可用 MCP 工具

## 🎯 最佳实践

1. **先列出可用工具**：使用 `list_mcp_tools.py` 查看所有可用工具
2. **测试单个工具**：先用 `MCPToolHelper` 测试单个工具调用
3. **集成到分析器**：确认工具可用后，使用 `MarketStructureAnalyzer` 进行完整分析
4. **错误处理**：始终检查返回结果中的 `error` 字段
5. **多工具尝试**：如果某个工具失败，尝试其他可能的工具名称

