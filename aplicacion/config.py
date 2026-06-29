import os

DATOS_URL = os.getenv("DATOS_URL", "http://localhost:8000")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-lociapro-changeme")
ALGORITHM = "HS256"
TOKEN_EXP_H = int(os.getenv("TOKEN_EXP_H", "8"))
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434")
