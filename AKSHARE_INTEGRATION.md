# AKShare 数据源集成说明

## 概述

已成功集成 AKShare 作为 A 股数据源，提供更全面和准确的 A 股市场数据。

## 安装

```bash
pip install akshare
```

如果安装较慢，可以使用国内镜像：

```bash
pip install akshare -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 功能特性

### 1. 数据源优先级

- **A股市场**：优先使用 AKShare → Fallback 到 yfinance
- **美股市场**：使用 finviz/fmp（不变）

### 2. 支持的功能

#### ✅ 已集成
- **股票列表**：获取所有 A 股股票
- **股票搜索**：按代码或名称搜索
- **股票筛选**：按行业、市值等条件筛选
- **股票基本信息**：获取股票名称、行业等
- **行业表现**：按行业分组计算表现
- **历史数据**：获取股票历史价格（已实现，待集成到分析流程）

#### 🔄 待扩展
- 财务数据（PE、PB、ROE等）
- 资金流向数据
- 机构持仓数据
- 更详细的行业分类（申万行业）

## 使用方法

### 基本使用

```python
from market_structure_analysis import MarketStructureAnalyzer

# 默认启用 akshare（如果已安装）
analyzer = MarketStructureAnalyzer(use_akshare=True)

# 运行分析
result = await analyzer.run_full_analysis(index_query="China", market_type="A股")
```

### 禁用 akshare

```python
# 如果不想使用 akshare，可以禁用
analyzer = MarketStructureAnalyzer(use_akshare=False)
```

## 数据源对比

| 功能 | AKShare | yfinance | 说明 |
|------|---------|----------|------|
| A股股票列表 | ✅ 完整 | ⚠️ 部分 | AKShare 覆盖所有 A 股 |
| 行业分类 | ✅ 详细 | ⚠️ 有限 | AKShare 支持申万行业分类 |
| 股票名称 | ✅ 准确 | ⚠️ 可能缺失 | AKShare 直接获取中文名称 |
| 实时行情 | ✅ 支持 | ✅ 支持 | 两者都支持 |
| 历史数据 | ✅ 支持 | ✅ 支持 | 两者都支持 |
| 财务数据 | ✅ 丰富 | ⚠️ 有限 | AKShare 提供更多财务指标 |
| 资金流向 | ✅ 支持 | ❌ 不支持 | AKShare 特有功能 |
| 机构持仓 | ✅ 支持 | ❌ 不支持 | AKShare 特有功能 |

## 优势

1. **数据更全面**：覆盖所有 A 股股票，支持申万行业分类
2. **中文支持更好**：直接返回中文股票名称和行业名称
3. **功能更丰富**：支持资金流向、机构持仓等高级数据
4. **免费使用**：无需 API key，完全免费
5. **自动 Fallback**：如果 akshare 失败，自动使用 yfinance

## 注意事项

1. **网络要求**：akshare 需要访问国内数据源，确保网络连接正常
2. **数据更新**：akshare 数据更新可能有延迟（通常几分钟）
3. **函数变化**：akshare 函数名可能随版本更新而变化，代码已做兼容处理
4. **性能考虑**：获取大量数据时可能需要一些时间

## 故障排除

### 问题1：akshare 未安装
```
⚠️ akshare 未安装，请运行: pip install akshare
```
**解决**：运行 `pip install akshare`

### 问题2：akshare 函数不存在
```
⚠️ 获取 A 股股票列表失败: ...
```
**解决**：代码已自动尝试多个函数名，如果仍失败，可能需要更新 akshare 版本

### 问题3：网络连接问题
```
⚠️ AKShare 获取行业数据失败: ...
```
**解决**：检查网络连接，确保可以访问 akshare 数据源

## 未来扩展

可以进一步集成：
- tushare（需要 API key，数据更专业）
- eastmoney（东方财富，部分免费数据）
- 其他 A 股数据源

## 相关文件

- `akshare_data_source.py`：AKShare 数据源封装类
- `market_structure_analysis.py`：主分析器（已集成 akshare）
- `requirements.txt`：依赖列表（包含 akshare）

