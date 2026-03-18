# 💍 IA Wedding Planner Assistant

Agente de IA para coordinar eventos de boda en tiempo real. Usa GPT-4o-mini con tool calling para gestionar tareas, equipo y proveedores.

## Funcionalidades

- Consultar estado de tareas y proveedores
- Actualizar estados por persona o servicio
- Deshacer el último cambio
- Análisis de timeline: tareas atrasadas, en riesgo, carga de equipo
- Detección de dependencias bloqueadas
- Historial completo de cambios con timestamps

## Requisitos

- Python 3.9+
- API key de OpenAI

## Instalación

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

- "¿Cómo va el catering?"
- "Marca como listo el montaje de Ana"
- "Deshaz el último cambio"
- "¿Quién tiene más carga de trabajo?"

Escribe `salir` para terminar.

## Estructura

```
├── agent.py           # Punto de entrada y loop principal
├── src/
│   ├── __init__.py    # Constantes (estados, timezone, archivo de datos)
│   ├── models.py      # Carga/guardado del evento JSON
│   ├── coordinator.py # Lógica de actualización y contexto LLM
│   └── timeline.py    # Análisis de timeline y coordinación automática
├── evento.json        # Datos del evento (estado, equipo, proveedores)
├── requirements.txt   # Dependencias Python
└── .env.example       # Variables de entorno requeridas
```
