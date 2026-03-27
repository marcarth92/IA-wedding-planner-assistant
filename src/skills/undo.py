"""Skill: deshacer el ultimo cambio."""

from src.skills.base import Skill
from src.coordinator import undo_last_change


class UndoLastChange(Skill):
    name = "undo_last_change"
    description = "Deshace el ultimo cambio realizado en el evento"
    parameters = {"type": "object", "properties": {}}

    def execute(self, evento, args):
        return undo_last_change(evento)
