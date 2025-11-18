# Chinese Formatter Plugin

该插件为 OpenBB 提供英文财务指标到中文描述的快速映射，适用于需要中文界面的报表与分析。核心能力是将指标名称如 `P/E Ratio` 自动转换为 `市盈率`，并保留原始英文值，方便中英文对照。

## 安装步骤
1. 在 OpenBB 根目录执行：
   ```bash
   poetry install -E chinese_formatter_plugin
   ```
2. 在配置文件（如 `openbb_cli/config/extensions.toml`）中启用插件：
   ```toml
   [extensions]
   chinese_formatter_plugin = "openbb_platform.extensions.chinese_formatter_plugin"
   ```
3. 运行 `openbb --log-level info`，确认日志中出现 `chinese_formatter_plugin` 加载记录。

## 使用示例
```python
from openbb_platform import app

formatter = app.services["chinese_formatter"]
formatter("P/E Ratio", 12.3)
# 输出: {"metric_cn": "市盈率", "metric_en": "P/E Ratio", "value": 12.3}
```

| 英文指标        | 中文指标     |
| --------------- | ------------ |
| P/E Ratio       | 市盈率       |
| EPS             | 每股收益     |
| Dividend Yield  | 股息率       |
| ROE             | 净资产收益率 |
| Free Cash Flow  | 自由现金流   |
