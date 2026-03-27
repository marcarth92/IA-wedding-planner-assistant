"""Wedding AI Agent — Web API."""

import json
import os
import sys
import tempfile

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.models import load_event, save_event
from src.coordinator import build_context
from src.skills import discover_skills
from src.excel_parser import parse_excel, create_template

load_dotenv(override=False)

if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Error: OPENAI_API_KEY no esta configurada.")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
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


@app.get("/api/template")
def download_template():
    path = tempfile.mktemp(suffix=".xlsx")
    create_template(path)
    return FileResponse(path, filename="evento_template.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.post("/api/upload")
async def upload_excel(file: UploadFile = File(...)):
    path = tempfile.mktemp(suffix=".xlsx")
    with open(path, "wb") as f:
        f.write(await file.read())
    try:
        data = parse_excel(path)
        save_event(data)
        conversation_history.clear()
        return {"ok": True, "evento": data["evento"]["nombre"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
