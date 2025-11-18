## Chinese Formatter Plugin 插件说明

### 插件概述
Chinese Formatter Plugin 通过一个可扩展的映射表，将 OpenBB 导出的英文财务指标即时转换为中文描述，同时保留原始数值，方便中文分析场景。插件以 Python 扩展形式加载，兼容 OpenBB CLI 与 Platform API。

### 功能特色
- 指标中英映射：内置常见指标的翻译表，可按需追加。
- 双语输出：既可返回中文指标，也可配置为「英文(中文)」并列模式。
- 轻量集成：插件只处理字符串映射，不干扰 OpenBB 数据管线。

### 目录结构
```
openbb_platform/extensions/chinese_formatter_plugin/
├─ openbb_chinese_formatter/
│  ├─ __init__.py
│  └─ formatter.py
├─ pyproject.toml
└─ README.md
```

### 核心代码示例
```python
# openbb_chinese_formatter/formatter.py
METRIC_MAP = {
    "P/E Ratio": "市盈率",
    "EPS": "每股收益",
    "Dividend Yield": "股息率",
    "ROE": "净资产收益率",
    "Free Cash Flow": "自由现金流",
}

def to_chinese(metric: str, fallback: bool = True) -> str:
    if fallback:
        return METRIC_MAP.get(metric, metric)
    return METRIC_MAP[metric]

def format_metric(metric: str, value: float | str) -> dict[str, str]:
    zh = to_chinese(metric)
    return {"metric_cn": zh, "metric_en": metric, "value": value}
```

### 插件安装步骤
1. 在 `openbb_platform/extensions/` 新建文件夹 `chinese_formatter_plugin`，按上方目录结构创建文件。
2. 在 `pyproject.toml` 中填写最小依赖（可参照其他扩展，核心是声明 `openbb_chinese_formatter` 包）。
3. 在 `openbb_chinese_formatter/__init__.py` 中导出 `load` 函数，例如：
   ```python
   from .formatter import format_metric

   def load(app):
       app.services["chinese_formatter"] = format_metric
   ```
4. (可选) 在 `openbb_cli/config/extensions.toml` 或对应环境变量里启用该扩展：
   ```
   [extensions]
   chinese_formatter_plugin = "openbb_platform.extensions.chinese_formatter_plugin"
   ```
5. 运行 `poetry install -E chinese_formatter_plugin`（或按项目实际方式安装），随后执行 `openbb --log-level info` 验证日志中出现插件加载记录。

### 使用方式
- 在 CLI 中：调用数据后，通过 `services["chinese_formatter"]` 对返回结果的指标列进行映射。
- 在 Platform API：导入 `format_metric`，对任意分析结果的列名或字段名进行中文化。

### 功能示例
| 英文指标 | 中文指标 |
| --- | --- |
| P/E Ratio | 市盈率 |
| EPS | 每股收益 |
| Dividend Yield | 股息率 |
| ROE | 净资产收益率 |
| Free Cash Flow | 自由现金流 |

> 可在 `METRIC_MAP` 中继续扩展更多专有名词，如 EBITDA、Operating Margin 等，以满足特定行业的中文化需求。

