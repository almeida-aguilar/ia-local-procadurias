from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
from config import ALGORITHM, DATOS_URL, SECRET_KEY, TOKEN_EXP_H
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

pwd_ctx = HTTPBearer()


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXP_H)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(pwd_ctx),
) -> dict:
    return decode_token(credentials.credentials)


def require_role(*roles: str):
    async def _check(user: dict = Depends(get_current_user)):
        if user.get("rol") not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin permisos suficientes")
        return user

    return _check


async def authenticate_user(email: str, password: str) -> dict:
    async with httpx.AsyncClient(base_url=DATOS_URL) as client:
        r = await client.get(f"/usuarios/internal/email/{email}")  # ← /internal/
        if r.status_code == 404:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas"
            )
        r.raise_for_status()
        user = r.json()

    if not verify_password(password, user["contrasena_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas")

    return user
