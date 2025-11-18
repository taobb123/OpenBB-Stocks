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