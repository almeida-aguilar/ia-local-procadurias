import faiss_service
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/faiss", tags=["faiss"])


class SearchIn(BaseModel):
    query: str
    k: int = 4


@router.post("/search")
def search(body: SearchIn):
    results = faiss_service.search(body.query, body.k)
    return {"results": results}


@router.post("/ingest")
def ingest(background_tasks: BackgroundTasks):
    """Lanza la indexación en background para no bloquear."""
    background_tasks.add_task(faiss_service.ingest)
    return {"ok": True, "message": "Indexación iniciada en background"}


@router.post("/ingest/sync")
def ingest_sync():
    """Indexación síncrona (para init.sh)."""
    result = faiss_service.ingest()
    return result
