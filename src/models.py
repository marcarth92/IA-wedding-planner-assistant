"""Carga, migración y persistencia del evento."""

import json
from pathlib import Path

from src.db import load_event_from_db, save_event_to_db

_JSON_PATH = Path(__file__).resolve().parent.parent / "evento.json"


def _migrate_json_if_needed():
    """One-time migration: import evento.json into SQLite if DB is empty."""
    if not _JSON_PATH.exists():
        return
    data = load_event_from_db()
    if data:
        return  # DB already has data
    try:
        with open(_JSON_PATH, "r") as f:
            json_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return

    # Apply same migrations as before
    json_data.setdefault("historial", [])
    for tarea, valor in json_data.get("estado", {}).items():
        if isinstance(valor, str):
            json_data["estado"][tarea] = {"estado": valor, "timestamp": None}
    for h in json_data.get("historial", []):
        h.setdefault("tipo", "legacy")
        h.setdefault("estado_anterior", None)
        h.setdefault("estado_nuevo", h.get("estado"))
    for persona in json_data.get("equipo", []):
        persona.setdefault("tareas", [])
        persona.setdefault("extras", {})
        for t in persona["tareas"]:
            t.setdefault("estado", "pendiente")
            t.setdefault("timestamp", None)
            t.setdefault("depende_de", [])
    for prov in json_data.get("proveedores", []):
        prov.setdefault("extras", {})

    save_event_to_db(json_data)
    # Rename old file so migration doesn't run again
    _JSON_PATH.rename(_JSON_PATH.with_suffix(".json.bak"))


# Run migration on first import
_migrate_json_if_needed()


def load_event():
    data = load_event_from_db()
    if not data:
        raise SystemExit("Error: No hay evento en la base de datos. Sube un Excel o crea uno.")
    return data


def save_event(data):
    save_event_to_db(data)
