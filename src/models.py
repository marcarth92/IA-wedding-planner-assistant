"""Carga, migración y persistencia del evento."""

import json
from pathlib import Path

from src import DATA_FILE

_DATA_PATH = Path(__file__).resolve().parent.parent / DATA_FILE


def load_event():
    try:
        with open(_DATA_PATH, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise SystemExit(f"Error cargando {DATA_FILE}: {e}")

    data.setdefault("historial", [])

    # migrar estado viejo (str → dict)
    for tarea, valor in data.get("estado", {}).items():
        if isinstance(valor, str):
            data["estado"][tarea] = {"estado": valor, "timestamp": None}

    # migrar historial
    for h in data.get("historial", []):
        h.setdefault("tipo", "legacy")
        h.setdefault("estado_anterior", None)
        h.setdefault("estado_nuevo", h.get("estado"))

    # asegurar tareas del equipo
    for persona in data.get("equipo", []):
        persona.setdefault("tareas", [])
        for t in persona["tareas"]:
            t.setdefault("estado", "pendiente")
            t.setdefault("timestamp", None)
            t.setdefault("depende_de", [])

    return data


def save_event(data):
    try:
        with open(_DATA_PATH, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error guardando {DATA_FILE}: {e}")
