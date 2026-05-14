import sys
from pathlib import Path

# Vercel runs from project root; add src/ so we can import the converter package.
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Explicit re-export so ruff F401 doesn't strip this — Vercel's @vercel/python
# discovers the ASGI handler by reading a module-level `app` symbol.
from converter.app import app as app  # noqa: E402

__all__ = ["app"]
