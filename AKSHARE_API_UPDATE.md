# AKShare API 更新说明（2025最新版）

## ⚠️ 已修复的问题

### 1. 废弃接口替换

**旧接口（已删除）**：
```python
ak.stock_a_pe_lg()  # ❌ 已废弃
```

**新接口（推荐）**：
```python
# 最推荐：财务分析指标（最稳定，不走push2）
ak.stock_financial_analysis_indicator(stock="600519")

# 替代方案：行业估值
ak.stock_industry_pe_ratio_cninfo()

# 替代方案：全市场估值
ak.stock_a_indicators_em()
```

### 2. Push2 接口替换

**旧接口（可能被封锁）**：
```python
ak.stock_zh_a_spot_em()  # ❌ 访问 push2.eastmoney.com，可能被封锁
```

**新接口（推荐）**：
```python
# 新浪接口（最稳定，不被封锁）
ak.stock_zh_a_spot()  # ✅ 推荐
```

## 📊 推荐的基本面数据获取方式

### 方式1：财务分析指标（最推荐）

```python
import akshare as ak

# 获取完整的基本面数据
df = ak.stock_financial_analysis_indicator(stock="600519")

# 包含的指标：
# - 市盈率 (PE)
# - 市净率 (PB)
# - ROE (净资产收益率)
# - ROA (总资产收益率)
# - 毛利率
# - 净利率
# - EPS (每股收益)
# - 每股净资产
# - 每股现金流
# - 营业收入
# - 净利润
# - ... 更多指标
```

**优点**：
- ✅ 不走 push2，不会被封锁
- ✅ 字段非常全
- ✅ 所有 A 股都支持
- ✅ 数据稳定可靠

### 方式2：财务报表（补充数据）

```python
# 利润表
income = ak.stock_financial_report_sina(stock="600519", symbol="利润表")

# 资产负债表
balance = ak.stock_financial_report_sina(stock="600519", symbol="资产负债表")

# 现金流量表
cashflow = ak.stock_financial_report_sina(stock="600519", symbol="现金流量表")
```

### 方式3：实时行情（替代 push2）

```python
# 新浪接口（推荐，不走push2）
spot_data = ak.stock_zh_a_spot()

# 或者获取单只股票的实时数据
tick = ak.stock_zh_a_tick_tx(code="600519")
```

## 🔧 代码更新

### 已更新的文件

1. **`akshare_data_source.py`**
   - ✅ 替换 `stock_a_pe_lg()` → `stock_financial_analysis_indicator()`
   - ✅ 替换 `stock_zh_a_spot_em()` → `stock_zh_a_spot()`（优先）
   - ✅ 添加多接口 fallback 机制
   - ✅ 改进错误处理

### 更新后的接口调用

```python
# 获取基本面数据（自动使用最新稳定接口）
fundamentals = akshare_source.get_stock_fundamentals("600519")

# 获取股票列表（使用新浪接口）
stock_list = akshare_source.get_stock_list()

# 获取实时行情（使用新浪接口）
spot_data = akshare_source.get_stock_list()  # 包含实时价格、涨跌幅等
```

## 📋 接口对比表

| 功能 | 旧接口 | 新接口 | 稳定性 |
|------|--------|--------|--------|
| PE/PB/ROE | `stock_a_pe_lg()` ❌ | `stock_financial_analysis_indicator()` ✅ | ⭐⭐⭐⭐⭐ |
| 实时行情 | `stock_zh_a_spot_em()` ⚠️ | `stock_zh_a_spot()` ✅ | ⭐⭐⭐⭐⭐ |
| 财务报表 | - | `stock_financial_report_sina()` ✅ | ⭐⭐⭐⭐ |
| 行业估值 | - | `stock_industry_pe_ratio_cninfo()` ✅ | ⭐⭐⭐⭐ |

## 🎯 使用建议

1. **优先使用 `stock_financial_analysis_indicator`**
   - 最稳定，不走 push2
   - 字段最全
   - 推荐用于基本面分析

2. **实时行情使用 `stock_zh_a_spot`**
   - 新浪接口，不被封锁
   - 数据更新及时
   - 推荐用于实时价格获取

3. **财务报表作为补充**
   - 需要详细财务数据时使用
   - 可以获取历史多期数据

## ⚠️ 注意事项

1. **网络环境**
   - 新浪接口对网络环境要求较低
   - 即使使用 VPN/代理也能正常访问

2. **数据更新频率**
   - 财务数据：通常按季度更新
   - 实时行情：实时更新（可能有几分钟延迟）

3. **错误处理**
   - 代码已添加多接口 fallback
   - 如果主接口失败，会自动尝试备用接口

## 📚 相关文档

- `akshare_data_source.py`：已更新的数据源封装
- `interactive_analysis.py`：使用更新后的接口进行分析
- `COLLABORATION_GUIDE.md`：协作使用指南

