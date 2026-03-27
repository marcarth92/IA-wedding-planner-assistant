"""Skill: consultar proveedores del evento."""

from src.skills.base import Skill


class VendorLookup(Skill):
    name = "vendor_lookup"
    description = "Consulta informacion de proveedores del evento. Puede buscar por servicio o listar todos."
    parameters = {
        "type": "object",
        "properties": {
            "servicio": {"type": "string", "description": "Nombre del servicio a buscar (ej: flores, catering). Dejar vacio para listar todos."},
        },
        "required": [],
    }

    def execute(self, evento, args):
        proveedores = evento.get("proveedores", [])
        servicio = args.get("servicio", "").lower()

        if servicio:
            for p in proveedores:
                if p["servicio"].lower() == servicio:
                    estado = evento.get("estado", {}).get(servicio, {})
                    return f"{p['servicio']}: {p['empresa']} (estado: {estado.get('estado', 'sin estado')})"
            return f"No se encontro proveedor para '{servicio}'"

        lines = []
        for p in proveedores:
            estado = evento.get("estado", {}).get(p["servicio"], {})
            lines.append(f"{p['servicio']}: {p['empresa']} (estado: {estado.get('estado', 'sin estado')})")
        return "\n".join(lines)
