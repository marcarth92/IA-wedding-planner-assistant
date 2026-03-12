from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini")

# -----------------------------
# JSON helpers
# -----------------------------

def load_event():
    with open("evento.json", "r") as f:
        return json.load(f)

def save_event(data):
    with open("evento.json", "w") as f:
        json.dump(data, f, indent=2)

# -----------------------------
# Tool function
# -----------------------------

def update_event_status(evento, task, status):

    evento["estado"][task] = status
    save_event(evento)

    return f"Estado actualizado: {task} -> {status}"

# -----------------------------
# Tools definition (OpenAI format)
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

    estado_text = "\n".join(
        [f"{k}: {v}" for k,v in evento["estado"].items()]
    )

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

Si el usuario menciona que algo llegó, está listo o fue completado,
usa la herramienta update_event_status para actualizar el estado.
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

    # revisar si el modelo quiere usar una tool
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
