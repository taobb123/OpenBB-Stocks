# A股数据源使用指南

## 📊 数据源优先级（A股市场）

系统现在支持**三层数据源策略**，按稳定性从高到低：

### 1. **OpenBB Platform API + EC Provider** ⭐⭐⭐⭐⭐（最推荐）

**优势**：
- ✅ 最稳定，国内网络环境友好
- ✅ 官方接口，数据质量高
- ✅ 无需额外配置

**使用方法**：
```python
from market_structure_analysis import MarketStructureAnalyzer

analyzer = MarketStructureAnalyzer()
# 系统会自动尝试使用 OpenBB Platform API + EC Provider
result = await analyzer.run_full_analysis(index_query="China", market_type="A股")
```

**注意**：如果 OpenBB Platform 支持 EC provider，系统会自动使用。如果不支持，会自动 fallback 到其他方法。

### 2. **AKShare** ⭐⭐⭐⭐（推荐）

**优势**：
- ✅ 数据全面，覆盖所有 A 股
- ✅ 支持申万行业分类
- ✅ 中文支持好
- ✅ 免费，无需 API key

**安装**：
```bash
pip install akshare
```

**使用方法**：
```python
analyzer = MarketStructureAnalyzer(use_akshare=True)  # 默认启用
```

**注意事项**：
- 如果网络环境无法访问 push2.eastmoney.com，akshare 可能失败
- 系统会自动 fallback 到 yfinance

### 3. **yfinance** ⭐⭐⭐（备用）

**优势**：
- ✅ 免费，无需 API key
- ✅ 全球网络可访问
- ✅ 基础功能稳定

**限制**：
- ⚠️ A股数据可能不完整
- ⚠️ 行业分类有限
- ⚠️ 股票名称可能缺失

## 🔄 自动 Fallback 机制

系统会自动按以下顺序尝试：

```
A股数据获取流程：
1. OpenBB Platform API (EC Provider) → 
2. AKShare → 
3. yfinance → 
4. 示例数据（用于演示）
```

如果某个数据源失败，会自动尝试下一个，确保程序不会中断。

## 📝 代码示例

### 基本使用（推荐）

```python
import asyncio
from market_structure_analysis import MarketStructureAnalyzer

async def main():
    # 自动使用最佳数据源
    analyzer = MarketStructureAnalyzer(use_akshare=True)
    
    # 运行完整分析
    result = await analyzer.run_full_analysis(
        index_query="China",
        market_type="A股"
    )
    
    await analyzer.close()
    return result

# 运行
result = asyncio.run(main())
```

### 手动指定数据源

```python
# 只使用 OpenBB Platform API
analyzer = MarketStructureAnalyzer(use_akshare=False)

# 只使用 AKShare（如果可用）
analyzer = MarketStructureAnalyzer(use_akshare=True)
```

## 🛠️ 故障排除

### 问题1：所有数据源都失败

**现象**：报告显示"待分析"或"未获取到行业数据"

**解决方案**：
1. 检查网络连接
2. 确认 akshare 已安装：`pip install akshare`
3. 检查 OpenBB MCP 服务器是否运行
4. 系统会自动使用示例数据生成报告（用于演示）

### 问题2：AKShare 连接失败

**现象**：`⚠️ AKShare 获取行业数据失败`

**可能原因**：
- push2.eastmoney.com 被网络环境阻断
- akshare 版本过旧

**解决方案**：
- 系统会自动 fallback 到 yfinance
- 或使用 OpenBB Platform API（如果支持 EC provider）

### 问题3：OpenBB EC Provider 不可用

**现象**：`⚠️ 使用 ec provider 失败`

**解决方案**：
- 这是正常的，系统会自动尝试其他 provider（yfinance, fmp, polygon）
- 如果都不行，会使用 AKShare 或 yfinance

## 📈 数据源对比表

| 特性 | OpenBB+EC | AKShare | yfinance |
|------|-----------|---------|----------|
| **稳定性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **A股覆盖** | ✅ 完整 | ✅ 完整 | ⚠️ 部分 |
| **行业分类** | ✅ 详细 | ✅ 申万分类 | ⚠️ 有限 |
| **中文支持** | ✅ 好 | ✅ 很好 | ⚠️ 一般 |
| **网络要求** | ✅ 国内友好 | ⚠️ 可能被阻断 | ✅ 全球可用 |
| **API Key** | ❌ 不需要 | ❌ 不需要 | ❌ 不需要 |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

## 🎯 最佳实践

1. **优先使用 OpenBB Platform API**：如果支持 EC provider，这是最稳定的方案
2. **安装 AKShare 作为备选**：`pip install akshare`
3. **保持网络畅通**：确保可以访问数据源
4. **使用自动 Fallback**：让系统自动选择最佳数据源

## 📚 相关文档

- `AKSHARE_INTEGRATION.md`：AKShare 集成详细说明
- `market_structure_analysis.py`：主分析器代码
- `akshare_data_source.py`：AKShare 数据源封装

