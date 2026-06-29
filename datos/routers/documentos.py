import json

from db import db, row_to_dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["documentos"])


# ── Documentos (archivos adjuntos) ──────────────────────────────


class DocumentoIn(BaseModel):
    nombre: str
    descripcion: str | None = None
    ruta_archivo: str | None = None
    tipo_mime: str | None = None
    tamanio: int | None = None
    metadata: dict | None = None


@router.get("/documentos")
def listar_documentos():
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM documentos ORDER BY created_at DESC"
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("/documentos", status_code=201)
def crear_documento(body: DocumentoIn):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO documentos (nombre, descripcion, ruta_archivo, tipo_mime, tamanio, metadata)"
            " VALUES (?,?,?,?,?,?)",
            (
                body.nombre,
                body.descripcion,
                body.ruta_archivo,
                body.tipo_mime,
                body.tamanio,
                json.dumps(body.metadata or {}),
            ),
        )
    return {"id": cur.lastrowid}


# ── Documentos sueltos (JSON estructurados para contexto RAG) ───


class SueltoIn(BaseModel):
    tipo: str
    nombre: str
    descripcion: str | None = None
    metadata: dict | None = None


@router.get("/sueltos")
def listar_sueltos(tipo: str | None = None, nombre: str | None = None):
    query = "SELECT * FROM documentos_sueltos WHERE 1=1"
    params: list = []
    if tipo:
        query += " AND tipo=?"
        params.append(tipo)
    if nombre:
        query += " AND nombre LIKE ?"
        params.append(f"%{nombre}%")
    query += " ORDER BY fecha_creacion DESC"
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("/sueltos", status_code=201)
def crear_suelto(body: SueltoIn):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO documentos_sueltos (tipo, nombre, descripcion, metadata)"
            " VALUES (?,?,?,?)",
            (body.tipo, body.nombre, body.descripcion, json.dumps(body.metadata or {})),
        )
    return {"id": cur.lastrowid}


@router.delete("/sueltos/{id}", status_code=204)
def eliminar_suelto(id: int):
    with db() as conn:
        conn.execute("DELETE FROM documentos_sueltos WHERE id=?", (id,))
