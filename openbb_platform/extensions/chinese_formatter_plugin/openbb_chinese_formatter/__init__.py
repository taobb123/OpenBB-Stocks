"""Chinese formatter plugin bootstrap."""

from .formatter import format_metric

__all__ = ["format_metric", "load"]


def load(app) -> None:
    """Register Chinese formatter service inside OpenBB app container."""
    app.services["chinese_formatter"] = format_metric