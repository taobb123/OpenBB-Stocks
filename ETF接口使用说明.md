# ETF 接口使用说明

本文档说明如何使用 `akshare_data_source.py` 中的 ETF 相关接口。

## 📋 接口列表

根据 akshare 官方文档，已实现以下 ETF 相关接口：

| 数据类别 | 方法名 | 主要功能说明 |
| :--- | :--- | :--- |
| **历史行情** | `get_etf_historical()` | 获取ETF日线等历史行情数据 |
| **实时行情** | `get_etf_spot()` | 获取所有ETF的实时行情 |
| **基本信息** | `get_etf_info()` | 获取ETF的规模、净值等基本信息 |
| **基金列表** | `get_fund_list()` | 获取包括ETF在内的所有基金列表及代码 |

## 🔧 使用方法

### 1. 初始化数据源

```python
from akshare_data_source import AKShareDataSource

# 创建数据源实例
akshare_source = AKShareDataSource()
```

### 2. 获取ETF历史行情数据

```python
# 获取沪深300ETF（代码510300）在2024年的日线历史数据，使用前复权
etf_data = akshare_source.get_etf_historical(
    symbol="510300",
    period="daily",
    start_date="20240101",
    end_date="20241120",
    adjust="qfq"
)

# 查看获取到的数据前5行
print(etf_data.head())
```

**参数说明**：
- `symbol`：ETF的代码，**不需要带市场前缀**（如.sh/.sz）
- `period`：数据周期，可以是 `"daily"`（日线）、`"weekly"`（周线）或 `"monthly"`（月线）
- `start_date` & `end_date`：查询的起止日期（格式：YYYYMMDD）
- `adjust`：复权方式，`"qfq"`（前复权）、`"hfq"`（后复权）或 `""`（不复权）

**返回数据**：
- DataFrame，包含日期、开盘、收盘、最高、最低、成交量等字段

### 3. 获取所有ETF的实时行情

```python
# 获取所有ETF的实时行情
etf_spot = akshare_source.get_etf_spot()

# 查看数据
print(etf_spot.head())
print(f"共获取到 {len(etf_spot)} 只ETF的实时行情")
```

**返回数据**：
- DataFrame，包含ETF代码、名称、最新价、涨跌幅、成交量等实时信息

### 4. 获取ETF基本信息

```python
# 获取ETF基本信息（规模、净值等）
etf_info = akshare_source.get_etf_info(symbol="511280")

# 查看信息
print(etf_info)
```

**返回数据**：
- Dict，包含ETF的规模、净值、成立日期等基本信息

### 5. 获取基金列表

```python
# 获取包括ETF在内的所有基金列表
fund_list = akshare_source.get_fund_list()

# 查看数据
print(fund_list.head())
print(f"共获取到 {len(fund_list)} 只基金")
```

**返回数据**：
- DataFrame，包含基金代码、名称等信息

## 💡 实际应用示例

### 示例1：计算ETF动量指标

```python
import pandas as pd
from akshare_data_source import AKShareDataSource

akshare_source = AKShareDataSource()

# 获取多只ETF的历史数据
etf_list = ['510300', '510500', '159915']  # 沪深300ETF, 中证500ETF, 创业板ETF
etf_momentum = {}

for code in etf_list:
    # 获取历史数据
    df = akshare_source.get_etf_historical(
        symbol=code,
        period="daily",
        start_date="20240101",
        end_date="20241120",
        adjust="qfq"
    )
    
    if not df.empty and "收盘" in df.columns:
        # 计算20日收益率作为动量
        df['20d_return'] = df['收盘'].pct_change(20)
        etf_momentum[code] = df['20d_return'].iloc[-1]

# 选择动量最强的ETF
if etf_momentum:
    best_etf = max(etf_momentum, key=etf_momentum.get)
    print(f"当前动量最强的ETF是：{best_etf}，20日收益率为：{etf_momentum[best_etf]:.2%}")
```

### 示例2：筛选高成交量的ETF

```python
from akshare_data_source import AKShareDataSource

akshare_source = AKShareDataSource()

# 获取所有ETF实时行情
etf_spot = akshare_source.get_etf_spot()

if not etf_spot.empty:
    # 筛选成交量大于1000万的ETF
    high_volume_etfs = etf_spot[etf_spot['成交量'] > 10000000]
    
    print(f"成交量大于1000万的ETF共 {len(high_volume_etfs)} 只：")
    print(high_volume_etfs[['代码', '名称', '最新价', '成交量']])
```

### 示例3：比较ETF基本信息

```python
from akshare_data_source import AKShareDataSource

akshare_source = AKShareDataSource()

# 获取多只ETF的基本信息
etf_codes = ['510300', '510500', '159915']
etf_infos = {}

for code in etf_codes:
    info = akshare_source.get_etf_info(symbol=code)
    if info:
        etf_infos[code] = info

# 显示比较结果
for code, info in etf_infos.items():
    print(f"\n{code} 基本信息：")
    for key, value in info.items():
        print(f"  {key}: {value}")
```

## ⚠️ 注意事项

1. **代码格式**：
   - ETF代码不需要带市场前缀（如 `510300` 而不是 `sh510300`）
   - 代码为6位数字字符串

2. **网络环境**：
   - 需要能够访问 akshare 的数据源
   - 某些接口可能需要较长时间，会显示进度条（这是 akshare 库内置功能）

3. **数据更新频率**：
   - 实时行情：实时更新（可能有几分钟延迟）
   - 历史数据：每日更新
   - 基本信息：不定期更新

4. **错误处理**：
   - 所有方法都包含错误处理
   - 失败时返回空 DataFrame 或空字典
   - 会打印错误信息到控制台

5. **进度条说明**：
   - 当调用 akshare 接口获取数据时，akshare 库会自动显示进度条
   - 进度条显示 "Please wait for a moment: XX%"
   - 这是 akshare 库的内置功能，表示正在从网络获取数据
   - 不需要担心，等待进度条完成即可

## 🔗 相关文档

- [akshare 官方文档](https://akshare.readthedocs.io/)
- [报告接口说明.md](./报告接口说明.md) - 查看其他数据接口说明

