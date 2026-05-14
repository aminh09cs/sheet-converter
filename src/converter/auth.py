from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from converter.config import OAUTH_SCOPES, Settings

if TYPE_CHECKING:
    from pathlib import Path

_FLOW_TTL_SECONDS = 600
_pending_flows: dict[str, tuple[str, float]] = {}


def _client_config(settings: Settings) -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.oauth_redirect_uri],
        }
    }


def _cleanup_expired() -> None:
    now = time.time()
    stale = [key for key, (_, ts) in _pending_flows.items() if now - ts > _FLOW_TTL_SECONDS]
    for key in stale:
        _pending_flows.pop(key, None)


def authorization_url(settings: Settings) -> tuple[str, str]:
    flow = Flow.from_client_config(_client_config(settings), scopes=list(OAUTH_SCOPES))
    flow.redirect_uri = settings.oauth_redirect_uri
    url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    _cleanup_expired()
    _pending_flows[state] = (flow.code_verifier or "", time.time())
    return url, state


def exchange_code(settings: Settings, code: str, state: str) -> Credentials:
    entry = _pending_flows.pop(state, None)
    if entry is None:
        raise RuntimeError("OAuth flow đã hết hạn hoặc state không khớp. Vui lòng đăng nhập lại.")
    verifier, _ = entry
    flow = Flow.from_client_config(
        _client_config(settings),
        scopes=list(OAUTH_SCOPES),
        state=state,
    )
    flow.redirect_uri = settings.oauth_redirect_uri
    flow.code_verifier = verifier
    flow.fetch_token(code=code)
    return flow.credentials


def get_user_email(credentials: Credentials) -> str:
    service = build("oauth2", "v2", credentials=credentials, cache_discovery=False)
    info = service.userinfo().get().execute()
    email = info.get("email")
    if not email:
        raise RuntimeError("Không lấy được email từ Google userinfo")
    return email


class TokenStore:
    def __init__(self, path: Path) -> None:
        # Lazy: don't touch filesystem on init — serverless hosts (Vercel) only allow
        # writes to /tmp, so we defer dir creation until the first save() call.
        self.path = path

    def _read(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        raw = self.path.read_text(encoding="utf-8") or "{}"
        return json.loads(raw)

    def _write(self, data: dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    def save(self, email: str, credentials: Credentials) -> None:
        data = self._read()
        data[email] = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes or []),
        }
        self._write(data)

    def load(self, email: str) -> Credentials | None:
        record = self._read().get(email)
        if not record:
            return None
        return Credentials(**record)

    def delete(self, email: str) -> None:
        data = self._read()
        data.pop(email, None)
        self._write(data)
