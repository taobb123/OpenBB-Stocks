# 用户与程序协作指南

## 🎯 概述

本指南说明如何通过用户输入、外部工具协作等方式，充分利用 akshare 的优势，完成完整的市场分析报告。

## 🔧 核心功能

### 1. 股票代码外部输入

支持多种输入方式：
- ✅ 手动输入（命令行）
- ✅ 从文件读取
- ✅ 从外部工具（OpenBB应用端、Excel等）复制粘贴
- ✅ 程序自动筛选（完整分析模式）

### 2. 买入时机判断

使用 akshare 获取历史数据，分析：
- ✅ **移动平均线（MA）**：判断趋势方向
- ✅ **相对强弱指标（RSI）**：判断超买超卖
- ✅ **价格位置**：相对于52周高低点的位置
- ✅ **成交量分析**：判断资金关注度
- ✅ **综合评分**：给出买入/观望/谨慎建议

### 3. 充分利用 akshare 优势

- ✅ **实时行情数据**：获取最新价格、涨跌幅、成交量等
- ✅ **财务数据**：PE、PB、市值等基本面指标
- ✅ **历史数据**：支持前复权、后复权，用于技术分析
- ✅ **股票信息**：公司名称、行业分类等

## 📋 使用流程

### 方式1：交互式分析（推荐）

```bash
python interactive_analysis.py
```

然后选择：
1. **输入股票代码列表**：手动输入要分析的股票
2. **从文件读取**：从文本文件读取股票代码列表
3. **外部工具协作**：使用 OpenBB 应用端等工具筛选后输入
4. **完整市场分析**：自动筛选强势行业股票

### 方式2：程序化调用

```python
import asyncio
from interactive_analysis import InteractiveMarketAnalyzer

async def main():
    analyzer = InteractiveMarketAnalyzer(use_akshare=True)
    
    # 分析自定义股票列表
    stock_symbols = ["600519", "000001", "000002"]
    analysis = await analyzer.analyze_custom_stocks(
        stock_symbols,
        market_type="A股"
    )
    
    # 生成报告
    report = analyzer.format_custom_analysis_report(analysis)
    print(report)
    
    await analyzer.close()

asyncio.run(main())
```

## 🔄 完整协作流程

### 步骤1：使用外部工具获取股票列表

#### 选项A：使用 OpenBB 应用端

1. 打开 OpenBB 应用端
2. 使用筛选功能找到目标股票
3. 复制股票代码列表
4. 在交互式分析中选择"外部工具协作"模式
5. 粘贴股票代码

#### 选项B：使用 Excel/其他工具

1. 在 Excel 中筛选股票
2. 导出股票代码列
3. 保存为文本文件（每行一个代码）
4. 在交互式分析中选择"从文件读取"

#### 选项C：手动输入

1. 直接输入股票代码（用逗号或空格分隔）
2. 例如：`600519,000001,000002` 或 `600519 000001 000002`

### 步骤2：程序自动分析

程序会自动：
1. ✅ 使用 akshare 获取每只股票的历史数据
2. ✅ 计算技术指标（MA、RSI、价格位置、成交量）
3. ✅ 判断买入时机（综合评分）
4. ✅ 获取基本面数据（PE、PB、市值等）
5. ✅ 获取股票基本信息

### 步骤3：生成完整报告

报告包含：
- ⏰ **买入时机分析**：综合评分、建议、关键因素
- 📊 **技术指标**：MA、RSI、价格位置、成交量
- 💰 **价格信息**：当前价、52周高低点
- 📈 **基本面数据**：PE、PB、市值等

## 📊 时机判断详解

### 评分系统

| 因素 | 加分 | 减分 |
|------|------|------|
| 均线上升趋势 | +2 | - |
| 均线下降趋势 | - | - |
| RSI超卖（<30） | +2 | - |
| RSI超买（>70） | - | -2 |
| 价格处于52周低位 | +2 | - |
| 价格处于52周高位 | - | -1 |
| 成交量放大 | +1 | - |

