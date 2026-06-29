import auth
import httpx
from config import DATOS_URL
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/gestion", tags=["gestion"])


class SueltoIn(BaseModel):
    tipo: str
    nombre: str
    descripcion: str | None = None
    metadata: dict | None = None


# ── Sueltos ──────────────────────────────────────────────────────


@router.get("/sueltos")
async def listar_sueltos(
    tipo: str | None = None,
    nombre: str | None = None,
    _: dict = Depends(auth.get_current_user),
):
    params = {}
    if tipo:
        params["tipo"] = tipo
    if nombre:
        params["nombre"] = nombre
    async with httpx.AsyncClient(base_url=DATOS_URL) as client:
        r = await client.get("/sueltos", params=params)
        r.raise_for_status()
    return r.json()


@router.post("/sueltos", status_code=201)
async def crear_suelto(
    body: SueltoIn,
    user: dict = Depends(auth.get_current_user),
):
    async with httpx.AsyncClient(base_url=DATOS_URL) as client:
        r = await client.post("/sueltos", json=body.model_dump())
        r.raise_for_status()
    return r.json()


@router.delete("/sueltos/{id}", status_code=204)
async def eliminar_suelto(
    id: int,
    user: dict = Depends(auth.require_role("admin", "procurador")),
):
    async with httpx.AsyncClient(base_url=DATOS_URL) as client:
        await client.delete(f"/sueltos/{id}")


# ── FAISS (solo admin/procurador) ────────────────────────────────


@router.post("/faiss/ingest")
async def faiss_ingest(
    _: dict = Depends(auth.require_role("admin", "procurador")),
):
    async with httpx.AsyncClient(base_url=DATOS_URL, timeout=300) as client:
        r = await client.post("/faiss/ingest/sync")
        r.raise_for_status()
    return r.json()


# ── Procuradurías (solo admin) ───────────────────────────────────


@router.get("/procuraduria")
async def listar_procuraduria(_: dict = Depends(auth.require_role("admin"))):
    async with httpx.AsyncClient(base_url=DATOS_URL) as client:
        r = await client.get("/procuraduria/")
        r.raise_for_status()
    return r.json()
