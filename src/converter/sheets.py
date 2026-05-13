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
                fields="sheets.data(rowData.values.formattedValue,rowMetadata.hiddenByUser)",
            )
            .execute()
        )
    except HttpError as exc:
        raise SheetReadError(_format_api_error(exc)) from exc

    visible = _extract_visible_rows(grid)
    return [cell for cell in detect_header(visible) if cell]


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
    metadata = grid.get("rowMetadata", [])
    rows = grid.get("rowData", [])
    visible: list[list[str]] = []
    for idx, row in enumerate(rows):
        if idx < len(metadata) and metadata[idx].get("hiddenByUser"):
            continue
        cells = [(cell.get("formattedValue") or "") for cell in row.get("values", [])]
        visible.append(cells)
    return visible


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
