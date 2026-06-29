from db import db, row_to_dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/procuraduria", tags=["procuraduria"])


class ProcuraduriaIn(BaseModel):
    nombre: str
    tipo: str | None = None
    descripcion: str | None = None


@router.get("/")
def listar():
    with db() as conn:
        rows = conn.execute("SELECT * FROM procuradurias ORDER BY id").fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/{id}")
def obtener(id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM procuradurias WHERE id=?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Procuraduría no encontrada")
    return row_to_dict(row)


@router.post("/", status_code=201)
def crear(body: ProcuraduriaIn):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO procuradurias (nombre, tipo, descripcion) VALUES (?,?,?)",
            (body.nombre, body.tipo, body.descripcion),
        )
    return {"id": cur.lastrowid}
