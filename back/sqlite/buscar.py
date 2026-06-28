# back/sqlite/buscar.py
import json
import os
import sqlite3

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(_BASE_DIR, "..", "..", "sueltos.db"))


def buscar_sueltos(tipo=None, nombre_contiene=None):
    """Búsqueda simple en SQLite – devuelve lista de dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM documentos_sueltos WHERE 1=1"
    params = []

    if tipo:
        query += " AND tipo = ?"
        params.append(tipo)
    if nombre_contiene:
        query += " AND nombre LIKE ?"
        params.append(f"%{nombre_contiene}%")

    cursor.execute(query, params)
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados
