import uvicorn
from db import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chats, documentos, faiss_router, procuraduria, usuarios

app = FastAPI(title="LociaPro · Capa de Datos", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(procuraduria.router)
app.include_router(usuarios.router)
app.include_router(chats.router)
app.include_router(documentos.router)
app.include_router(faiss_router.router)


@app.on_event("startup")
def startup():
    init_db()
    print("✅ Base de datos inicializada")


@app.get("/health")
def health():
    return {"status": "ok", "layer": "datos"}


def start():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