### 建议标准

- **买入**：评分 ≥ 3
- **观望**：评分 0-2
- **谨慎**：评分 < 0

### 示例输出

```
⏰ 买入时机分析:
  综合评分: 4
  建议: 买入

  关键因素:
    ✅ 均线呈上升趋势
    ✅ RSI显示超卖，可能反弹
    ✅ 价格处于52周低位
    ✅ 成交量放大，资金关注

  技术指标:
    均线: MA5=150.23, MA20=148.56, 趋势=上升
    RSI: 28.45 (超卖)
    价格位置: 15.3% (低位)
```

## 🎯 实际使用示例

### 示例1：分析单只股票

```python
from interactive_analysis import InteractiveMarketAnalyzer

analyzer = InteractiveMarketAnalyzer(use_akshare=True)

# 分析单只股票
timing = analyzer.get_stock_timing_analysis("600519")
print(f"时机评分: {timing['timing']['score']}")
print(f"建议: {timing['timing']['recommendation']}")
```

### 示例2：从 OpenBB 应用端获取股票后分析

1. 在 OpenBB 应用端筛选出"计算机"行业前10只股票
2. 复制股票代码：`000977,688041,300496,...`
3. 运行交互式分析：
   ```bash
   python interactive_analysis.py
   ```
4. 选择"3. 外部工具协作"
5. 粘贴股票代码
6. 程序自动分析并生成报告

### 示例3：批量分析

创建 `stocks.txt` 文件：
```
600519
000001
000002
600036
```

然后运行：
```bash
python interactive_analysis.py
# 选择 2. 从文件读取
# 输入 stocks.txt
```

## 🔍 充分利用 akshare 的优势

### 1. 实时数据获取

```python
# 获取实时行情
spot_data = analyzer.akshare.get_stock_list()
# 包含：最新价、涨跌幅、成交量、换手率、PE、PB等
```

### 2. 历史数据分析

```python
# 获取历史数据（支持前复权）
hist_data = analyzer.akshare.get_stock_historical(
    symbol="600519",
    start_date="20240101",
    end_date="20241118",
    adjust="qfq"  # 前复权
)
```

### 3. 基本面数据

```python
# 获取基本面数据
fundamentals = analyzer.get_stock_fundamentals_akshare("600519")
# 包含：PE、PB、市值、财务指标等
```

### 4. 时机判断

```python
# 综合分析买入时机
timing = analyzer.get_stock_timing_analysis("600519")
# 包含：技术指标、综合评分、建议等
```

## 📝 报告格式

生成的报告包含：

1. **股票代码和基本信息**
2. **买入时机分析**
   - 综合评分
   - 建议（买入/观望/谨慎）
   - 关键因素列表
   - 技术指标详情
3. **基本面数据**
   - PE、PB、市值
   - 财务指标
4. **价格信息**
   - 当前价
   - 52周高低点

## 🚀 最佳实践

1. **先用外部工具筛选**：使用 OpenBB 应用端或其他工具初步筛选
2. **输入到程序分析**：使用交互式分析进行深度分析
3. **关注时机判断**：重点关注"买入时机分析"部分
4. **结合基本面**：技术面 + 基本面综合判断
5. **保存报告**：报告自动保存，方便后续查看

## ⚠️ 注意事项

1. **确保 akshare 已安装**：`pip install akshare`
2. **网络连接**：akshare 需要访问数据源
3. **股票代码格式**：A股代码为6位数字（如 600519）
4. **数据更新延迟**：实时数据可能有几分钟延迟

## 📚 相关文件

- `interactive_analysis.py`：交互式分析主程序
- `akshare_data_source.py`：akshare 数据源封装
- `market_structure_analysis.py`：市场结构分析器

## 🎯 总结

通过用户输入和外部工具协作，可以：
1. ✅ 充分利用 akshare 的数据优势
2. ✅ 进行精确的买入时机判断
3. ✅ 生成完整的分析报告
4. ✅ 灵活支持多种输入方式

