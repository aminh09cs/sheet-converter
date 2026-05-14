from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials

_SHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")
_GID_RE = re.compile(r"[?#&]gid=(\d+)")


class SheetURLError(ValueError):
    pass


class SheetReadError(RuntimeError):
    pass


@dataclass(frozen=True)
class SheetRef:
    sheet_id: str
    gid: int


def parse_url(url: str) -> SheetRef:
    if "docs.google.com" not in url:
        raise SheetURLError("URL phải là docs.google.com")
    id_match = _SHEET_ID_RE.search(url)
    if not id_match:
        raise SheetURLError("Không tìm thấy spreadsheet ID trong URL")
    gid_match = _GID_RE.search(url)
    return SheetRef(
        sheet_id=id_match.group(1),
        gid=int(gid_match.group(1)) if gid_match else 0,
    )


def detect_header(rows: list[list[str]]) -> list[str]:
    for row in rows:
        non_empty = [cell.strip() for cell in row if cell.strip()]
        if len(non_empty) < 4:
            continue
        text_cells = sum(1 for cell in non_empty if not cell[0].isdigit())
        if text_cells >= len(non_empty) * 0.7:
            return [cell.strip() for cell in row]
    for row in rows:
        if any(cell.strip() for cell in row):
            return [cell.strip() for cell in row]
    return []


def _is_header_candidate(row: list[str]) -> bool:
    """Row looks like a header: ≥4 non-empty cells, ≥70% start with non-digit."""
    non_empty = [cell.strip() for cell in row if cell.strip()]
    if len(non_empty) < 4:
        return False
    text_cells = sum(1 for cell in non_empty if not cell[0].isdigit())
    return text_cells >= len(non_empty) * 0.7


def _merge_header_rows(main: list[str], sub: list[str]) -> list[str]:
    """Combine sub-header values into main using nearest non-empty main cell as parent."""
    merged: list[str] = []
    parent = ""
    width = max(len(main), len(sub))
    for i in range(width):
        m = (main[i] if i < len(main) else "").strip()
        s = (sub[i] if i < len(sub) else "").strip()
        if m:
            parent = m
        if s:
            merged.append(f"{parent} - {s}" if parent and parent != s else s)
        else:
            merged.append(m)
    return merged


def split_into_blocks(
    rows: list[list[str]],
) -> list[tuple[list[str], list[list[str]]]]:
    """Detect all (header, data_rows) blocks in a sheet.

    A new block starts at each header-like row. Sub-header rows (sparse + fill
    gaps) are merged into the parent header. Data rows must have ≥50% of the
    current header width filled to count.
    """
    blocks: list[tuple[list[str], list[list[str]]]] = []
    cur_header: list[str] | None = None
    cur_threshold = 0.0
    cur_data: list[list[str]] = []

    i = 0
    n = len(rows)
    while i < n:
        row = rows[i]
        if _is_header_candidate(row):
            if cur_header is not None and cur_data:
                blocks.append((cur_header, cur_data))

            main = row
            next_i = i + 1
            if next_i < n:
                cand = rows[next_i]
                cand_non_empty = sum(1 for c in cand if c.strip())
                main_size = sum(1 for c in main if c.strip())
                fills_gaps = any(
                    j < len(main) and cand[j].strip() and not main[j].strip()
                    for j in range(len(cand))
                )
                if 0 < cand_non_empty < main_size * 0.5 and fills_gaps:
                    main = _merge_header_rows(main, cand)
                    next_i += 1

            cur_header = [c.strip() for c in main if c.strip()]
            cur_threshold = len(cur_header) * 0.5
            cur_data = []
            i = next_i
            continue

        if cur_header is not None:
            non_empty = sum(1 for c in row if c.strip())
            if non_empty >= cur_threshold:
                cur_data.append(row)
        i += 1

    if cur_header is not None and cur_data:
        blocks.append((cur_header, cur_data))

    return blocks


_GRID_FIELDS = (
    "sheets.data("
    "rowData.values(formattedValue,effectiveFormat.backgroundColor,hyperlink),"
    "rowMetadata.hiddenByUser,"
    "columnMetadata.hiddenByUser"
    ")"
)

# Rows tinted with this background mark sold/locked units and must be excluded.
_EXCLUDED_BG_HEX = "#ff0000"


def _bg_hex(cell: dict) -> str | None:
    color = cell.get("effectiveFormat", {}).get("backgroundColor")
    if not color:
        return None
    r = int(round(color.get("red", 0) * 255))
    g = int(round(color.get("green", 0) * 255))
    b = int(round(color.get("blue", 0) * 255))
    return f"#{r:02x}{g:02x}{b:02x}"


def read_source_columns(
    url: str,
    credentials: Credentials,
    *,
    sample_rows: int = 30,
) -> list[str]:
    ref = parse_url(url)
    try:
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        sheet_name = _resolve_sheet_name(service, ref.sheet_id, ref.gid)
        grid = (
            service.spreadsheets()
            .get(
                spreadsheetId=ref.sheet_id,
                ranges=[f"'{sheet_name}'!A1:Z{sample_rows}"],
                includeGridData=True,
                fields=_GRID_FIELDS,
            )
            .execute()
        )
    except HttpError as exc:
        raise SheetReadError(_format_api_error(exc)) from exc

    visible = _extract_visible_rows(grid)
    return [cell for cell in detect_header(visible) if cell]


def read_all_rows(url: str, credentials: Credentials) -> list[list[str]]:
    ref = parse_url(url)
    try:
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        sheet_name = _resolve_sheet_name(service, ref.sheet_id, ref.gid)
        grid = (
            service.spreadsheets()
            .get(
                spreadsheetId=ref.sheet_id,
                ranges=[f"'{sheet_name}'"],
                includeGridData=True,
                fields=_GRID_FIELDS,
            )
            .execute()
        )
    except HttpError as exc:
        raise SheetReadError(_format_api_error(exc)) from exc

    return _extract_visible_rows(grid)


def _resolve_sheet_name(service, sheet_id: str, gid: int) -> str:
    metadata = (
        service.spreadsheets()
        .get(
            spreadsheetId=sheet_id,
            fields="sheets.properties(sheetId,title)",
        )
        .execute()
    )
    for sheet in metadata.get("sheets", []):
        props = sheet["properties"]
        if props["sheetId"] == gid:
            return props["title"]
    raise SheetReadError(f"Không tìm thấy tab có gid={gid} trong spreadsheet")


def _extract_visible_rows(api_result: dict) -> list[list[str]]:
    sheets = api_result.get("sheets", [])
    if not sheets:
        return []
    blocks = sheets[0].get("data", [])
    if not blocks:
        return []
    grid = blocks[0]
    row_meta = grid.get("rowMetadata", [])
    col_meta = grid.get("columnMetadata", [])
    hidden_cols = {i for i, m in enumerate(col_meta) if m.get("hiddenByUser")}
    rows = grid.get("rowData", [])
    visible: list[list[str]] = []
    for idx, row in enumerate(rows):
        if idx < len(row_meta) and row_meta[idx].get("hiddenByUser"):
            continue
        visible_cells = [
            cell for i, cell in enumerate(row.get("values", [])) if i not in hidden_cols
        ]
        if any(_bg_hex(cell) == _EXCLUDED_BG_HEX for cell in visible_cells):
            continue
        cells = []
        for cell in visible_cells:
            value = cell.get("formattedValue") or ""
            url = cell.get("hyperlink")
            cells.append(f"{value} → {url}" if url else value)
        # Trim trailing format-only cells (banding/borders) that have no value
        while cells and not cells[-1].strip():
            cells.pop()
        if not cells:
            continue
        visible.append(cells)
    max_len = max((len(r) for r in visible), default=0)
    return [r + [""] * (max_len - len(r)) for r in visible]


def _format_api_error(exc: HttpError) -> str:
    status = exc.resp.status if exc.resp else "?"
    if status == 403:
        return (
            "Bạn không có quyền đọc sheet này. Kiểm tra account đã đăng nhập có được share không."
        )
    if status == 404:
        return "Sheet không tồn tại hoặc URL sai."
    if status == 401:
        return "Token Google hết hạn. Đăng xuất rồi đăng nhập lại."
    return f"Sheets API lỗi (HTTP {status}): {exc.reason or 'unknown'}"
