"""Saved mapping templates — persist & retrieve column mappings per sheet.

When admin maps source columns to Salepro targets, they can save it. Next time
the same Google Sheet is loaded, the saved mapping is auto-applied so admin
doesn't have to drag-drop again.

Backed by Supabase (Postgres). Table schema:

    create table mapping_templates (
        sheet_id    text primary key,
        source_url  text not null,
        column_map  jsonb not null,
        updated_at  timestamptz default now()
    );

Layered design:
- Pydantic models (DTO) — request/response shapes;
- Service functions — `upsert_template`, `find_template`;
- Client factory — `get_supabase`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel
from supabase import Client, create_client

if TYPE_CHECKING:
    from converter.config import Settings


_TABLE = "mapping_templates"


# ─── Pydantic schemas ────────────────────────────────────────────────────
class TemplatePayload(BaseModel):
    """Body for PUT /templates/{sheet_id}."""

    source_url: str
    column_map: dict[str, str]


class TemplateResponse(BaseModel):
    """Body for GET /templates/{sheet_id}."""

    found: bool
    source_url: str | None = None
    column_map: dict[str, str] | None = None


# ─── Client factory ─────────────────────────────────────────────────────
def get_supabase(settings: Settings) -> Client | None:
    """Build a Supabase client, or return None if not configured.

    Returning None lets callers no-op gracefully when SUPABASE_URL/KEY aren't
    set (e.g. local dev without Supabase) instead of crashing.
    """
    if not settings.supabase_url or not settings.supabase_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)


# ─── Service functions ──────────────────────────────────────────────────
def upsert_template(client: Client, sheet_id: str, gid: int, payload: TemplatePayload) -> None:
    """Insert or replace the template row keyed by (sheet_id, gid)."""
    client.table(_TABLE).upsert(
        {
            "sheet_id": sheet_id,
            "gid": gid,
            "source_url": payload.source_url,
            "column_map": payload.column_map,
        }
    ).execute()


def find_template(client: Client, sheet_id: str, gid: int) -> TemplateResponse:
    """Look up template by (sheet_id, gid). Always returns a TemplateResponse."""
    res = (
        client.table(_TABLE)
        .select("source_url, column_map")
        .eq("sheet_id", sheet_id)
        .eq("gid", gid)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return TemplateResponse(found=False)
    row = rows[0]
    return TemplateResponse(
        found=True,
        source_url=row["source_url"],
        column_map=row["column_map"],
    )
