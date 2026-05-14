import sys
from pathlib import Path

# Vercel runs from project root; add src/ so we can import the converter package.
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# Vercel's @vercel/python detects ASGI `app` and serves it.
