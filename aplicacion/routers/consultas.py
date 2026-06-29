import auth
import httpx
import rag
from config import DATOS_URL
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/consultas", tags=["consultas"])


class ConsultaIn(BaseModel):
    pregunta: str
    chat_id: int | None = None  # None → crea un chat nuevo automáticamente


@router.post("/")
async def consultar(
    body: ConsultaIn,
    user: dict = Depends(auth.get_current_user),
):
    usuario_id = int(user["sub"])

    async with httpx.AsyncClient(base_url=DATOS_URL, timeout=120) as client:
        # 1. Crear chat si no viene uno
        if body.chat_id is None:
            titulo = body.pregunta[:60] + ("…" if len(body.pregunta) > 60 else "")
            r = await client.post(
                "/chats/", json={"usuario_id": usuario_id, "titulo": titulo}
            )
            r.raise_for_status()
            chat_id = r.json()["id"]
        else:
            chat_id = body.chat_id

        # 2. Persistir mensaje del usuario
        await client.post(
            f"/chats/{chat_id}/mensajes",
            json={
                "rol": "usuario",
                "contenido": body.pregunta,
                "metadata": {"email": user["email"]},
            },
        )

    # 3. Ejecutar pipeline RAG (puede ser lento → timeout generoso)
    try:
        respuesta = await rag.consultar(body.pregunta)
    except Exception as e:
        respuesta = f"Error al procesar la consulta: {e}"

    async with httpx.AsyncClient(base_url=DATOS_URL, timeout=30) as client:
        # 4. Persistir respuesta del asistente
        await client.post(
            f"/chats/{chat_id}/mensajes",
            json={
                "rol": "asistente",
                "contenido": respuesta,
                "metadata": {"modelo": "llama3.2"},
            },
        )

    return {"chat_id": chat_id, "respuesta": respuesta}


@router.get("/chats")
async def mis_chats(user: dict = Depends(auth.get_current_user)):
    usuario_id = int(user["sub"])
    async with httpx.AsyncClient(base_url=DATOS_URL) as client:
        r = await client.get(f"/chats/usuario/{usuario_id}")
        r.raise_for_status()
    return r.json()


@router.get("/chats/{chat_id}/mensajes")
async def mensajes(
    chat_id: int,
    user: dict = Depends(auth.get_current_user),
):
    async with httpx.AsyncClient(base_url=DATOS_URL) as client:
        chat_r = await client.get(f"/chats/{chat_id}")
        if chat_r.status_code == 404:
            raise HTTPException(404, "Chat no encontrado")
        chat = chat_r.json()

    if chat["usuario_id"] != int(user["sub"]) and user["rol"] != "admin":
        raise HTTPException(403, "Sin acceso a este chat")

    async with httpx.AsyncClient(base_url=DATOS_URL) as client:
        r = await client.get(f"/chats/{chat_id}/mensajes")
        r.raise_for_status()
    return r.json()


@router.delete("/chats/{chat_id}", status_code=204)
async def eliminar_chat(
    chat_id: int,
    user: dict = Depends(auth.get_current_user),
):
    async with httpx.AsyncClient(base_url=DATOS_URL) as client:
        await client.delete(f"/chats/{chat_id}")
