# back/rag/ingest.py
import os

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.normpath(os.path.join(_BASE_DIR, "..", "data", "pdfs"))
SAVE_PATH = os.path.normpath(os.path.join(_BASE_DIR, "..", "data", "indice_faiss"))


def main():
    if not os.path.isdir(PDF_DIR):
        print(f"❌ Carpeta de PDFs no encontrada: {PDF_DIR}")
        return

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
    if not pdf_files:
        print(f"❌ No se encontraron PDFs en {PDF_DIR}")
        return

    print(f"📄 Procesando {len(pdf_files)} PDF(s): {pdf_files}")
    all_chunks = []

    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        print(f"  ▶ Cargando {pdf_file}...")
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", " ", ""],
        )
        chunks = splitter.split_documents(docs)
        all_chunks.extend(chunks)
        print(f"    → {len(chunks)} fragmentos generados")

    if not all_chunks:
        print("❌ No se generaron fragmentos. Verifica los PDFs.")
        return

    print("🧠 Generando embeddings con nomic-embed-text...")
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    os.makedirs(SAVE_PATH, exist_ok=True)
    vectorstore = FAISS.from_documents(all_chunks, embeddings)
    vectorstore.save_local(SAVE_PATH)

    print(f"✅ Índice FAISS guardado en '{SAVE_PATH}'")
    print(f"   Total de fragmentos indexados: {len(all_chunks)}")


if __name__ == "__main__":
    main()
