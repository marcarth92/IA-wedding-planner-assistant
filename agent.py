from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json
import pytz
from datetime import datetime

mexico_tz = pytz.timezone("America/Mexico_City")

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini")

# -----------------------------
# LOAD + MIGRATIONS
# -----------------------------

def load_event():
    with open("evento.json", "r") as f:
        data = json.load(f)

    if "historial" not in data:
        data["historial"] = []

    # migrar estado viejo
    if "estado" in data:
        for tarea, valor in data["estado"].items():
            if isinstance(valor, str):
                data["estado"][tarea] = {
                    "estado": valor,
                    "timestamp": None
                }

    # migrar historial
    for h in data.get("historial", []):
        h.setdefault("tipo", "legacy")
        h.setdefault("estado_anterior", None)
        h.setdefault("estado_nuevo", h.get("estado"))

    # asegurar tareas
    for persona in data.get("equipo", []):
        persona.setdefault("tareas", [])
        for t in persona["tareas"]:
            t.setdefault("estado", "pendiente")
            t.setdefault("timestamp", None)
            t.setdefault("depende_de", [])

    return data


def save_event(data):
    with open("evento.json", "w") as f:
        json.dump(data, f, indent=2)


# -----------------------------
# CORE LOGIC
# -----------------------------

def classify_change(old, new):
    if old == new:
        return "sin_cambio"
    if old in ["listo", "entregado"] and new == "pendiente":
        return "correccion"
    if old == "pendiente" and new in ["listo", "entregado"]:
        return "progreso"
    return "actualizacion"


def update_event_status(evento, task, status, source="llm"):
    if task not in evento["estado"]:
        return f"La tarea '{task}' no existe."

    timestamp = datetime.now(mexico_tz).isoformat()
    estado_actual = evento["estado"][task]["estado"]
    tipo = classify_change(estado_actual, status)

    evento["estado"][task]["estado"] = status
    evento["estado"][task]["timestamp"] = timestamp

    evento["historial"].append({
        "tarea": task,
        "estado_anterior": estado_actual,
        "estado_nuevo": status,
        "timestamp": timestamp,
        "tipo": tipo,
        "source": source
    })

    save_event(evento)
    return f"{task}: {estado_actual} → {status} ({tipo})"


def update_person_task(evento, person, task_name, status):
    timestamp = datetime.now(mexico_tz).isoformat()

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
                        "source": "llm"
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
                        t["estado"] = last["estado_anterior"]
                        t["timestamp"] = None
    else:
        evento["estado"][last["tarea"]]["estado"] = last["estado_anterior"]

    save_event(evento)
    return "Último cambio deshecho."


# -----------------------------
# TIMELINE INTELLIGENCE 🧠
# -----------------------------

def analyze_timeline(evento):

    now = datetime.now(mexico_tz)

    atrasadas = []
    en_riesgo = []
    carga_equipo = {}
    completadas = 0

    for persona in evento.get("equipo", []):

        nombre = persona["nombre"]
        tareas = persona.get("tareas", [])

        carga_equipo[nombre] = len([
            t for t in tareas if t["estado"] != "listo"
        ])

        for t in tareas:

            hora_programada = datetime.strptime(
                t["hora"], "%H:%M"
            ).replace(
                year=now.year,
                month=now.month,
                day=now.day,
                tzinfo=mexico_tz
            )

            if t["estado"] == "listo":
                completadas += 1
                continue

            if now > hora_programada:
                atrasadas.append({
                    "persona": nombre,
                    "tarea": t["nombre"],
                    "hora": t["hora"]
                })

            elif (hora_programada - now).total_seconds() < 1800:
                en_riesgo.append({
                    "persona": nombre,
                    "tarea": t["nombre"],
                    "hora": t["hora"]
                })

    return {
        "atrasadas": atrasadas,
        "en_riesgo": en_riesgo,
        "carga_equipo": carga_equipo,
        "completadas": completadas
    }


# -----------------------------
# AUTO COORDINATOR (SIN DELEGAR)
# -----------------------------

def auto_coordinator(evento):

    inteligencia = analyze_timeline(evento)

    acciones = []

    # atrasos
    for a in inteligencia["atrasadas"]:
        acciones.append(
            f"Priorizar {a['persona']} - {a['tarea']} (debía {a['hora']})"
        )

    # riesgos
    for r in inteligencia["en_riesgo"]:
        acciones.append(
            f"Atención: {r['persona']} - {r['tarea']} (a las {r['hora']})"
        )

    # carga
    for persona, carga in inteligencia["carga_equipo"].items():
        if carga >= 4:
            acciones.append(
                f"{persona} tiene alta carga ({carga} tareas pendientes)"
            )

    # dependencias
    for p in evento["equipo"]:
        for t in p["tareas"]:
            for dep in t.get("depende_de", []):
                for p2 in evento["equipo"]:
                    for t2 in p2["tareas"]:
                        if t2["nombre"].lower() == dep.lower():
                            if t2["estado"] != "listo":
                                acciones.append(
                                    f"{t['nombre']} está bloqueada por '{dep}'"
                                )

    return acciones


# -----------------------------
# CONTEXT
# -----------------------------

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

    estado_text = "\n".join([
        f"{k}: {v['estado']}" for k,v in evento["estado"].items()
    ])

    acciones_text = "\n".join(acciones) or "Sin alertas"

    return f"""
Eres un coordinador experto en bodas.

Estado:
{estado_text}

Equipo:
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
- NO reasignes tareas automáticamente
"""


# -----------------------------
# MAIN LOOP
# -----------------------------

tools = [
{
    "type": "function",
    "function": {
        "name": "update_event_status",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "status": {"type": "string"}
            },
            "required": ["task","status"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "update_person_task",
        "parameters": {
            "type": "object",
            "properties": {
                "person": {"type": "string"},
                "task_name": {"type": "string"},
                "status": {"type": "string"}
            },
            "required": ["person","task_name","status"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "undo_last_change",
        "parameters": {"type": "object","properties": {}}
    }
}
]


print("Wedding AI Agent — Coordinador Inteligente 💍\n")

while True:

    evento = load_event()

    # 👇 mostrar recomendaciones automáticas
    acciones = auto_coordinator(evento)
    if acciones:
        print("\n🤖 Recomendaciones:")
        for a in acciones:
            print("-", a)
        print()

    user_input = input("Pregunta: ")

    if user_input.lower() == "salir":
        break

    context = build_context(evento)

    messages = [
        SystemMessage(content=context),
        HumanMessage(content=user_input)
    ]

    response = llm.invoke(messages, tools=tools)

    tool_calls = response.additional_kwargs.get("tool_calls")

    if tool_calls:

        tool_call = tool_calls[0]
        name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])

        if name == "update_event_status":
            result = update_event_status(evento, args["task"], args["status"])

        elif name == "update_person_task":
            result = update_person_task(evento, args["person"], args["task_name"], args["status"])

        elif name == "undo_last_change":
            result = undo_last_change(evento)

        print("\n", result, "\n")

    else:
        print("\nRespuesta:", response.content, "\n")