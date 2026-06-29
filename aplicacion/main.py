import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth_router, consultas, gestion

app = FastAPI(title="LociaPro · Capa de Aplicación", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(consultas.router)
app.include_router(gestion.router)


@app.get("/health")
def health():
    return {"status": "ok", "layer": "aplicacion"}


def start():
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    start()
