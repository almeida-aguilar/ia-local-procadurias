import json

from db import db, row_to_dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/chats", tags=["chats"])


class ChatIn(BaseModel):
    usuario_id: int
    titulo: str | None = None


class MensajeIn(BaseModel):
    rol: str
    contenido: str
    metadata: dict | None = None


@router.post("/", status_code=201)
def crear_chat(body: ChatIn):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO chats (usuario_id, titulo) VALUES (?,?)",
            (body.usuario_id, body.titulo),
        )
    return {"id": cur.lastrowid}


@router.get("/usuario/{usuario_id}")
def chats_de_usuario(usuario_id: int):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM chats WHERE usuario_id=? ORDER BY updated_at DESC",
            (usuario_id,),
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/{chat_id}")
def obtener_chat(chat_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Chat no encontrado")
    return row_to_dict(row)


@router.patch("/{chat_id}/estado")
def cambiar_estado(chat_id: int, estado: str):
    with db() as conn:
        conn.execute(
            "UPDATE chats SET estado=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (estado, chat_id),
        )
    return {"ok": True}


@router.post("/{chat_id}/mensajes", status_code=201)
def agregar_mensaje(chat_id: int, body: MensajeIn):
    meta = json.dumps(body.metadata or {})
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO mensajes (chat_id, rol, contenido, metadata) VALUES (?,?,?,?)",
            (chat_id, body.rol, body.contenido, meta),
        )
        conn.execute(
            "UPDATE chats SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (chat_id,)
        )
    return {"id": cur.lastrowid}


@router.get("/{chat_id}/mensajes")
def mensajes_de_chat(chat_id: int):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM mensajes WHERE chat_id=? ORDER BY timestamp ASC",
            (chat_id,),
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.delete("/{chat_id}", status_code=204)
def eliminar_chat(chat_id: int):
    with db() as conn:
        conn.execute("DELETE FROM chats WHERE id=?", (chat_id,))
