from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from converter import auth, sheets
from converter.config import Settings, get_settings
from converter.schema import ProjectType, target_columns

PACKAGE_DIR = Path(__file__).resolve().parent
_templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


@dataclass
class IndexView:
    project_type: ProjectType
    target_columns: tuple[str, ...]
    user_email: str | None = None
    link: str = ""
    mapping: dict[str, str] = field(default_factory=dict)
    source_columns: list[str] | None = None
    error: str | None = None
    oauth_configured: bool = True


def _coerce_project_type(raw: str | None) -> ProjectType:
    try:
        return ProjectType(raw) if raw else ProjectType.LOW_RISE
    except ValueError:
        return ProjectType.LOW_RISE


def _extract_mapping(form_items: list[tuple[str, str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for key, value in form_items:
        if key.startswith("map[") and key.endswith("]"):
            mapping[key[4:-1]] = (value or "").strip()
    return mapping


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
        view = IndexView(
            project_type=ProjectType.LOW_RISE,
            target_columns=target_columns(ProjectType.LOW_RISE),
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
        mapping = _extract_mapping([(k, str(v)) for k, v in form.multi_items()])
        credentials = _current_credentials(email)

        source_columns: list[str] | None = None
        error: str | None = None

        if link and not credentials:
            error = "Token Google hết hạn. Đăng xuất rồi đăng nhập lại."
        elif link:
            try:
                source_columns = sheets.read_source_columns(link, credentials)
            except (sheets.SheetURLError, sheets.SheetReadError) as exc:
                error = str(exc)
            except Exception as exc:
                error = f"Lỗi không xác định: {exc}"

        view = IndexView(
            project_type=project_type,
            target_columns=target_columns(project_type),
            user_email=email,
            link=link,
            mapping=mapping,
            source_columns=source_columns,
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

    @app.post("/auth/logout")
    def logout(request: Request):
        request.session.pop("user_email", None)
        return RedirectResponse("/", status_code=303)

    return app


app = create_app()
