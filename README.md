# sheet-converter

Multi-user converter: paste Google Sheets link → map cột nguồn → export về template Salepro (Cao tầng / Thấp tầng).

## Cách chạy

```bash
cp .env.example .env
# Mở .env, paste GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET
# Generate SESSION_SECRET: python -c "import secrets; print(secrets.token_urlsafe(32))"

uv sync
uv run python -m converter
```

Mở http://127.0.0.1:8001 → bấm **Đăng nhập Google** → consent → quay lại tool đã sign-in.

## Cấu trúc project

```
src/converter/
├── config.py    Settings từ .env (pydantic-settings)
├── auth.py      OAuth flow + TokenStore (per-user)
├── sheets.py    Google Sheets API + skip hidden rows
├── schema.py    ProjectType + target column lists
├── app.py       FastAPI factory + routes + view model
├── __main__.py  Entry point: python -m converter
├── templates/   Jinja2 views
└── static/      CSS (design tokens)
```
