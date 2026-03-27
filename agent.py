"""Wedding AI Agent — Coordinador Inteligente"""

import os
import sys

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.models import load_event
from src.coordinator import build_context
from src.skills import discover_skills

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Error: OPENAI_API_KEY no esta configurada. Copia .env.example a .env y agrega tu key.")

llm = ChatOpenAI(model="gpt-4o-mini")

# Auto-discovery de skills
skills = discover_skills()
TOOLS = [s.schema() for s in skills]
TOOL_MAP = {s.name: s for s in skills}

conversation_history = []


def main():
    print("Wedding AI Agent — Coordinador Inteligente\n")

    while True:
        evento = load_event()

        try:
            user_input = input("Pregunta: ")
        except (KeyboardInterrupt, EOFError):
            print("\nHasta luego!")
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

        tool_calls = getattr(response, "tool_calls", [])

        if tool_calls:
            for tool_call in tool_calls:
                skill = TOOL_MAP.get(tool_call["name"])
                if skill:
                    result = skill.execute(evento, tool_call["args"])
                    print(f"\n{result}\n")
                else:
                    print(f"\nHerramienta desconocida: {tool_call['name']}\n")
        else:
            print(f"\nRespuesta: {response.content}\n")
            conversation_history.append(response)


if __name__ == "__main__":
    main()
