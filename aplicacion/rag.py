import json

import httpx
from config import DATOS_URL, LLM_MODEL
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM

PROMPT = ChatPromptTemplate.from_template("""Eres un asistente legal experto en legislación peruana.
Responde en español basándote ÚNICAMENTE en el contexto proporcionado.
Si no encuentras la respuesta, di exactamente: "No tengo información suficiente en los documentos disponibles."

--- NORMATIVA Y JURISPRUDENCIA (RAG) ---
{contexto_faiss}

--- EXPEDIENTES Y REGISTROS INTERNOS ---
{contexto_sueltos}

--- PREGUNTA ---
{pregunta}

RESPUESTA:""")


async def _faiss_search(query: str, client: httpx.AsyncClient) -> str:
    r = await client.post("/faiss/search", json={"query": query, "k": 4})
    if r.status_code != 200:
        return "(índice FAISS no disponible)"
    chunks = r.json().get("results", [])
    if not chunks:
        return "(sin resultados en el índice)"
    return "\n\n".join(c["content"] for c in chunks)


async def _sueltos_context(query: str, client: httpx.AsyncClient) -> str:
    r = await client.get("/sueltos")
    if r.status_code != 200:
        return "(sin registros internos)"
    sueltos = r.json()
    if not sueltos:
        return "(sin registros internos)"

    keywords = set(query.lower().split())
    relevantes = [
        s
        for s in sueltos
        if any(
            kw in (s.get("nombre", "") + s.get("descripcion", "")).lower()
            for kw in keywords
        )
    ]
    items = relevantes[:5] if relevantes else sueltos[:3]
    lines = [
        f"[{s['tipo'].upper()}] {s['nombre']}: {s.get('descripcion', '')} "
        f"| meta: {json.dumps(s.get('metadata', {}), ensure_ascii=False)}"
        for s in items
    ]
    return "\n".join(lines)


async def consultar(pregunta: str) -> str:
    async with httpx.AsyncClient(base_url=DATOS_URL, timeout=60) as client:
        ctx_faiss = await _faiss_search(pregunta, client)
        ctx_sueltos = await _sueltos_context(pregunta, client)

    llm = OllamaLLM(model=LLM_MODEL, temperature=0)
    chain = PROMPT | llm | StrOutputParser()
    return chain.invoke(
        {
            "contexto_faiss": ctx_faiss,
            "contexto_sueltos": ctx_sueltos,
            "pregunta": pregunta,
        }
    )
