# Sheet-converter


## How to run

uv sync
uv run python -m converter
```

## Project structure

```
src/converter/
├── config.py    Settings from
├── auth.py      OAuth flow + TokenStore (per-user)
├── sheets.py    Google Sheets API + skip hidden rows
├── schema.py    ProjectType + target column lists
├── app.py       FastAPI factory + routes + view model
├── __main__.py  Entry point: python -m converter
├── templates/   Jinja2 views
└── static/      CSS (design tokens)
```
