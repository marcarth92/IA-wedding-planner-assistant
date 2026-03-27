# IA Wedding Planner Assistant

Agente de IA para coordinar eventos de boda en tiempo real. Usa GPT-4o-mini con tool calling y una arquitectura de skills auto-descubribles.

## Funcionalidades

- Consultar estado de tareas y proveedores
- Actualizar estados por persona o servicio
- Deshacer el ultimo cambio
- Analisis de timeline: tareas atrasadas, en riesgo, carga de equipo
- Deteccion de dependencias bloqueadas
- Historial completo de cambios con timestamps

## Requisitos

- Python 3.9+
- API key de OpenAI

## Instalacion

```bash
git clone https://github.com/marcarth92/IA-wedding-planner-assistant.git
cd IA-wedding-planner-assistant
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edita .env y agrega tu OPENAI_API_KEY
```

## Uso

```bash
python agent.py
```

Escribe tus preguntas o instrucciones en lenguaje natural:

- "Como va el catering?"
- "Marca como listo el montaje de Ana"
- "Deshaz el ultimo cambio"
- "Quien tiene mas carga de trabajo?"

Escribe `salir` para terminar.

## Estructura

```
├── agent.py                # Punto de entrada y loop principal
├── src/
│   ├── __init__.py         # Constantes (estados, timezone, archivo de datos)
│   ├── models.py           # Carga/guardado del evento JSON
│   ├── coordinator.py      # Logica de actualizacion y contexto LLM
│   ├── timeline.py         # Analisis de timeline y coordinacion automatica
│   └── skills/
│       ├── __init__.py     # Auto-discovery de skills
│       ├── base.py         # Clase base Skill (schema + execute)
│       ├── update_status.py  # Actualizar estado de servicios
│       ├── manage_team.py    # Actualizar tareas por persona
│       └── undo.py           # Deshacer ultimo cambio
├── evento.json             # Datos del evento (estado, equipo, proveedores)
├── requirements.txt        # Dependencias Python
└── .env.example            # Variables de entorno requeridas
```

## Arquitectura de Skills

Cada skill es un modulo independiente en `src/skills/` que hereda de `Skill` y define:

- `name` — nombre de la funcion para el LLM
- `description` — descripcion para el LLM
- `parameters` — schema JSON de parametros
- `execute(evento, args)` — logica de ejecucion

El agente descubre todos los skills automaticamente al iniciar. Para agregar uno nuevo, solo crea un archivo en `src/skills/` con una clase que herede de `Skill`.

```python
from src.skills.base import Skill

class MiNuevoSkill(Skill):
    name = "mi_skill"
    description = "Descripcion para el LLM"
    parameters = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
        },
        "required": ["param1"],
    }

    def execute(self, evento, args):
        # logica aqui
        return "resultado"
```
