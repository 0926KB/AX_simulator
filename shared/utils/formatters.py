"""shared/utils/formatters.py — 숫자/통화 포매터"""
from __future__ import annotations


def fmt_currency(value: float, currency: str = "억원", decimals: int = 2) -> str:
    """1234.5 → '1,234.50 억원'"""
    return f"{value:,.{decimals}f} {currency}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    """0.1234 → '12.3%'"""
    return f"{value * 100:.{decimals}f}%"


def fmt_delta(value: float, decimals: int = 3) -> str:
    """+0.123 / -0.456"""
    return f"{value:+.{decimals}f}"


def fmt_years(value: float) -> str:
    """2.5 → '2.5년'  /  float('inf') → '∞'"""
    if value == float("inf") or value > 99:
        return "∞"
    return f"{value:.1f}년"
