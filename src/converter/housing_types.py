"""Normalize housing-type cell values to the canonical short codes.

Sales agents write housing types in many variants (case, spacing, punctuation).
This module maps them back to the short codes (e.g. "ĐƠN LẬP" → "DL") used by Salepro.
"""

from __future__ import annotations

import re

from converter.schema import ProjectType

# Target column where this normalization is applied.
HOUSING_TYPE_COLUMN = "Mã loại hình căn hộ"

HIGH_RISE_TYPES: dict[str, str] = {
    "1 PHÒNG NGỦ": "1BR",
    "1 PHÒNG NGỦ +": "1BR+",
    "2 PHÒNG NGỦ +": "2BR+",
    "3 PHÒNG NGỦ": "3BR",
    "2 PHÒNG NGỦ": "2BR",
    "STUDIO": "ST",
    "2 PHÒNG NGỦ + 1 P.ĐA NĂNG": "2BR+1MR",
    "DUPLEX": "DUPLEX",
    "SHOP CHÂN ĐẾ": "SHCD",
    "2 PHÒNG NGỦ + 1 P.ĐA NĂNG + 2VS": "2BR+1MR+2WC",
    "DUAL KEY": "DUALKEY",
    "PENHOUSE": "PENHOUSE",
    "1 PHÒNG NGỦ + 1 P.ĐA NĂNG": "1BR+1MR",
    "4 PHÒNG NGỦ": "4BR",
    "2 PHÒNG NGỦ + 1 P.ĐA NĂNG + 1VS": "2BR+1MR+1WC",
    "CHỖ ĐỂ XE": "PKG",
    "CONDOTEL": "CD",
    "SIMPLEX": "SIMPLEX",
    "3 PHÒNG NGỦ +": "3BR+",
    "TRIPLEX": "TRIPLEX",
    "3 PHÒNG NGỦ (CÓ SÂN VƯỜN)": "3BR+SV",
    "3 PHÒNG NGỦ (DUAL KEY)": "3BR+DK",
    "4 PHÒNG NGỦ (CÓ SÂN VƯỜN)": "4BR+SV",
    "3 PHÒNG NGỦ LỚN": "3BRL",
    "4 PHÒNG NGỦ +": "4BR+",
    "4 PHÒNG NGỦ (DUAL KEY)": "4BR+DK",
    "2,5 PHÒNG NGỦ": "2,5BR",
    "3,5 PHÒNG NGỦ": "3,5BR",
    "GARDEN HOUSE": "GH",
    "Panorama": "PAN",
    "Hyper Panorama": "HPAN",
    "S-Hyper Panorama": "S-HPAN",
    "TMDV": "TMDV CD",
    "PENHOUSE DUPLEX": "PHDL",
    "STUDIO+": "ST+",
    "RISA": "RS",
    "LOFT 1 PHÒNG NGỦ": "LOFT1",
    "LOFT 2 PHÒNG NGỦ": "LOFT2",
    "LOFT 2 PHÒNG NGỦ + 2 VS": "LOFT2W",
    "LOFT 3 PHÒNG NGỦ": "LOFT3",
    "3BR-LIFT": "3BR_LIFT",
    "4BR_LIFT": "4BR_LIFT",
    "2BR_LIFT": "2BR_LIFT",
    "5 PHÒNG NGỦ": "5BR",
    "7 PHÒNG NGỦ": "7BR",
    "9 PHÒNG NGỦ": "9BR",
    "6 PHÒNG NGỦ": "6BR",
}

LOW_RISE_TYPES: dict[str, str] = {
    "ĐƠN LẬP": "DL",
    "SONG LẬP": "SL",
    "TỨ LẬP": "TL",
    "LIỀN KỀ": "LK",
    "LIỀN KỀ GÓC": "LKG",
    "LIỀN KỀ ÁP GÓC": "LKAG",
    "SHOPHOUSE": "SH",
    "LIỀN KỀ XẺ KHE": "LKXK",
    "LIỀN KỀ ÁP XẺ KHE": "LKAXK",
    "SONG LẬP VIP": "SLV",
    "SONG LẬP GÓC": "SLG",
    "BIỆT THỰ TỨ LẬP": "BTTL",
    "BIỆT THỰ SONG LẬP": "BTSL",
    "TAM LẬP GÓC": "TALG",
    "ĐƠN LẬP GÓC": "DLG",
    "SHOPHOUSE VIP": "SHV",
    "SHOPHOUSE XẺ KHE": "SHXK",
    "SHOPHOUSE GÓC": "SHG",
    "DINH THỰ ĐƠN LẬP": "DTDL",
    "DINH THỰ": "DT",
    "TMDV": "TMDV",
    "SHOPHOUSE ÁP GÓC": "SHAG",
    "TAM LẬP": "TAL",
    "SHOPHOUSE ÁP XẺ KHE": "SHAXK",
    "ĐẤT NỀN": "DN",
    "River Pool": "RP",
    "Pool Townhouse": "PT",
    "Infinity Pool": "IP",
    "SHOP CHÂN ĐẾ": "SCD",
    "VILLA": "VL",
    "BIỆT THỰ ĐƠN LẬP": "BTĐL",
    "BOUTIQUE VILLA": "BOUTIQUE VILLA",
    "BOUTIQUE": "BOUTIQUE",
    "GARDEN VILLA": "GV",
    "DỊCH VỤ DU LỊCH": "DVDL",
    "ĐỘC BẢN": "DB",
    "SHOPHOUSE KHỐI ĐẾ": "SHKĐ",
    "SHOPHOUSE 2 MẶT TIỀN": "SH2MT",
    "CĂN HỘ": "CH",
    "Deluxe Villas": "DV",
    "Town Villas": "TV",
}


def _strict_key(s: str) -> str:
    """Uppercase + collapse whitespace + normalize decimal separator (period→comma)."""
    s = re.sub(r"[\n\t\r]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    s = s.strip().upper()
    # In VN convention "2,5" and "2.5" both mean two-point-five; normalize so they collide.
    s = re.sub(r"(\d)\.(\d)", r"\1,\2", s)
    return s


def _loose_key(s: str) -> str:
    """Strict key with ALL whitespace removed (catches missing-space typos)."""
    return re.sub(r"\s+", "", _strict_key(s))


def _build_tables(table: dict[str, str]) -> tuple[dict[str, str], dict[str, str], set[str]]:
    strict = {_strict_key(k): v for k, v in table.items()}
    loose = {_loose_key(k): v for k, v in table.items()}
    short_codes = {v.strip().upper() for v in table.values()}
    return strict, loose, short_codes


_HIGH_RISE_LOOKUP = _build_tables(HIGH_RISE_TYPES)
_LOW_RISE_LOOKUP = _build_tables(LOW_RISE_TYPES)


def normalize_housing_type(value, project_type: ProjectType) -> str:
    """Map a free-form housing-type cell to its canonical short code.

    Resolution order:
      1. Strict-normalized match (case/whitespace/decimal-separator insensitive);
      2. Loose-normalized match (also ignores all whitespace, e.g. "ĐƠNLẬP");
      3. Input already equals a short code → keep as-is;
      4. Otherwise return raw value unchanged.
    """
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""

    strict, loose, short_codes = (
        _HIGH_RISE_LOOKUP if project_type == ProjectType.HIGH_RISE else _LOW_RISE_LOOKUP
    )

    strict_key = _strict_key(raw)
    if strict_key in strict:
        return strict[strict_key]

    loose_key = _loose_key(raw)
    if loose_key in loose:
        return loose[loose_key]

    if strict_key in short_codes:
        return raw

    return raw
