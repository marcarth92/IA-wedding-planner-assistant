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
# JSON helpers
# -----------------------------

def load_event():

    with open("evento.json", "r") as f:
        data = json.load(f)

    # asegurar historial
    if "historial" not in data:
        data["historial"] = []

    # migrar estado viejo a nuevo formato
    if "estado" in data:

        for tarea, valor in data["estado"].items():

            if isinstance(valor, str):

                data["estado"][tarea] = {
                    "estado": valor,
                    "timestamp": None
                }

    return data


def save_event(data):

    with open("evento.json", "w") as f:
        json.dump(data, f, indent=2)


# -----------------------------
# Tool function
# -----------------------------

def update_event_status(evento, task, status):

    if task not in evento["estado"]:
        return f"La tarea '{task}' no existe."

    timestamp = datetime.now(mexico_tz).isoformat()

    # actualizar estado
    evento["estado"][task]["estado"] = status
    evento["estado"][task]["timestamp"] = timestamp

    # guardar en historial
    evento["historial"].append({
        "tarea": task,
        "estado": status,
        "timestamp": timestamp
    })

    save_event(evento)

    return f"Estado actualizado: {task} -> {status}"


# -----------------------------
# Tools definition
# -----------------------------

tools = [
{
    "type": "function",
    "function": {
        "name": "update_event_status",
        "description": "Actualizar estado de una tarea del evento",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "tarea del evento como flores, catering o musica"
                },
                "status": {
                    "type": "string",
                    "description": "estado nuevo como pendiente, listo o entregado"
                }
            },
            "required": ["task","status"]
        }
    }
}
]


# -----------------------------
# Context builder
# -----------------------------

def build_context(evento):

    equipo_text = "\n".join(
        [f"{p['nombre']} — responsable de {p['rol']}" for p in evento["equipo"]]
    )

    proveedores_text = "\n".join(
        [f"{p['servicio']} — {p['empresa']}" for p in evento["proveedores"]]
    )

    estado_lines = []

    for tarea, info in evento.get("estado", {}).items():

        estado = info["estado"]
        timestamp = info["timestamp"]

        if timestamp:

            try:
                hora = datetime.fromisoformat(timestamp).strftime("%H:%M")
                estado_lines.append(f"{tarea}: {estado} (actualizado a las {hora})")

            except:
                estado_lines.append(f"{tarea}: {estado}")

        else:

            estado_lines.append(f"{tarea}: {estado}")

    estado_text = "\n".join(estado_lines)

    historial = evento.get("historial", [])

    historial_text = "\n".join(
        [f"{h['tarea']} -> {h['estado']} ({h['timestamp']})" for h in historial]
    )

    if historial_text == "":
        historial_text = "Sin actualizaciones aún."

    context = f"""
Eres un asistente que ayuda a coordinar un evento de boda.

Evento: {evento['evento']['nombre']}
Fecha: {evento['evento']['fecha']}
Lugar: {evento['evento']['lugar']}

Equipo:
{equipo_text}

Proveedores:
{proveedores_text}

Estado actual:
{estado_text}

Historial del evento:
{historial_text}

Reglas importantes:

Si el usuario menciona que algo llegó, está listo o fue completado,
usa la herramienta update_event_status para actualizar el estado.

Si el usuario pregunta a qué hora ocurrió algo,
usa el timestamp del estado para responder la hora.

Por ejemplo:
si flores tiene timestamp, esa es la hora en que llegaron.
"""

    return context


print("Wedding AI Agent iniciado. Escribe 'salir' para terminar.\n")

while True:

    evento = load_event()

    user_input = input("Pregunta: ")

    if user_input.lower() == "salir":
        break

    context = build_context(evento)

    messages = [
        SystemMessage(content=context),
        HumanMessage(content=user_input)
    ]

    response = llm.invoke(
        messages,
        tools=tools
    )

    tool_calls = response.additional_kwargs.get("tool_calls")

    if tool_calls:

        tool_call = tool_calls[0]

        args = tool_call["function"]["arguments"]

        args = json.loads(args)

        result = update_event_status(
            evento,
            args["task"],
            args["status"]
        )

        print("\n", result, "\n")

    else:

        print("\nRespuesta:", response.content, "\n")