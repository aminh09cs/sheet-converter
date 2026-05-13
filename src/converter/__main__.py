from __future__ import annotations

import uvicorn

from converter.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "converter.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
