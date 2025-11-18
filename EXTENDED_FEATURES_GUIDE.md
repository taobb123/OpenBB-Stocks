# 扩展功能使用指南

## 📋 概述

本指南介绍如何使用扩展后的市场分析框架，包含完整的6步分析流程。

## 🎯 完整工作流（Step 1-6）

### Step 1: 市场状态分析
判断市场是趋势还是震荡

### Step 2: 行业强弱分析
- 获取行业表现数据（类似 `openbb.sectors.performance()`）
- 获取行业热力图（类似 `openbb.sectors.heatmap()`）
- 分析行业强弱排名和资金流向

### Step 3: 筛选行业内的强势股票
- 股票搜索（类似 `openbb.equity.search()`）
- 股票筛选器（类似 `openbb.equity.screener()`）
- 结合基本面指标筛选

### Step 4: 构建策略（趋势/反转/因子）
- MA（移动平均）策略分析
- MR（均值回归）策略分析
- 策略适配性判断

### Step 5: 股票深度研究
- 财务与盈利能力分析
- 估值分析（PE/PB vs 行业）
- 技术面分析（RSI、MACD、SMA等）

### Step 6: 生成投资报告
自动生成结构化投资报告

## 🚀 快速开始

### 方式1: 运行完整工作流

```python
import asyncio
from market_structure_analysis import MarketStructureAnalyzer

async def main():
    analyzer = MarketStructureAnalyzer(mcp_url="http://127.0.0.1:8002/mcp")
    
    # 运行完整工作流
    result = await analyzer.run_complete_workflow(
        index_query="China",           # 指数搜索关键词
        target_sector="航空",          # 目标行业（可选）
        target_stocks=["600111"],      # 目标股票（可选）
        market="A股"                   # 市场类型：A股/美股/港股
    )
    
    await analyzer.close()

asyncio.run(main())
```

### 方式2: 单独运行某个步骤

```python
# Step 2: 行业强弱分析
sector_performance = await analyzer.get_sector_performance_detailed()
sector_heatmap = await analyzer.get_sector_heatmap()
sector_ranking = analyzer.analyze_sector_ranking(sector_performance)

# Step 3: 股票筛选
stocks = await analyzer.search_stocks("航空")
screened = await analyzer.screen_stocks({
    "sector": "technology",
    "mktcap": "large"
})

# Step 4: 策略分析
ma_result = await analyzer.analyze_ma_strategy("600111", fast=5, slow=20)
mr_result = await analyzer.analyze_mr_strategy("600111", window=20, z_entry=1.0)
strategy_fit = analyzer.determine_strategy_fit("趋势", ma_result, mr_result)

# Step 5: 股票深度研究
deep_analysis = await analyzer.analyze_stock_deep("600111")

# Step 6: 生成报告
report = analyzer.generate_investment_report(full_analysis)
```

## 📊 详细功能说明

### Step 2: 行业强弱分析

#### 获取行业表现数据
```python
sector_data = await analyzer.get_sector_performance_detailed()
```

**分析要点**：
- 升序排名 → 找最强的三个行业
- 看这些行业是否有资金流入（moneyflow）趋势
- 判断行业是否处在加速上涨/回调/震荡阶段

#### 获取行业热力图
```python
heatmap_data = await analyzer.get_sector_heatmap()
```

### Step 3: 股票筛选

#### 搜索股票
```python
# 搜索关键词（如行业、主题）
results = await analyzer.search_stocks("航空", provider="nasdaq")
results = await analyzer.search_stocks("AI", provider="nasdaq")
```

#### 使用筛选器
```python
# 筛选条件示例
filters = {
    "sector": "technology",      # 行业
    "mktcap": "large",          # 市值
    "price_min": 10,            # 最低价格
    "volume_min": 1000000,      # 最低成交量
    "beta_min": 0.5,            # 最低Beta
    "beta_max": 1.5             # 最高Beta
}

screened_stocks = await analyzer.screen_stocks(filters, provider="finviz")
```

**筛选要点**：
- 在强势行业里筛强势股（相对强度趋势、换手、成交量）
- 避免只看K线，要结合基本面指标：
  - 营收增速
  - 毛利率
  - ROE
  - 机构持仓

### Step 4: 策略分析

#### MA（移动平均）策略
```python
ma_result = await analyzer.analyze_ma_strategy(
    symbol="600111",
    fast=5,      # 快速均线周期
    slow=20,     # 慢速均线周期
    period="1y" # 回测周期
)
```

**MA策略特点**：
- 当快线上穿慢线时产生买入信号
- 当快线下穿慢线时产生卖出信号
- **适合趋势市场**（多个山顶 → MA高收益）

