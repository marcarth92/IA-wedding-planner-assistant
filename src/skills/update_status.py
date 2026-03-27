"""Skill: actualizar estado de un servicio del evento."""

from src.skills.base import Skill
from src.coordinator import update_event_status


class UpdateEventStatus(Skill):
    name = "update_event_status"
    description = "Actualiza el estado general de un servicio del evento (flores, catering, musica, etc.)"
    parameters = {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "Nombre del servicio a actualizar"},
            "status": {"type": "string", "description": "Nuevo estado: pendiente, listo, entregado"},
        },
        "required": ["task", "status"],
    }

    def execute(self, evento, args):
        return update_event_status(evento, args["task"], args["status"])
