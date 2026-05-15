"""Normalize Vietnamese real-estate price values to "tỷ" magnitude (≥ 1B VND).

Sales agents write shorthand like "27", "27.000", "27 tỷ" — all meaning 27 tỷ.
This module converts those shorthand forms to full VND (e.g. "27.000.000.000").
"""

from __future__ import annotations

import re

# Target columns that need price normalization — caller checks membership.
PRICE_COLUMNS = (
    "Giá niêm yết",
    "Giá thanh toán sớm",
    "Giá TTTĐ",
    "Giá vay",
)

_ONE_BILLION = 1_000_000_000

# Strip trailing "tỷ" / "tỉ" / "ty" / "ti" (with optional surrounding space).
_SUFFIX_RE = re.compile(r"\s*(tỷ|tỉ|ty|ti)\s*$", re.IGNORECASE)

# Extract any numeric token (digits with optional period/comma separators).
# Catches both single values and multi-value cells like "VOS: 14.198\nCKTT: 13.536".
_NUMBER_TOKEN_RE = re.compile(r"\d+(?:[.,]\d+)*")


def normalize_price(value) -> str:
    """Convert shorthand prices to full VND (≥ 1 tỷ).

    If the cell contains multiple numeric tokens (e.g. "VOS: 14.198\\nCKTT: 13.536"),
    the LOWEST value is picked and normalized.

    Examples:
        '27' → '27.000.000.000'
        '27.000' → '27.000.000.000'
        '27.456' → '27.456.000.000'
        '27,5' → '27.500.000.000'
        '26 tỷ' → '26.000.000.000'
        '27.000.000.000' → '27.000.000.000'   (already in billions, kept)
        'VOS: 14.198\\nCKTT: 13.536' → '13.536.000.000'  (lowest of [14.198, 13.536])
        'Liên hệ' → 'Liên hệ'                  (no numeric token, kept as-is)
        '' → ''
    """
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""

    cleaned = _SUFFIX_RE.sub("", raw).strip()

    tokens = _NUMBER_TOKEN_RE.findall(cleaned)
    if not tokens:
        return raw

    parsed: list[float] = []
    for tok in tokens:
        n = _parse_vn_number(tok)
        if n is not None and n > 0:
            parsed.append(n)
    if not parsed:
        return raw

    n = min(parsed)
    while n < _ONE_BILLION:
        n *= 1000

    return _format_vn(int(round(n)))


def _parse_vn_number(s: str) -> float | None:
    """Parse a VN-formatted number string.

    Heuristic: last separator (period or comma) with 1-2 digits after it
    is treated as the decimal point; otherwise all separators are thousand
    separators and get stripped.
    """
    last_period = s.rfind(".")
    last_comma = s.rfind(",")
    last_sep_pos = max(last_period, last_comma)

    if last_sep_pos == -1:
        try:
            return float(s)
        except ValueError:
            return None

    digits_after = len(s) - last_sep_pos - 1
    if digits_after in (1, 2):
        # decimal separator
        head = s[:last_sep_pos].replace(".", "").replace(",", "")
        normalized = f"{head}.{s[last_sep_pos + 1 :]}"
    else:
        # all separators are thousand separators
        normalized = s.replace(".", "").replace(",", "")
    try:
        return float(normalized)
    except ValueError:
        return None


def _format_vn(n: int) -> str:
    """27000000000 → '27.000.000.000'"""
    return f"{n:,}".replace(",", ".")
