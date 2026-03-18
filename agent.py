"""Wedding AI Agent — Coordinador Inteligente 💍"""

import json
import os
import sys

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from src.models import load_event
from src.coordinator import (
    build_context,
    update_event_status,
    update_person_task,
    undo_last_change,
)
from src.timeline import auto_coordinator

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Error: OPENAI_API_KEY no está configurada. Copia .env.example a .env y agrega tu key.")

llm = ChatOpenAI(model="gpt-4o-mini")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_event_status",
            "description": "Actualiza el estado general de un servicio del evento (flores, catering, musica, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Nombre del servicio a actualizar"},
                    "status": {"type": "string", "description": "Nuevo estado: pendiente, listo, entregado"},
                },
                "required": ["task", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_person_task",
            "description": "Actualiza el estado de una tarea específica asignada a una persona del equipo",
            "parameters": {
                "type": "object",
                "properties": {
                    "person": {"type": "string", "description": "Nombre de la persona"},
                    "task_name": {"type": "string", "description": "Nombre de la tarea"},
                    "status": {"type": "string", "description": "Nuevo estado: pendiente, listo, completada"},
                },
                "required": ["person", "task_name", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "undo_last_change",
            "description": "Deshace el último cambio realizado en el evento",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOL_MAP = {
    "update_event_status": lambda evento, args: update_event_status(evento, args["task"], args["status"]),
    "update_person_task": lambda evento, args: update_person_task(evento, args["person"], args["task_name"], args["status"]),
    "undo_last_change": lambda evento, args: undo_last_change(evento),
}

conversation_history = []


def main():
    print("Wedding AI Agent — Coordinador Inteligente 💍\n")

    while True:
        evento = load_event()

        acciones = auto_coordinator(evento)
        if acciones:
            print("\n🤖 Recomendaciones:")
            for a in acciones:
                print("-", a)
            print()

        try:
            user_input = input("Pregunta: ")
        except (KeyboardInterrupt, EOFError):
            print("\n¡Hasta luego!")
            break

        if user_input.strip().lower() in ("salir", "exit", "quit"):
            break

        if not user_input.strip():
            continue

        context = build_context(evento)
        conversation_history.append(HumanMessage(content=user_input))

        messages = [SystemMessage(content=context)] + conversation_history[-10:]

        try:
            response = llm.invoke(messages, tools=TOOLS)
        except Exception as e:
            print(f"\nError al comunicarse con OpenAI: {e}\n")
            conversation_history.pop()
            continue

        tool_calls = response.additional_kwargs.get("tool_calls", [])

        if tool_calls:
            for tool_call in tool_calls:
                name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])
                handler = TOOL_MAP.get(name)
                if handler:
                    result = handler(evento, args)
                    print(f"\n✅ {result}\n")
                else:
                    print(f"\n⚠️ Herramienta desconocida: {name}\n")
        else:
            print(f"\nRespuesta: {response.content}\n")
            conversation_history.append(response)


if __name__ == "__main__":
    main()
