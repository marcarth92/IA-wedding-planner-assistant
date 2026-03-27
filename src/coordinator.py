"""Lógica de actualización de estado y contexto para el LLM."""

from datetime import datetime

import pytz

from src import MEXICO_TZ
from src.models import save_event
from src.timeline import analyze_timeline, auto_coordinator

_tz = pytz.timezone(MEXICO_TZ)


def classify_change(old, new):
    if old == new:
        return "sin_cambio"
    if old in ("listo", "entregado", "completada") and new == "pendiente":
        return "correccion"
    if old == "pendiente" and new in ("listo", "entregado", "completada"):
        return "progreso"
    return "actualizacion"


def update_event_status(evento, task, status):
    if task not in evento["estado"]:
        return f"La tarea '{task}' no existe."

    timestamp = datetime.now(_tz).isoformat()
    estado_actual = evento["estado"][task]["estado"]

    evento["estado"][task]["estado"] = status
    evento["estado"][task]["timestamp"] = timestamp

    evento["historial"].append({
        "tarea": task,
        "estado_anterior": estado_actual,
        "estado_nuevo": status,
        "timestamp": timestamp,
        "tipo": classify_change(estado_actual, status),
        "source": "llm",
    })

    save_event(evento)
    return f"{task}: {estado_actual} → {status} ({classify_change(estado_actual, status)})"


def update_person_task(evento, person, task_name, status):
    timestamp = datetime.now(_tz).isoformat()

    for p in evento["equipo"]:
        if p["nombre"].lower() == person.lower():
            for t in p["tareas"]:
                if t["nombre"].lower() == task_name.lower():
                    old = t["estado"]
                    t["estado"] = status
                    t["timestamp"] = timestamp

                    evento["historial"].append({
                        "tarea": task_name,
                        "responsable": person,
                        "estado_anterior": old,
                        "estado_nuevo": status,
                        "timestamp": timestamp,
                        "tipo": classify_change(old, status),
                        "source": "llm",
                    })

                    save_event(evento)
                    return f"{person} - {task_name}: {old} → {status}"

    return "No se encontró la tarea o persona."


def undo_last_change(evento):
    if not evento["historial"]:
        return "Nada que deshacer."

    last = evento["historial"].pop()

    if "responsable" in last:
        for p in evento["equipo"]:
            if p["nombre"] == last["responsable"]:
                for t in p["tareas"]:
                    if t["nombre"] == last["tarea"]:
                        t["estado"] = last["estado_anterior"] or "pendiente"
                        t["timestamp"] = None
    else:
        evento["estado"][last["tarea"]]["estado"] = last["estado_anterior"] or "pendiente"

    save_event(evento)
    return "Último cambio deshecho."


def build_context(evento):
    inteligencia = analyze_timeline(evento)
    acciones = auto_coordinator(evento)

    equipo_text = ""
    for p in evento.get("equipo", []):
        tareas = "\n".join([
            f"- {t['nombre']} ({t['hora']}) [{t['estado']}] "
            f"{'(hecho a las ' + datetime.fromisoformat(t['timestamp']).strftime('%H:%M') + ')' if t['timestamp'] else ''}"
            for t in p.get("tareas", [])
        ])
        equipo_text += f"{p['nombre']} ({p['rol']}):\n{tareas}\n\n"

    proveedores_text = "\n".join([
        f"- {p['servicio']}: {p['empresa']}" for p in evento.get("proveedores", [])
    ]) or "Sin proveedores"

    estado_text = "\n".join([f"{k}: {v['estado']}" for k, v in evento["estado"].items()])
    acciones_text = "\n".join(acciones) or "Sin alertas"

    return f"""Eres un coordinador experto en bodas.

Estado:
{estado_text}

Proveedores:
{proveedores_text}

Equipo (staff del wedding planner):
{equipo_text}

Análisis:
- Atrasadas: {len(inteligencia['atrasadas'])}
- En riesgo: {len(inteligencia['en_riesgo'])}
- Completadas: {inteligencia['completadas']}

Alertas:
{acciones_text}

REGLAS:
- Usa timestamp para responder "a qué hora se hizo"
- Da recomendaciones claras
- NO reasignes tareas automáticamente"""
