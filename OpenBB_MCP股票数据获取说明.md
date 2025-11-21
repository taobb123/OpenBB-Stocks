# OpenBB MCP 股票数据获取说明

## ✅ 可以使用 OpenBB MCP 获取股票数据

代码中已经实现了通过 OpenBB MCP 获取股票数据的功能。`MarketStructureAnalyzer` 类提供了完整的 MCP 调用接口。

## 📋 可用的 MCP 工具

### 1. 股票历史价格数据

**工具名称**：`equity_price_historical`

**使用方法**：
```python
from market_structure_analysis import MarketStructureAnalyzer

analyzer = MarketStructureAnalyzer(mcp_url="http://127.0.0.1:8002/mcp")

# 获取股票历史数据
result = await analyzer.get_stock_historical(
    symbol="AAPL",
    period="1y",  # 1年
    provider="fmp"  # 数据提供商
)
```

**参数说明**：
- `symbol`: 股票代码（如 "AAPL", "600519"）
- `period`: 时间周期（"1y", "6m", "3m"）
- `provider`: 数据提供商（"fmp", "yfinance", "polygon" 等）

**返回数据**：
```python
{
    "results": [
        {
            "date": "2024-01-01",
            "open": 150.0,
            "high": 155.0,
            "low": 149.0,
            "close": 153.0,
            "volume": 1000000
        },
        ...
    ]
}
```

### 2. 股票筛选

**工具名称**：`equity_screener`（或 `equity/screener`, `equity_screen`）

**使用方法**：
```python
# 通过行业筛选股票
stocks = await analyzer.get_stocks_by_industry_openbb(
    industry="计算机",
    country="CN",
    mktcap_min=1e9,  # 最小市值 10 亿
    limit=20,
    provider="yfinance"
)
```

**参数说明**：
- `industry`: 行业名称
- `country`: 国家代码（"CN" 表示中国）
- `mktcap_min`: 最小市值
- `limit`: 返回数量限制
- `provider`: 数据提供商

### 3. 其他可用的 MCP 工具

根据代码实现，还可以使用以下工具：

| 工具名称 | 说明 | 使用场景 |
|---------|------|---------|
| `equity_price_historical` | 获取历史价格 | 技术分析、策略回测 |
| `equity_screener` | 股票筛选 | 行业分析、选股 |
| `equity_compare_groups` | 行业对比 | 行业强弱分析 |
| `index_search` | 指数搜索 | 市场指数查询 |
| `economy_calendar` | 经济日历 | 宏观经济分析 |
| `economy_indicators` | 经济指标 | 宏观经济分析 |

## 🔧 直接调用 MCP 工具

如果需要直接调用 MCP 工具（不通过封装方法），可以使用 `call_mcp_tool` 方法：

```python
from market_structure_analysis import MarketStructureAnalyzer

analyzer = MarketStructureAnalyzer()

# 初始化会话
await analyzer._initialize_session()

# 直接调用 MCP 工具
result = await analyzer.call_mcp_tool(
    "equity_price_historical",
    {
        "symbol": "AAPL",
        "start_date": "2024-01-01",
        "end_date": "2024-11-20",
        "provider": "fmp"
    }
)

print(result)
```

## 📊 在 InteractiveMarketAnalyzer 中使用

`InteractiveMarketAnalyzer` 已经集成了 `MarketStructureAnalyzer`，可以通过 MCP 获取数据：

```python
from interactive_analysis import InteractiveMarketAnalyzer

analyzer = InteractiveMarketAnalyzer(
    mcp_url="http://127.0.0.1:8002/mcp",
    use_akshare=True
)

# 分析器内部会使用 MCP 获取数据（如果需要）
analysis = await analyzer.analyze_custom_stocks(
    stock_symbols=["600519", "000001"],
    market_type="A股"
)
```

## ⚠️ 注意事项

### 1. MCP 服务器地址

默认地址是 `http://127.0.0.1:8002/mcp`，确保：
- OpenBB MCP 服务器正在运行
- 端口号正确（默认 8002）
- 网络连接正常

### 2. 数据提供商（Provider）

不同的 provider 支持不同的市场：
- **fmp**: 支持美股，需要 API key
- **yfinance**: 支持美股和部分国际股票
- **polygon**: 支持美股，需要 API key
- **ec**: 支持 A 股（如果配置了 EC provider）

### 3. A 股数据

对于 A 股数据，建议：
- **优先使用 AKShare**（已在代码中实现）
- 如果 AKShare 不可用，可以尝试 OpenBB MCP 的 yfinance provider
- 注意 A 股代码格式（如 "600519.SS" 或 "000001.SZ"）

### 4. 错误处理

代码已经实现了自动 fallback 机制：
1. 先尝试 MCP 工具调用
2. 如果失败，尝试 REST API
3. 如果失败，使用 AKShare（A 股）
4. 如果失败，使用 yfinance（最后备选）

## 🎯 使用示例

### 示例 1：获取单只股票历史数据

```python
import asyncio
from market_structure_analysis import MarketStructureAnalyzer

async def main():
    analyzer = MarketStructureAnalyzer()
    
    # 获取苹果股票的历史数据
    data = await analyzer.get_stock_historical(
        symbol="AAPL",
        period="1y",
        provider="yfinance"
    )
    
    if data and "results" in data:
        print(f"获取到 {len(data['results'])} 条数据")
        for record in data["results"][:5]:  # 显示前5条
            print(record)
    
    await analyzer.close()

asyncio.run(main())
```

### 示例 2：筛选行业股票

```python
import asyncio
from market_structure_analysis import MarketStructureAnalyzer

async def main():
    analyzer = MarketStructureAnalyzer()
    
    # 获取计算机行业的股票
    stocks = await analyzer.get_stocks_by_industry_openbb(
        industry="计算机",
        country="CN",
        mktcap_min=1e9,
        limit=10,
        provider="yfinance"
    )
    
    if stocks:
        print(f"找到 {len(stocks)} 只股票：")
        for stock in stocks:
            print(f"  {stock.get('symbol')} - {stock.get('name', 'N/A')}")
    
    await analyzer.close()

asyncio.run(main())
```

### 示例 3：在文件分析中使用

```python
from interactive_analysis import InteractiveMarketAnalyzer

# 创建分析器（会自动使用 MCP 如果可用）
analyzer = InteractiveMarketAnalyzer(
    mcp_url="http://127.0.0.1:8002/mcp",
    use_akshare=True
)

# 分析股票列表
analysis = await analyzer.analyze_custom_stocks(
    stock_symbols=["600519", "000001"],
    market_type="A股"
)

# 生成报告
report = analyzer.format_custom_analysis_report(analysis)
print(report)
```

## ✅ 总结

**可以使用 OpenBB MCP 获取股票数据**，代码中已经实现了：

1. ✅ MCP 工具调用接口（`call_mcp_tool`）
2. ✅ 股票历史数据获取（`get_stock_historical`）
3. ✅ 股票筛选功能（`get_stocks_by_industry_openbb`）
4. ✅ 自动 fallback 机制
5. ✅ 错误处理和重试

**建议**：
- 对于 A 股，优先使用 AKShare（更稳定、数据更全）
- 对于美股，可以使用 OpenBB MCP
- 确保 MCP 服务器正常运行

