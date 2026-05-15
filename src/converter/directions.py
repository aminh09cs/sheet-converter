"""Normalize direction (hướng) cell values to canonical short codes."""

from __future__ import annotations

import re

DIRECTION_COLUMN = "Mã hướng"

DIRECTIONS: dict[str, str] = {
    "ĐÔNG": "D",
    "TÂY": "T",
    "NAM": "N",
    "BẮC": "B",
    "TÂY NAM": "TN",
    "TÂY NAM - TÂY BẮC": "TN_TB",
    "TÂY BẮC": "TB",
    "ĐÔNG - ĐÔNG BẮC": "D_DB",
    "NAM - TÂY NAM": "N_TN",
    "ĐÔNG BẮC - TÂY BẮC": "DB_TB",
    "ĐÔNG BẮC - TÂY NAM - ĐÔNG NAM": "DB_TN_DN",
    "ĐÔNG NAM - TÂY NAM": "DN_TN",
    "ĐÔNG NAM - ĐÔNG BẮC": "DN_DB",
    "TÂY BẮC - ĐÔNG BẮC": "TB_DB",
    "TÂY BẮC - TÂY NAM": "TB_TN",
    "TÂY NAM - ĐÔNG BẮC": "TN_DB",
    "ĐÔNG BẮC - NAM": "DB_N",
    "ĐÔNG BẮC - BẮC": "DB_B",
    "TÂY NAM - TÂY": "TN_T",
    "ĐÔNG BẮC - TÂY NAM": "DB_TN",
    "ĐÔNG NAM - TÂY": "DN_T",
    "ĐÔNG NAM - NAM": "DN_N",
    "ĐÔNG NAM - TÂY NAM - ĐÔNG BẮC": "DN_TN_DB",
    "ĐÔNG BẮC - ĐÔNG NAM": "DB_DN",
    "TÂY NAM - ĐÔNG NAM": "TN_DN",
    "TÂY BẮC - BẮC": "TB_B",
    "TÂY BẮC - NAM": "TB_N",
    "TÂY BẮC - ĐÔNG NAM": "TB_DN",
    "ĐÔNG NAM - TÂY BẮC": "DN_TB",
    "TÂY BẮC - TÂY NAM- ĐÔNG BẮC": "TB_TN_DB",
    "ĐÔNG NAM": "DN",
    "ĐÔNG BẮC": "DB",
    "NAM - ĐÔNG": "N_D",
    "NAM - TÂY": "N_T",
    "ĐÔNG - BẮC": "D_B",
    "TÂY - NAM": "T_N",
    "BẮC - TÂY": "B_T",
    "BẮC - TÂY BẮC": "B_TB",
    "BẮC - ĐÔNG BẮC": "B_DB",
    "TÂY NAM - TÂY BẮC - ĐÔNG BẮC": "TN_TB_DB",
    "TÂY BẮC - TÂY NAM- ĐÔNG NAM": "TB_TN_DN",
    "TÂY BẮC - ĐÔNG BẮC - ĐÔNG NAM": "TB_DB_DN",
    "TÂY NAM - ĐÔNG NAM - ĐÔNG BẮC": "TN_DN_DB",
    "ĐÔNG - TÂY": "D_T",
    "TÂY - ĐÔNG": "T_D",
    "BẮC - NAM": "B_N",
    "NAM - BẮC": "N_B",
    "ĐÔNG - ĐÔNG NAM": "D_DN",
    "TÂY - BẮC": "T_B",
    "ĐÔNG - NAM": "D_N",
}


def _strict_key(s: str) -> str:
    """Uppercase + collapse whitespace (newlines, multiple spaces, tabs)."""
    s = re.sub(r"[\n\t\r]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().upper()


def _loose_key(s: str) -> str:
    """Strict key with ALL whitespace removed."""
    return re.sub(r"\s+", "", _strict_key(s))


_STRICT = {_strict_key(k): v for k, v in DIRECTIONS.items()}
_LOOSE = {_loose_key(k): v for k, v in DIRECTIONS.items()}
_SHORT_CODES = {v.strip().upper() for v in DIRECTIONS.values()}


def normalize_direction(value) -> str:
    """Map a free-form direction cell to its canonical short code.

    Resolution order:
      1. Strict-normalized match (case/whitespace insensitive);
      2. Loose-normalized match (also ignores all whitespace);
      3. Input already equals a short code → keep as-is;
      4. Otherwise return raw value unchanged.
    """
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""

    sk = _strict_key(raw)
    if sk in _STRICT:
        return _STRICT[sk]

    lk = _loose_key(raw)
    if lk in _LOOSE:
        return _LOOSE[lk]

    if sk in _SHORT_CODES:
        return raw

    return raw
