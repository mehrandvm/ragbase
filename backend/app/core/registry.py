# backend/app/core/registry.py
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings

REGISTRY_PATH = Path(settings.chroma_path) / "kb_registry.json"


def _read() -> dict:
    if not REGISTRY_PATH.exists():
        return {}
    return json.loads(REGISTRY_PATH.read_text())


def _write(data: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(data, indent=2, default=str))


def create_kb(name: str, description: Optional[str] = None) -> dict:
    data = _read()
    kb   = {
        "id":          str(uuid.uuid4())[:8],
        "name":        name,
        "description": description,
        "created_at":  datetime.now().isoformat(),
    }
    data[kb["id"]] = kb
    _write(data)
    return kb


def list_kbs() -> list:
    return list(_read().values())


def get_kb(kb_id: str) -> Optional[dict]:
    return _read().get(kb_id)


def delete_kb(kb_id: str) -> bool:
    data = _read()
    if kb_id not in data:
        return False
    del data[kb_id]
    _write(data)
    return True


# Stores KB metadata as a flat JSON file next to the Chroma store.
# Each KB has an 8-char UUID used as both the registry key and Chroma collection name.
# No database needed — the registry is the source of truth for names/descriptions,
# Chroma is the source of truth for vectors.