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


def safe_user(row) -> dict:
    d = row_to_dict(row)
    d.pop("contrasena_hash", None)
    return d


@router.get("/email/{email}")
def por_email(email: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
    if not row:
        raise HTTPException(404, "Usuario no encontrado")
    return safe_user(row)  # sin hash — para uso general


@router.get("/internal/email/{email}")  # ← nuevo, solo para authenticate_user
def por_email_internal(email: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
    if not row:
        raise HTTPException(404, "Usuario no encontrado")
    return row_to_dict(row)  # con hash — solo lo llama la capa de aplicación


@router.get("/{id}")
def obtener(id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id=?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Usuario no encontrado")
    return safe_user(row)


@router.get("/procuraduria/{pid}")
def por_procuraduria(pid: int):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM usuarios WHERE procuraduria_id=?", (pid,)
        ).fetchall()
    return [safe_user(r) for r in rows]


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
