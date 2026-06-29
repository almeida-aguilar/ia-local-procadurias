import os
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

FAISS_PATH = os.getenv(
    "FAISS_PATH", str(Path(__file__).parent.parent / "data" / "indice_faiss")
)
PDF_DIR = os.getenv("PDF_DIR", str(Path(__file__).parent.parent / "data" / "pdfs"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")


def _embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=EMBED_MODEL)


def ingest() -> dict:
    pdf_dir = Path(PDF_DIR)
    if not pdf_dir.is_dir():
        return {"ok": False, "error": f"Carpeta no encontrada: {PDF_DIR}"}

    pdfs = list(pdf_dir.glob("*.pdf"))
    if not pdfs:
        return {"ok": False, "error": "No hay PDFs en la carpeta"}

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", ".", " ", ""]
    )
    all_chunks = []
    for pdf in pdfs:
        docs = PyPDFLoader(str(pdf)).load()
        all_chunks.extend(splitter.split_documents(docs))

    faiss_path = Path(FAISS_PATH)
    faiss_path.mkdir(parents=True, exist_ok=True)

    vs = FAISS.from_documents(all_chunks, _embeddings())
    vs.save_local(str(faiss_path))

    return {"ok": True, "pdfs": len(pdfs), "chunks": len(all_chunks)}


def search(query: str, k: int = 4) -> list[dict]:
    faiss_path = Path(FAISS_PATH)
    if not faiss_path.is_dir():
        return []

    vs = FAISS.load_local(
        str(faiss_path), _embeddings(), allow_dangerous_deserialization=True
    )
    docs = vs.similarity_search_with_score(query, k=k)
    return [
        {"content": doc.page_content, "metadata": doc.metadata, "score": float(score)}
        for doc, score in docs
    ]
