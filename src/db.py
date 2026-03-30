"""SQLite database layer."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "evento.db"

def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS evento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            fecha TEXT NOT NULL,
            lugar TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS equipo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL,
            FOREIGN KEY (evento_id) REFERENCES evento(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            persona_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            hora TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            timestamp TEXT,
            depende_de TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (persona_id) REFERENCES equipo(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER NOT NULL,
            servicio TEXT NOT NULL,
            empresa TEXT NOT NULL,
            FOREIGN KEY (evento_id) REFERENCES evento(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS estado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER NOT NULL,
            servicio TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            timestamp TEXT,
            FOREIGN KEY (evento_id) REFERENCES evento(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER NOT NULL,
            tarea TEXT NOT NULL,
            responsable TEXT,
            estado_anterior TEXT,
            estado_nuevo TEXT,
            timestamp TEXT,
            tipo TEXT NOT NULL DEFAULT 'legacy',
            source TEXT,
            FOREIGN KEY (evento_id) REFERENCES evento(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS campos_extra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidad TEXT NOT NULL,
            entidad_id INTEGER NOT NULL,
            campo TEXT NOT NULL,
            valor TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

def get_evento_id(conn):
    row = conn.execute("SELECT id FROM evento ORDER BY id DESC LIMIT 1").fetchone()
    return row["id"] if row else None

def load_event_from_db():
    conn = get_conn()
    eid = get_evento_id(conn)
    if not eid:
        conn.close()
        return None

    ev = conn.execute("SELECT * FROM evento WHERE id=?", (eid,)).fetchone()
    evento = {"nombre": ev["nombre"], "fecha": ev["fecha"], "lugar": ev["lugar"]}

    # Equipo + tareas
    equipo = []
    for p in conn.execute("SELECT * FROM equipo WHERE evento_id=?", (eid,)):
        tareas = []
        for t in conn.execute("SELECT * FROM tareas WHERE persona_id=?", (p["id"],)):
            dep = [d.strip() for d in t["depende_de"].split(",") if d.strip()]
            tareas.append({
                "nombre": t["nombre"], "hora": t["hora"], "estado": t["estado"],
                "timestamp": t["timestamp"], "depende_de": dep,
            })
        extras = _load_extras(conn, "equipo", p["id"])
        equipo.append({"nombre": p["nombre"], "rol": p["rol"], "tareas": tareas, "extras": extras})

    # Proveedores
    proveedores = []
    for pr in conn.execute("SELECT * FROM proveedores WHERE evento_id=?", (eid,)):
        extras = _load_extras(conn, "proveedor", pr["id"])
        proveedores.append({"servicio": pr["servicio"], "empresa": pr["empresa"], "extras": extras})

    # Estado
    estado = {}
    for s in conn.execute("SELECT * FROM estado WHERE evento_id=?", (eid,)):
        estado[s["servicio"]] = {"estado": s["estado"], "timestamp": s["timestamp"]}

    # Historial
    historial = []
    for h in conn.execute("SELECT * FROM historial WHERE evento_id=? ORDER BY id", (eid,)):
        entry = {
            "tarea": h["tarea"], "estado_anterior": h["estado_anterior"],
            "estado_nuevo": h["estado_nuevo"], "timestamp": h["timestamp"],
            "tipo": h["tipo"], "source": h["source"],
        }
        if h["responsable"]:
            entry["responsable"] = h["responsable"]
        historial.append(entry)

    conn.close()
    return {"evento": evento, "equipo": equipo, "proveedores": proveedores, "estado": estado, "historial": historial}

def save_event_to_db(data):
    conn = get_conn()
    # Clear existing data
    old_eid = get_evento_id(conn)
    if old_eid:
        conn.execute("DELETE FROM evento WHERE id=?", (old_eid,))

    ev = data["evento"]
    cur = conn.execute("INSERT INTO evento (nombre, fecha, lugar) VALUES (?,?,?)",
                       (ev["nombre"], ev["fecha"], ev["lugar"]))
    eid = cur.lastrowid

    for p in data.get("equipo", []):
        cur = conn.execute("INSERT INTO equipo (evento_id, nombre, rol) VALUES (?,?,?)",
                           (eid, p["nombre"], p["rol"]))
        pid = cur.lastrowid
        for k, v in p.get("extras", {}).items():
            conn.execute("INSERT INTO campos_extra (entidad, entidad_id, campo, valor) VALUES (?,?,?,?)",
                         ("equipo", pid, k, str(v)))
        for t in p.get("tareas", []):
            dep = ",".join(t.get("depende_de", []))
            conn.execute("INSERT INTO tareas (persona_id, nombre, hora, estado, timestamp, depende_de) VALUES (?,?,?,?,?,?)",
                         (pid, t["nombre"], t["hora"], t.get("estado", "pendiente"), t.get("timestamp"), dep))

    for pr in data.get("proveedores", []):
        cur = conn.execute("INSERT INTO proveedores (evento_id, servicio, empresa) VALUES (?,?,?)",
                           (eid, pr["servicio"], pr["empresa"]))
        prid = cur.lastrowid
        for k, v in pr.get("extras", {}).items():
            conn.execute("INSERT INTO campos_extra (entidad, entidad_id, campo, valor) VALUES (?,?,?,?)",
                         ("proveedor", prid, k, str(v)))

    for servicio, val in data.get("estado", {}).items():
        if isinstance(val, dict):
            conn.execute("INSERT INTO estado (evento_id, servicio, estado, timestamp) VALUES (?,?,?,?)",
                         (eid, servicio, val["estado"], val.get("timestamp")))
        else:
            conn.execute("INSERT INTO estado (evento_id, servicio, estado) VALUES (?,?,?)",
                         (eid, servicio, val))

    for h in data.get("historial", []):
        conn.execute(
            "INSERT INTO historial (evento_id, tarea, responsable, estado_anterior, estado_nuevo, timestamp, tipo, source) VALUES (?,?,?,?,?,?,?,?)",
            (eid, h["tarea"], h.get("responsable"), h.get("estado_anterior"),
             h.get("estado_nuevo"), h.get("timestamp"), h.get("tipo", "legacy"), h.get("source")))

    conn.commit()
    conn.close()

# --- Granular update helpers ---

def update_estado_servicio(servicio, nuevo_estado, timestamp):
    conn = get_conn()
    eid = get_evento_id(conn)
    conn.execute("UPDATE estado SET estado=?, timestamp=? WHERE evento_id=? AND servicio=?",
                 (nuevo_estado, timestamp, eid, servicio))
    conn.commit()
    conn.close()

def update_tarea_persona(persona_nombre, tarea_nombre, nuevo_estado, timestamp):
    conn = get_conn()
    eid = get_evento_id(conn)
    row = conn.execute("SELECT id FROM equipo WHERE evento_id=? AND LOWER(nombre)=LOWER(?)",
                       (eid, persona_nombre)).fetchone()
    if row:
        conn.execute("UPDATE tareas SET estado=?, timestamp=? WHERE persona_id=? AND LOWER(nombre)=LOWER(?)",
                     (nuevo_estado, timestamp, row["id"], tarea_nombre))
    conn.commit()
    conn.close()

def add_historial(entry):
    conn = get_conn()
    eid = get_evento_id(conn)
    conn.execute(
        "INSERT INTO historial (evento_id, tarea, responsable, estado_anterior, estado_nuevo, timestamp, tipo, source) VALUES (?,?,?,?,?,?,?,?)",
        (eid, entry["tarea"], entry.get("responsable"), entry.get("estado_anterior"),
         entry.get("estado_nuevo"), entry.get("timestamp"), entry.get("tipo", "legacy"), entry.get("source")))
    conn.commit()
    conn.close()

def pop_last_historial():
    conn = get_conn()
    eid = get_evento_id(conn)
    row = conn.execute("SELECT * FROM historial WHERE evento_id=? ORDER BY id DESC LIMIT 1", (eid,)).fetchone()
    if row:
        conn.execute("DELETE FROM historial WHERE id=?", (row["id"],))
        conn.commit()
        result = dict(row)
    else:
        result = None
    conn.close()
    return result

def add_persona(nombre, rol, extras=None):
    conn = get_conn()
    eid = get_evento_id(conn)
    cur = conn.execute("INSERT INTO equipo (evento_id, nombre, rol) VALUES (?,?,?)", (eid, nombre, rol))
    pid = cur.lastrowid
    for k, v in (extras or {}).items():
        conn.execute("INSERT INTO campos_extra (entidad, entidad_id, campo, valor) VALUES (?,?,?,?)",
                     ("equipo", pid, k, str(v)))
    conn.commit()
    conn.close()

def delete_persona(nombre):
    conn = get_conn()
    eid = get_evento_id(conn)
    row = conn.execute("SELECT id FROM equipo WHERE evento_id=? AND LOWER(nombre)=LOWER(?)", (eid, nombre)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute("DELETE FROM campos_extra WHERE entidad='equipo' AND entidad_id=?", (row["id"],))
    conn.execute("DELETE FROM equipo WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()
    return True

def add_tarea(persona_nombre, nombre, hora, depende_de=None):
    conn = get_conn()
    eid = get_evento_id(conn)
    row = conn.execute("SELECT id FROM equipo WHERE evento_id=? AND LOWER(nombre)=LOWER(?)",
                       (eid, persona_nombre)).fetchone()
    if not row:
        conn.close()
        return False
    dep = ",".join(depende_de or [])
    conn.execute("INSERT INTO tareas (persona_id, nombre, hora, estado, depende_de) VALUES (?,?,?,?,?)",
                 (row["id"], nombre, hora, "pendiente", dep))
    conn.commit()
    conn.close()
    return True

def delete_tarea(persona_nombre, tarea_nombre):
    conn = get_conn()
    eid = get_evento_id(conn)
    row = conn.execute("SELECT id FROM equipo WHERE evento_id=? AND LOWER(nombre)=LOWER(?)",
                       (eid, persona_nombre)).fetchone()
    if not row:
        conn.close()
        return False
    r = conn.execute("DELETE FROM tareas WHERE persona_id=? AND LOWER(nombre)=LOWER(?)",
                     (row["id"], tarea_nombre))
    conn.commit()
    deleted = r.rowcount > 0
    conn.close()
    return deleted

def add_proveedor(servicio, empresa, extras=None):
    conn = get_conn()
    eid = get_evento_id(conn)
    cur = conn.execute("INSERT INTO proveedores (evento_id, servicio, empresa) VALUES (?,?,?)",
                       (eid, servicio, empresa))
    prid = cur.lastrowid
    for k, v in (extras or {}).items():
        conn.execute("INSERT INTO campos_extra (entidad, entidad_id, campo, valor) VALUES (?,?,?,?)",
                     ("proveedor", prid, k, str(v)))
    conn.execute("INSERT INTO estado (evento_id, servicio, estado) VALUES (?,?,?)",
                 (eid, servicio, "pendiente"))
    conn.commit()
    conn.close()

def delete_proveedor(servicio):
    conn = get_conn()
    eid = get_evento_id(conn)
    row = conn.execute("SELECT id FROM proveedores WHERE evento_id=? AND LOWER(servicio)=LOWER(?)",
                       (eid, servicio)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute("DELETE FROM campos_extra WHERE entidad='proveedor' AND entidad_id=?", (row["id"],))
    conn.execute("DELETE FROM proveedores WHERE id=?", (row["id"],))
    conn.execute("DELETE FROM estado WHERE evento_id=? AND LOWER(servicio)=LOWER(?)", (eid, servicio))
    conn.commit()
    conn.close()
    return True

def _load_extras(conn, entidad, entidad_id):
    extras = {}
    for row in conn.execute("SELECT campo, valor FROM campos_extra WHERE entidad=? AND entidad_id=?",
                            (entidad, entidad_id)):
        extras[row["campo"]] = row["valor"]
    return extras

# Initialize on import
init_db()
