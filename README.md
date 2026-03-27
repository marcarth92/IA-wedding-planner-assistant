# IA Wedding Planner Assistant

AI-powered wedding coordination platform that provides real-time event management through natural language interaction. Built with GPT-4o-mini, FastAPI, and a modular skills architecture.

## Features

- **Natural Language Chat** — Manage your event through conversational AI. Update statuses, query team workload, and get recommendations in plain language.
- **Live Dashboard** — Real-time overview of event progress, service statuses, team tasks, and vendor details across dedicated tabs.
- **Excel Import/Export** — Define your event in a structured Excel template and upload it to generate the event configuration automatically.
- **Auto-Discoverable Skills** — Modular plugin architecture. Add new capabilities without modifying the core agent.
- **Timeline Analysis** — Automatic detection of overdue tasks, at-risk items, blocked dependencies, and team workload imbalance.
- **Change History** — Full audit trail of every status change with timestamps and rollback support.

## Requirements

- Python 3.9+
- OpenAI API key

## Quick Start

```bash
git clone https://github.com/marcarth92/IA-wedding-planner-assistant.git
cd IA-wedding-planner-assistant
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

### Run the Web Application

```bash
uvicorn web:app --host 0.0.0.0 --port 5000
```

Open `http://localhost:5000` in your browser.

### Run with Docker

```bash
docker build -t wedding-planner .
docker run -p 5000:5000 --env-file .env wedding-planner
```

### Run as CLI (legacy)

```bash
python agent.py
```

## Usage

### Web Interface

The application provides four main views:

| Tab | Description |
|-----|-------------|
| **Evento** | Event summary, service statuses, task completion progress, and recent change history |
| **Equipo** | Team members with their assigned roles and task lists including scheduled times and current status |
| **Proveedores** | Vendor directory with service type and current fulfillment status |
| **Chat** | Natural language interface to query and update the event in real time |

### Excel Import

1. Click **Descargar Template** to get the Excel template
2. Fill in the three sheets:

**Evento** — General event information

| Campo | Valor |
|-------|-------|
| Nombre | Boda de X y Y |
| Fecha | 12 Octubre 2026 |
| Lugar | Hacienda Los Olivos |

**Equipo** — Staff members and task assignments

| Persona | Rol | Tarea | Hora | Depende de |
|---------|-----|-------|------|------------|
| Ana | flores | recepcion de flores | 09:00 | |
| Ana | flores | montaje ceremonia | 11:00 | recepcion de flores |

**Proveedores** — Vendor registry

| Servicio | Empresa |
|----------|---------|
| flores | Floreria Luna |
| catering | Banquetes del Valle |

3. Click **Subir Excel** to load the event. All statuses initialize as `pendiente`.

### Chat Examples

- "Como va el catering?"
- "Marca como listo el montaje de Ana"
- "Quien tiene mas carga de trabajo?"
- "Cuales son los proveedores del evento?"
- "Deshaz el ultimo cambio"

## Project Structure

```
├── agent.py                    # CLI entry point (legacy)
├── web.py                      # FastAPI web application
├── static/
│   └── index.html              # Single-page dashboard + chat UI
├── src/
│   ├── __init__.py             # Constants (valid states, timezone, data file)
│   ├── models.py               # Event JSON load/save with schema migration
│   ├── coordinator.py          # Status update logic and LLM context builder
│   ├── timeline.py             # Timeline analysis and automatic coordination
│   ├── excel_parser.py         # Excel-to-JSON parser and template generator
│   └── skills/
│       ├── __init__.py         # Auto-discovery engine
│       ├── base.py             # Skill base class
│       ├── update_status.py    # Update service status
│       ├── manage_team.py      # Update person task status
│       ├── vendor_lookup.py    # Query vendor information
│       └── undo.py             # Rollback last change
├── evento.json                 # Event data (runtime state)
├── Dockerfile                  # Container configuration
├── requirements.txt            # Python dependencies
└── .env.example                # Environment variables template
```

## Skills Architecture

Each skill is a self-contained module in `src/skills/` that the agent discovers automatically at startup. To add a new capability:

```python
# src/skills/my_skill.py
from src.skills.base import Skill

class MySkill(Skill):
    name = "my_skill"
    description = "Description for the LLM"
    parameters = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
        },
        "required": ["param1"],
    }

    def execute(self, evento, args):
        return "result"
```

No changes to `web.py` or `agent.py` required. The skill is available to the LLM immediately.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the web UI |
| `GET` | `/api/evento` | Returns current event data as JSON |
| `GET` | `/api/template` | Downloads the Excel template |
| `POST` | `/api/upload` | Uploads an Excel file to replace the current event |
| `POST` | `/chat` | Sends a message to the AI agent and returns the response |

## License

MIT
