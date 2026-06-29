import auth
import httpx
from config import DATOS_URL
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class RegisterIn(BaseModel):
    procuraduria_id: int
    nombre: str
    email: str
    password: str
    rol: str = "asistente"


@router.post("/login")
async def login(body: LoginIn):
    user = await auth.authenticate_user(body.email, body.password)
    token = auth.create_token(
        {
            "sub": str(user["id"]),
            "email": user["email"],
            "nombre": user["nombre"],
            "rol": user["rol"],
            "procuraduria_id": user["procuraduria_id"],
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "nombre": user["nombre"],
            "email": user["email"],
            "rol": user["rol"],
            "procuraduria_id": user["procuraduria_id"],
        },
    }


@router.post("/register", status_code=201)
async def register(body: RegisterIn):
    payload = {
        "procuraduria_id": body.procuraduria_id,
        "nombre": body.nombre,
        "email": body.email,
        "rol": body.rol,
        "contrasena_hash": auth.hash_password(body.password),
    }
    async with httpx.AsyncClient(base_url=DATOS_URL) as client:
        r = await client.post("/usuarios/", json=payload)
        if r.status_code == 409:
            raise HTTPException(409, "Email ya registrado")
        r.raise_for_status()
    return r.json()


@router.get("/me")
async def me(user: dict = Depends(auth.get_current_user)):
    return user
