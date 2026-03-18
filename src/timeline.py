"""Análisis de timeline y coordinación automática."""

from datetime import datetime

import pytz

from src import MEXICO_TZ

_tz = pytz.timezone(MEXICO_TZ)


def _parse_event_date(evento):
    """Extrae la fecha del evento para comparaciones correctas."""
    fecha_str = evento.get("evento", {}).get("fecha", "")
    try:
        return datetime.strptime(fecha_str, "%d %B %Y")
    except ValueError:
        # fallback: usar fecha de hoy
        return datetime.now(_tz)


def analyze_timeline(evento):
    now = datetime.now(_tz)
    event_date = _parse_event_date(evento)

    atrasadas = []
    en_riesgo = []
    carga_equipo = {}
    completadas = 0

    for persona in evento.get("equipo", []):
        nombre = persona["nombre"]
        tareas = persona.get("tareas", [])

        carga_equipo[nombre] = len([t for t in tareas if t["estado"] not in ("listo", "completada")])

        for t in tareas:
            if t["estado"] in ("listo", "completada"):
                completadas += 1
                continue

            hora_programada = datetime.strptime(t["hora"], "%H:%M").replace(
                year=event_date.year,
                month=event_date.month,
                day=event_date.day,
                tzinfo=_tz,
            )

            # solo alertar si estamos en el día del evento
            if now.date() != event_date.date():
                continue

            if now > hora_programada:
                atrasadas.append({"persona": nombre, "tarea": t["nombre"], "hora": t["hora"]})
            elif (hora_programada - now).total_seconds() < 1800:
                en_riesgo.append({"persona": nombre, "tarea": t["nombre"], "hora": t["hora"]})

    return {
        "atrasadas": atrasadas,
        "en_riesgo": en_riesgo,
        "carga_equipo": carga_equipo,
        "completadas": completadas,
    }


def auto_coordinator(evento):
    inteligencia = analyze_timeline(evento)
    acciones = []

    for a in inteligencia["atrasadas"]:
        acciones.append(f"Priorizar {a['persona']} - {a['tarea']} (debía {a['hora']})")

    for r in inteligencia["en_riesgo"]:
        acciones.append(f"Atención: {r['persona']} - {r['tarea']} (a las {r['hora']})")

    for persona, carga in inteligencia["carga_equipo"].items():
        if carga >= 4:
            acciones.append(f"{persona} tiene alta carga ({carga} tareas pendientes)")

    # dependencias bloqueadas
    tareas_por_nombre = {}
    for p in evento.get("equipo", []):
        for t in p["tareas"]:
            tareas_por_nombre[t["nombre"].lower()] = t

    for p in evento.get("equipo", []):
        for t in p["tareas"]:
            for dep in t.get("depende_de", []):
                dep_tarea = tareas_por_nombre.get(dep.lower())
                if dep_tarea and dep_tarea["estado"] not in ("listo", "completada"):
                    acciones.append(f"{t['nombre']} está bloqueada por '{dep}'")

    return acciones
