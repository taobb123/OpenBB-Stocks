# OpenBB Platform API + EC Provider 集成说明

## ✅ 已完成的集成

### 1. 添加了 `get_stocks_by_industry_openbb` 方法

**位置**：`market_structure_analysis.py` (第308-389行)

**功能**：
- 直接使用 OpenBB Platform API 获取行业股票
- 优先尝试 EC provider（如果可用）
- 自动 fallback 到其他 provider（yfinance, fmp, polygon）
- 支持通过 MCP 工具和 REST API 两种方式调用

**使用示例**：
```python
stocks = await analyzer.get_stocks_by_industry_openbb(
    industry="计算机",
    country="CN",
    mktcap_min=1e9,
    limit=20,
    provider="ec"  # 优先尝试 EC provider
)
```

### 2. 更新了股票筛选逻辑

**位置**：`market_structure_analysis.py` (第1069-1144行)

**三层数据源策略**：

1. **OpenBB Platform API + EC Provider**（最优先）
   - 尝试通过 MCP 工具调用 `equity_screener`
   - 尝试通过 REST API 调用 `/api/v1/equity/screener`
   - 支持多个 provider：ec, yfinance, fmp, polygon

2. **AKShare**（第二优先）
   - 如果 OpenBB Platform API 失败，使用 AKShare
   - 支持中文行业名称
   - 支持市值筛选

3. **yfinance**（最后备选）
   - 如果前两者都失败，使用 yfinance
   - 基础功能，数据可能不完整

### 3. 自动 Fallback 机制

系统会自动按优先级尝试，如果某个数据源失败，会自动切换到下一个：

```
OpenBB Platform API (EC) → AKShare → yfinance → 搜索功能
```

## 📋 使用说明

### 基本使用（推荐）

```python
import asyncio
from market_structure_analysis import MarketStructureAnalyzer

async def main():
    # 系统会自动使用最佳数据源
    analyzer = MarketStructureAnalyzer(use_akshare=True)
    
    # 运行完整分析（会自动尝试 OpenBB + EC Provider）
    result = await analyzer.run_full_analysis(
        index_query="China",
        market_type="A股"
    )
    
    await analyzer.close()
    return result

result = asyncio.run(main())
```

### 手动调用 OpenBB Platform API

```python
# 直接获取某个行业的股票
stocks = await analyzer.get_stocks_by_industry_openbb(
    industry="计算机",
    country="CN",
    mktcap_min=1000000000,  # 10亿人民币
    limit=20,
    provider="ec"  # 优先尝试 EC provider
)

print(f"获取到 {len(stocks)} 只股票")
for stock in stocks:
    print(f"{stock.get('symbol')} - {stock.get('name')}")
```

## 🔍 技术细节

### Provider 尝试顺序

1. **EC Provider**（如果 OpenBB Platform 支持）
   - 东财官方接口
   - 国内网络环境友好
   - 数据质量高

2. **yfinance**
   - 免费，全球可用
   - 基础功能稳定

3. **fmp**
   - 需要 API key
   - 数据质量高

4. **polygon**
   - 需要 API key
   - 专业数据源

### 调用方式

系统会尝试两种方式：

1. **MCP 工具调用**
   ```python
   result = await self.call_mcp_tool(
       "equity_screener",
       {
           "provider": "ec",
           "country": "CN",
           "industry": "计算机",
           "mktcap_min": 1000000000,
           "limit": 20
       }
   )
   ```

2. **REST API 调用**
   ```python
   result = await self.call_rest_api(
       "/api/v1/equity/screener",
       params={
           "provider": "ec",
           "country": "CN",
           "industry": "计算机",
           "mktcap_min": 1000000000,
           "limit": 20
       }
   )
   ```

## ⚠️ 注意事项

### 1. EC Provider 可用性

OpenBB Platform 可能不内置 EC provider。如果不可用：
- 系统会自动尝试其他 provider
- 不会影响程序运行
- 会 fallback 到 AKShare 或 yfinance

### 2. 网络环境

- EC Provider 需要访问东财接口
- 如果网络环境限制，可能无法使用
- 系统会自动 fallback 到其他数据源

### 3. API 兼容性

- OpenBB Platform API 端点可能因版本而异
- 系统会尝试多个可能的端点
- 如果都失败，会使用备选数据源

## 🎯 最佳实践

1. **保持 OpenBB MCP 服务器运行**
   ```bash
   python -m openbb_mcp_server.app.app --port 8002
   ```

2. **安装 AKShare 作为备选**
   ```bash
   pip install akshare
   ```

3. **使用默认配置**
   ```python
   analyzer = MarketStructureAnalyzer(use_akshare=True)
   # 系统会自动选择最佳数据源
   ```

4. **监控日志输出**
   - 查看使用了哪个数据源
   - 如果某个数据源失败，会显示警告
   - 系统会自动切换到下一个数据源

## 📊 数据源对比

| 特性 | OpenBB+EC | AKShare | yfinance |
|------|-----------|---------|----------|
| **稳定性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **网络要求** | 国内友好 | 可能被阻断 | 全球可用 |
| **数据质量** | 高 | 高 | 中等 |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

## 🔧 故障排除

### 问题1：EC Provider 不可用

**现象**：`⚠️ 使用 ec provider 失败`

**解决**：这是正常的，系统会自动尝试其他 provider

### 问题2：所有 Provider 都失败

**现象**：`⚠️ 所有 OpenBB provider 都失败`

**解决**：
1. 检查 OpenBB MCP 服务器是否运行
2. 检查网络连接
3. 系统会自动使用 AKShare 或 yfinance

### 问题3：没有筛选出股票

**现象**：报告显示"待筛选（需要强势行业数据）"

**可能原因**：
- 强势行业数据为空
- 所有数据源都失败
- 筛选条件太严格

**解决**：
1. 检查行业数据是否获取成功
2. 查看日志输出，确认使用了哪个数据源
3. 调整筛选条件（市值、数量等）

## 📚 相关文档

- `DATA_SOURCE_GUIDE.md`：数据源使用指南
- `AKSHARE_INTEGRATION.md`：AKShare 集成说明
- `market_structure_analysis.py`：主分析器代码

