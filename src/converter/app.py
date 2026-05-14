from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from converter import auth, sheets
from converter.config import Settings, get_settings
from converter.schema import ProjectType, target_columns

PACKAGE_DIR = Path(__file__).resolve().parent
_templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


@dataclass
class BlockView:
    index: int
    header: list[str]
    data_count: int
    mapping: dict[str, str] = field(default_factory=dict)


@dataclass
class IndexView:
    project_type: ProjectType
    target_columns: tuple[str, ...]
    user_email: str | None = None
    link: str = ""
    blocks: list[BlockView] = field(default_factory=list)
    error: str | None = None
    oauth_configured: bool = True


def _coerce_project_type(raw: str | None) -> ProjectType:
    try:
        return ProjectType(raw) if raw else ProjectType.LOW_RISE
    except ValueError:
        return ProjectType.LOW_RISE


_MAP_RE = re.compile(r"^map\[(\d+)\]\[(.+)\]$")


def _extract_mappings(form_items: list[tuple[str, str]]) -> dict[int, dict[str, str]]:
    mappings: dict[int, dict[str, str]] = {}
    for key, value in form_items:
        match = _MAP_RE.match(key)
        if match:
            idx = int(match.group(1))
            target = match.group(2)
            mappings.setdefault(idx, {})[target] = (value or "").strip()
    return mappings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    token_store = auth.TokenStore(settings.token_store_path)

    app = FastAPI(title="Sheet Converter")
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
    app.mount(
        "/static",
        StaticFiles(directory=str(PACKAGE_DIR / "static")),
        name="static",
    )

    def _current_email(request: Request) -> str | None:
        return request.session.get("user_email")

    def _current_credentials(email: str | None):
        return token_store.load(email) if email else None

    def _render(request: Request, view: IndexView) -> HTMLResponse:
        return _templates.TemplateResponse(request, "index.html", {"view": view})

    def _render_login(request: Request) -> HTMLResponse:
        return _templates.TemplateResponse(
            request,
            "login.html",
            {"oauth_configured": settings.is_oauth_configured},
        )

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        email = _current_email(request)
        if not email:
            return _render_login(request)
        project_type = _coerce_project_type(request.query_params.get("project_type"))
        view = IndexView(
            project_type=project_type,
            target_columns=target_columns(project_type),
            user_email=email,
            oauth_configured=settings.is_oauth_configured,
        )
        return _render(request, view)

    @app.post("/load", response_class=HTMLResponse)
    async def load(request: Request) -> HTMLResponse:
        email = _current_email(request)
        if not email:
            return _render_login(request)

        form = await request.form()
        link = (form.get("link") or "").strip()
        project_type = _coerce_project_type(form.get("project_type"))
        mappings = _extract_mappings([(k, str(v)) for k, v in form.multi_items()])
        credentials = _current_credentials(email)

        blocks_view: list[BlockView] = []
        error: str | None = None

        if link and not credentials:
            error = "Token Google hết hạn. Đăng xuất rồi đăng nhập lại."
        elif link:
            try:
                all_rows = sheets.read_all_rows(link, credentials)
                raw_blocks = sheets.split_into_blocks(all_rows)
                total_data = sum(len(d) for _, d in raw_blocks)
                print(f"=== {len(raw_blocks)} block, {total_data} data rows ===")
                for block_idx, (header, data) in enumerate(raw_blocks, start=1):
                    print(f"--- Block {block_idx}: Header ({len(header)} cột) ---")
                    print(header)
                    print(f"--- Block {block_idx}: Data ({len(data)} dòng) ---")
                    for idx, row in enumerate(data, start=1):
                        print(f"  [{idx}] {row}")
                    blocks_view.append(
                        BlockView(
                            index=block_idx,
                            header=header,
                            data_count=len(data),
                            mapping=mappings.get(block_idx, {}),
                        )
                    )
            except (sheets.SheetURLError, sheets.SheetReadError) as exc:
                error = str(exc)
            except Exception as exc:
                error = f"Lỗi không xác định: {exc}"

        view = IndexView(
            project_type=project_type,
            target_columns=target_columns(project_type),
            user_email=email,
            link=link,
            blocks=blocks_view,
            error=error,
            oauth_configured=settings.is_oauth_configured,
        )
        return _render(request, view)

    @app.get("/auth/login", response_model=None)
    def login(request: Request):
        if not settings.is_oauth_configured:
            return HTMLResponse(
                "Server chưa cấu hình GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET trong .env",
                status_code=500,
            )
        url, _state = auth.authorization_url(settings)
        return RedirectResponse(url)

    @app.get("/auth/callback", response_model=None)
    def callback(request: Request):
        code = request.query_params.get("code")
        state = request.query_params.get("state") or ""
        if not code:
            return HTMLResponse("Thiếu code từ Google OAuth", status_code=400)
        try:
            credentials = auth.exchange_code(settings, code, state)
            email = auth.get_user_email(credentials)
            token_store.save(email, credentials)
            request.session["user_email"] = email
        except Exception as exc:
            return HTMLResponse(f"OAuth error: {exc}", status_code=500)
        return RedirectResponse("/", status_code=303)

    @app.post("/export")
    async def export(request: Request) -> Response:
        email = _current_email(request)
        if not email:
            return Response("Chưa đăng nhập", status_code=401)

        form = await request.form()
        link = (form.get("link") or "").strip()
        block = int(request.query_params.get("block", "1") or 1)
        project_type = _coerce_project_type(form.get("project_type"))
        mappings = _extract_mappings([(k, str(v)) for k, v in form.multi_items()])
        credentials = _current_credentials(email)

        if not link:
            return Response("Thiếu link", status_code=400)
        if not credentials:
            return Response("Token Google hết hạn. Đăng xuất rồi đăng nhập lại.", status_code=401)

        try:
            all_rows = sheets.read_all_rows(link, credentials)
            raw_blocks = sheets.split_into_blocks(all_rows)
        except (sheets.SheetURLError, sheets.SheetReadError) as exc:
            return Response(str(exc), status_code=400)

        if block < 1 or block > len(raw_blocks):
            return Response(f"Block {block} không tồn tại", status_code=400)

        header, data = raw_blocks[block - 1]
        block_mapping = mappings.get(block, {})
        targets = target_columns(project_type)

        xlsx_bytes = sheets.build_xlsx(header, data, targets, block_mapping)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = "cao_tang" if project_type == ProjectType.HIGH_RISE else "thap_tang"
        filename = f"salepro_{suffix}_block{block}_{timestamp}.xlsx"

        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/auth/logout")
    def logout(request: Request):
        request.session.pop("user_email", None)
        return RedirectResponse("/", status_code=303)

    return app


app = create_app()
