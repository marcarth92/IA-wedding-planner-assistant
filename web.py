"""Wedding AI Agent — Web API."""

import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.models import load_event
from src.coordinator import build_context
from src.skills import discover_skills

load_dotenv(override=False)

if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Error: OPENAI_API_KEY no esta configurada.")

app = FastAPI()
llm = ChatOpenAI(model="gpt-4o-mini")
skills = discover_skills()
TOOLS = [s.schema() for s in skills]
TOOL_MAP = {s.name: s for s in skills}

conversation_history = []


class ChatRequest(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html") as f:
        content = f.read()
    return HTMLResponse(content=content, headers={"Cache-Control": "no-store"})


@app.get("/api/evento")
def get_evento():
    return load_event()


@app.post("/chat")
def chat(req: ChatRequest):
    evento = load_event()
    context = build_context(evento)
    conversation_history.append(HumanMessage(content=req.message))

    messages = [SystemMessage(content=context)] + conversation_history[-10:]

    try:
        response = llm.invoke(messages, tools=TOOLS)
    except Exception as e:
        conversation_history.pop()
        return {"response": f"Error: {e}"}

    tool_calls = getattr(response, "tool_calls", [])

    if tool_calls:
        results = []
        for tc in tool_calls:
            skill = TOOL_MAP.get(tc["name"])
            if skill:
                results.append(skill.execute(evento, tc["args"]))
            else:
                results.append(f"Herramienta desconocida: {tc['name']}")
        return {"response": "\n".join(results)}

    conversation_history.append(response)
    return {"response": response.content}
