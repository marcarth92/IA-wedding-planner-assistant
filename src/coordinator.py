"""Logica de actualizacion de estado y contexto para el LLM."""

from datetime import datetime

import pytz

from src import MEXICO_TZ
from src.db import (
    update_estado_servicio, update_tarea_persona,
    add_historial, pop_last_historial, load_event_from_db,
)
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

    update_estado_servicio(task, status, timestamp)
    add_historial({
        "tarea": task,
        "estado_anterior": estado_actual,
        "estado_nuevo": status,
        "timestamp": timestamp,
        "tipo": classify_change(estado_actual, status),
        "source": "llm",
    })

    return f"{task}: {estado_actual} -> {status} ({classify_change(estado_actual, status)})"


def update_person_task(evento, person, task_name, status):
    timestamp = datetime.now(_tz).isoformat()

    for p in evento["equipo"]:
        if p["nombre"].lower() == person.lower():
            for t in p["tareas"]:
                if t["nombre"].lower() == task_name.lower():
                    old = t["estado"]
                    update_tarea_persona(person, task_name, status, timestamp)
                    add_historial({
                        "tarea": task_name,
                        "responsable": person,
                        "estado_anterior": old,
                        "estado_nuevo": status,
                        "timestamp": timestamp,
                        "tipo": classify_change(old, status),
                        "source": "llm",
                    })
                    return f"{person} - {task_name}: {old} -> {status}"

    return "No se encontro la tarea o persona."


def undo_last_change(evento):
    last = pop_last_historial()
    if not last:
        return "Nada que deshacer."

    if last.get("responsable"):
        update_tarea_persona(last["responsable"], last["tarea"],
                             last["estado_anterior"] or "pendiente", None)
    else:
        update_estado_servicio(last["tarea"], last["estado_anterior"] or "pendiente", None)

    return "Ultimo cambio deshecho."


def build_context(evento):
    inteligencia = analyze_timeline(evento)
    acciones = auto_coordinator(evento)

    equipo_text = ""
    for p in evento.get("equipo", []):
        extras = p.get("extras", {})
        extras_str = ", ".join(f"{k}: {v}" for k, v in extras.items()) if extras else ""
        tareas = "\n".join([
            f"- {t['nombre']} ({t['hora']}) [{t['estado']}] "
            f"{'(hecho a las ' + datetime.fromisoformat(t['timestamp']).strftime('%H:%M') + ')' if t['timestamp'] else ''}"
            for t in p.get("tareas", [])
        ])
        equipo_text += f"{p['nombre']} ({p['rol']}){' [' + extras_str + ']' if extras_str else ''}:\n{tareas}\n\n"

    proveedores_text = "\n".join([
        f"- {pr['servicio']}: {pr['empresa']}" +
        (" (" + ", ".join(f"{k}: {v}" for k, v in pr.get("extras", {}).items()) + ")" if pr.get("extras") else "")
        for pr in evento.get("proveedores", [])
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

Analisis:
- Atrasadas: {len(inteligencia['atrasadas'])}
- En riesgo: {len(inteligencia['en_riesgo'])}
- Completadas: {inteligencia['completadas']}

Alertas:
{acciones_text}

REGLAS:
- Usa timestamp para responder "a que hora se hizo"
- Da recomendaciones claras
- NO reasignes tareas automaticamente"""
