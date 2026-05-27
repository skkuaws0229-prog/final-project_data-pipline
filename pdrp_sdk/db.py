from __future__ import annotations


def db_status() -> dict[str, object]:
    return {
        "loaded_to_postgres": False,
        "note": "This SDK v0.2 writes CSV/JSON/Markdown artifacts only. DB loading is intentionally left as a separate db_load agent/stage.",
    }
