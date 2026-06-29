from db import db, row_to_dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class UsuarioIn(BaseModel):
    procuraduria_id: int
    nombre: str
    email: str
    rol: str
    contrasena_hash: str


@router.get("/email/{email}")
def por_email(email: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
    if not row:
        raise HTTPException(404, "Usuario no encontrado")
    return row_to_dict(row)


@router.get("/{id}")
def obtener(id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id=?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Usuario no encontrado")
    return row_to_dict(row)


@router.get("/procuraduria/{pid}")
def por_procuraduria(pid: int):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM usuarios WHERE procuraduria_id=?", (pid,)
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("/", status_code=201)
def crear(body: UsuarioIn):
    try:
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO usuarios (procuraduria_id, nombre, email, rol, contrasena_hash)"
                " VALUES (?,?,?,?,?)",
                (
                    body.procuraduria_id,
                    body.nombre,
                    body.email,
                    body.rol,
                    body.contrasena_hash,
                ),
            )
        return {"id": cur.lastrowid}
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(409, "Email ya registrado")
        raise
