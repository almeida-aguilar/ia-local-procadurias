# back/sqlite/insertar.py
import json
import os
import sqlite3

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(_BASE_DIR, "..", "..", "sueltos.db"))


def insertar_suelto(tipo, nombre, descripcion="", metadata=None):
    """Agrega un documento suelto a SQLite. Devuelve el ID insertado."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Crear tabla si no existe (útil en primera ejecución)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documentos_sueltos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo            TEXT CHECK(tipo IN ('caso', 'perfil', 'expediente')),
            nombre          TEXT NOT NULL,
            descripcion     TEXT,
            metadata        TEXT,
            fecha_creacion  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "INSERT INTO documentos_sueltos (tipo, nombre, descripcion, metadata) VALUES (?, ?, ?, ?)",
        (tipo, nombre, descripcion, json.dumps(metadata or {})),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id
