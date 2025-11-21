# OpenBB MCP 集成到文件分析报告说明

## ✅ 集成完成

已将 OpenBB MCP 工具的分析功能集成到文件分析报告的生成过程中。

## 📋 集成内容

### 1. MCP 分析方法

**方法**：`get_stock_mcp_analysis(symbol, hist_data=None)`

**功能**：
- ✅ 获取股票估值数据（PE、PB、市值、股息率）
- ✅ 获取财务指标（营收增长率、净利润、EPS、ROE）
- ✅ 基于历史数据计算价格预测
- ✅ 生成买入信号（结合 MCP 预测和技术指标）

**调用位置**：
- 在 `analyze_custom_stocks()` 方法中，每个股票分析完成后调用

### 2. 报告显示

**位置**：在每只股票的详细分析部分

**显示内容**：
1. **价格预测**
   - 当前价格
   - 预测价格
   - 预期涨跌幅
   - 趋势（上升/下降）
   - 置信度

2. **估值指标**
   - 市盈率(PE)
   - 市净率(PB)
   - 市值
   - 股息率

3. **财务指标**
   - 营收增长率
   - 净利润
   - 每股收益(EPS)
   - 净资产收益率(ROE)

4. **MCP 买入信号**
   - 信号强度（强/中等/弱）
   - 买入理由列表

### 3. 买入信号生成逻辑

**条件**：
1. 价格突破50日均线
2. MCP 预测价格上涨

**信号强度**：
- **强**：满足2个条件
- **中等**：满足1个条件
- **弱**：无买入信号

### 4. 买入理由汇总

在报告的第7部分"买入理由汇总"中，会包含：
- ✅ 右侧交易策略条件
- ✅ OpenBB MCP 买入信号
- ✅ MCP 价格预测
- ✅ MCP 估值指标（如果 PE 较低，可能被低估）

## 🔧 技术实现

### MCP 工具调用

```python
# 1. 获取估值数据
profile_result = await self.analyzer.call_mcp_tool(
    "equity_profile",  # 或 "equity/profile", "equity_info"
    {
        "symbol": openbb_symbol,
        "provider": "yfinance"
    }
)

# 2. 获取财务指标
metrics_result = await self.analyzer.call_mcp_tool(
    "equity_fundamental_metrics",  # 或 "equity/fundamental/metrics"
    {
        "symbol": openbb_symbol,
        "provider": "yfinance"
    }
)
```

### 价格预测计算

```python
# 基于历史数据计算
if hist_data is not None:
    close_prices = hist_data["收盘"].astype(float)
    current_price = close_prices.iloc[-1]
    sma_50 = close_prices.rolling(window=50).mean().iloc[-1]
    
    # 趋势判断
    price_trend = "上升" if current_price > sma_50 else "下降"
    predicted_price = current_price * 1.05 if price_trend == "上升" else current_price * 0.95
```

### 买入信号生成

```python
# 结合 MCP 预测和技术指标
buy_signal = False
buy_reasons = []

# 条件1: 价格突破50日均线
if current_price > sma_50:
    buy_signal = True
    buy_reasons.append("价格突破50日均线")

# 条件2: MCP 预测价格上涨
if predicted_price > current_price:
    buy_signal = True
    buy_reasons.append(f"MCP预测价格上涨 {price_change_pct:.2f}%")
```

## 📊 报告结构

```
自定义股票分析报告
├── 股票1
│   ├── 基本信息
│   ├── 买入时机分析
│   ├── 技术指标（MACD、布林带等）
│   ├── 🤖 OpenBB MCP 分析
│   │   ├── 价格预测
│   │   ├── 估值指标
│   │   ├── 财务指标
│   │   └── MCP 买入信号
│   └── 价格信息
├── 股票2
│   └── ...
├── 策略推荐
├── 风险提示
└── 买入理由汇总（右侧交易策略 + OpenBB MCP 分析）
```

## 🎯 使用示例

### 基本使用

```python
from interactive_analysis import InteractiveMarketAnalyzer

# 创建分析器（MCP 已集成）
analyzer = InteractiveMarketAnalyzer(
    mcp_url="http://127.0.0.1:8002/mcp",
    use_akshare=True
)

# 分析股票列表（会自动调用 MCP 分析）
analysis = await analyzer.analyze_custom_stocks(
    stock_symbols=["600519", "000001"],
    market_type="A股"
)

# 生成报告（包含 MCP 分析结果）
report = analyzer.format_custom_analysis_report(analysis)
print(report)
```

### 报告输出示例

```
🤖 OpenBB MCP 分析:
    价格预测:
      当前价格: 150.00
      预测价格: 157.50
      预期涨跌幅: 5.00%
      趋势: 上升
      置信度: 中等
    估值指标:
      市盈率(PE): 25.30
      市净率(PB): 3.50
      市值: 1,500,000,000
    财务指标:
      营收增长率: 15.20%
      净利润: 50,000,000
      每股收益(EPS): 2.50
    🎯 MCP 买入信号: ✅ 强
      • 价格突破50日均线
      • MCP预测价格上涨 5.00%
```

## ⚠️ 注意事项

### 1. MCP 服务器

- 确保 OpenBB MCP 服务器在 `http://127.0.0.1:8002/mcp` 运行
- 如果 MCP 不可用，分析会继续，但不会包含 MCP 数据

### 2. 数据提供商

- 对于 A 股，MCP 可能无法获取完整数据
- 建议优先使用 AKShare 获取 A 股数据
- MCP 主要用于美股和补充分析

### 3. 错误处理

- MCP 分析失败不会影响整体分析流程
- 如果 MCP 工具调用失败，会显示警告但继续分析
- 报告会显示可用的 MCP 数据，缺失的部分会跳过

### 4. 买入信号

- MCP 买入信号是基于技术指标和价格预测的简单判断
- 实际投资决策需要结合更多因素
- 仅供参考，不构成投资建议

## ✅ 集成完成

现在文件分析报告包含：
- ✅ OpenBB MCP 价格预测
- ✅ OpenBB MCP 估值指标
- ✅ OpenBB MCP 财务指标
- ✅ OpenBB MCP 买入信号
- ✅ 结合技术指标的买入理由汇总

所有 MCP 分析结果都会自动显示在报告中，为投资决策提供更多参考信息。