#### MR（均值回归）策略
```python
mr_result = await analyzer.analyze_mr_strategy(
    symbol="600111",
    window=20,    # 窗口期
    z_entry=1.0,  # 入场Z值（标准差倍数）
    z_exit=0.0,   # 出场Z值
    period="1y"   # 回测周期
)
```

**MR策略特点**：
- 当价格偏离均值超过Z_entry个标准差时入场
- 当价格回归到均值附近（Z_exit）时出场
- **适合震荡市场**（多个谷底 → MR高收益）

#### 策略适配性判断
```python
strategy_fit = analyzer.determine_strategy_fit(
    market_regime="趋势",  # 或 "震荡"
    ma_result=ma_result,
    mr_result=mr_result
)
```

**策略选择表**：

| 市场形态 | MA策略 | MR策略 | 推荐策略 |
|---------|--------|--------|---------|
| 多个山顶（趋势） | 高收益 | 低收益 | **MA** |
| 多个谷底（震荡） | 增长有限 | 高收益 | **MR** |

### Step 5: 股票深度研究

#### 财务与盈利能力
```python
fundamentals = await analyzer.get_stock_fundamentals("600111")
```

**关注指标**：
- 营收/净利润趋势
- 毛利率上升？下降？
- ROE是否稳定？
- 负债率是否可控？

#### 估值分析
```python
valuation = await analyzer.get_stock_valuation("600111")
```

**估值判断**：
- PE < 行业中位数 → 高性价比
- ROE > 行业平均 → 优质
- 反之则属高估

#### 技术面分析
```python
technical = await analyzer.get_stock_technical(
    symbol="600111",
    indicators=["rsi", "macd", "sma"]
)
```

**技术指标**：
- RSI：相对强弱指标
- MACD：趋势指标
- SMA：简单移动平均
- 判断趋势/盘整状态

#### 完整深度研究
```python
deep_analysis = await analyzer.analyze_stock_deep("600111")
```

包含财务、估值、技术面的综合分析。

### Step 6: 生成投资报告

```python
report = analyzer.generate_investment_report(full_analysis)
```

**报告内容**：
1. 当前市场状态
2. 行业强弱排序
3. 候选股票名单（3-5个）
4. 策略推荐（趋势/反转）
5. 风险提示与触发点

报告会自动保存为文本文件。

## 📝 使用示例

### 示例1: 分析整个市场
```python
result = await analyzer.run_complete_workflow(
    index_query="China",
    market="A股"
)
```

### 示例2: 分析特定行业
```python
result = await analyzer.run_complete_workflow(
    index_query="China",
    target_sector="航空",
    market="A股"
)
```

### 示例3: 分析特定股票
```python
result = await analyzer.run_complete_workflow(
    index_query="China",
    target_stocks=["600111", "600519"],
    market="A股"
)
```

### 示例4: 完整分析（行业+股票）
```python
result = await analyzer.run_complete_workflow(
    index_query="China",
    target_sector="航空",
    target_stocks=["600111"],
    market="A股"
)
```

## ⚠️ 注意事项

1. **MCP工具名称**：实际工具名称可能不同，脚本已包含REST API备选方案
2. **数据提供商**：某些provider可能需要API密钥
3. **市场类型**：不同市场（A股/美股/港股）的股票代码格式不同
4. **策略回测**：当前实现为框架结构，实际回测需要调用OpenBB的technical API

## 🔧 扩展建议

1. **添加更多技术指标**：RSI、MACD、布林带等
2. **实现实际回测**：调用OpenBB的technical API进行策略回测
3. **数据可视化**：使用matplotlib/plotly绘制图表
4. **自动化报告**：定期运行分析，生成PDF报告
5. **策略优化**：添加更多策略类型（如动量策略、反转策略）

## 📚 相关文档

- [MARKET_ANALYSIS_GUIDE.md](MARKET_ANALYSIS_GUIDE.md) - 基础分析指南
- [QUICK_START.md](QUICK_START.md) - 快速开始指南

## ❓ 常见问题

### Q: 如何判断市场是趋势还是震荡？
A: 使用Step 1的市场状态分析，结合指数波动率和宏观经济指标判断。

### Q: MA和MR策略如何选择？
A: 根据市场状态选择：
- 趋势市场 → MA策略
- 震荡市场 → MR策略

### Q: 如何筛选强势股票？
A: 使用Step 3的筛选功能，结合：
- 相对强度趋势
- 换手率和成交量
- 基本面指标（营收增速、毛利率、ROE、机构持仓）

### Q: 报告保存在哪里？
A: 报告保存在当前目录，文件名格式：`investment_report_YYYYMMDD_HHMMSS.txt`

