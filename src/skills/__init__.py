"""Auto-discovery de skills."""

import importlib
import pkgutil

from src.skills.base import Skill


def discover_skills():
    """Descubre y retorna instancias de todos los skills disponibles."""
    skills = []
    package = importlib.import_module("src.skills")

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        if module_name == "base":
            continue
        module = importlib.import_module(f"src.skills.{module_name}")
        for attr in dir(module):
            cls = getattr(module, attr)
            if isinstance(cls, type) and issubclass(cls, Skill) and cls is not Skill:
                skills.append(cls())

    return skills
