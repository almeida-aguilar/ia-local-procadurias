# back/rag/buscar.py
import os

from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaEmbeddings, OllamaLLM

# Ruta absoluta relativa a este archivo → siempre funciona sin importar el CWD
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAISS_PATH = os.path.join(_BASE_DIR, "..", "data", "indice_faiss")


def consultar_rag(pregunta: str) -> str:
    """Recibe una pregunta y devuelve respuesta basada en los PDFs indexados."""

    # 1. Cargar el índice FAISS
    #    ⚠️  El modelo de embeddings DEBE ser el mismo que usó ingest.py
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    faiss_path = os.path.normpath(FAISS_PATH)
    if not os.path.isdir(faiss_path):
        return (
            f"❌ Índice FAISS no encontrado en '{faiss_path}'. "
            "Ejecuta primero: python back/rag/ingest.py"
        )

    vectorstore = FAISS.load_local(
        faiss_path, embeddings, allow_dangerous_deserialization=True
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # 2. Obtener chunks relevantes
    chunks = retriever.invoke(pregunta)
    if not chunks:
        return "No encontré fragmentos relevantes en los documentos indexados."

    contexto = "\n\n".join([c.page_content for c in chunks])

    # 3. Prompt
    prompt = ChatPromptTemplate.from_template(
        """Responde en español basándote SOLO en este contexto legal peruano.
Si no encuentras la respuesta en el contexto, di exactamente:
"No tengo información sobre eso en los documentos proporcionados."

CONTEXTO:
{contexto}

PREGUNTA:
{pregunta}

RESPUESTA:"""
    )

    # 4. LLM
    llm = OllamaLLM(model="llama3.2", temperature=0)

    # 5. Cadena RAG correcta: pasamos el dict directamente al prompt
    chain = prompt | llm | StrOutputParser()
    respuesta = chain.invoke({"contexto": contexto, "pregunta": pregunta})
    return respuesta
