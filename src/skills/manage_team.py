"""Skill: actualizar tarea de una persona del equipo."""

from src.skills.base import Skill
from src.coordinator import update_person_task


class UpdatePersonTask(Skill):
    name = "update_person_task"
    description = "Actualiza el estado de una tarea especifica asignada a una persona del equipo"
    parameters = {
        "type": "object",
        "properties": {
            "person": {"type": "string", "description": "Nombre de la persona"},
            "task_name": {"type": "string", "description": "Nombre de la tarea"},
            "status": {"type": "string", "description": "Nuevo estado: pendiente, listo, completada"},
        },
        "required": ["person", "task_name", "status"],
    }

    def execute(self, evento, args):
        return update_person_task(evento, args["person"], args["task_name"], args["status"])
