#!/usr/bin/env bash
# ================================================================
#  init.sh  –  Inicializa Ollama (modelos) + índice FAISS
#  Uso: bash init.sh [--skip-ingest]
# ================================================================
set -euo pipefail

# ── Colores ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
ok()      { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
section() { echo -e "\n${BOLD}━━━  $*  ━━━${RESET}"; }

SKIP_INGEST=false
[[ "${1:-}" == "--skip-ingest" ]] && SKIP_INGEST=true

# ── Raíz del proyecto (donde está este script) ───────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ================================================================
section "1 · Verificar Ollama"
# ================================================================
if ! command -v ollama &>/dev/null; then
    error "Ollama no está instalado."
    echo    "  → Instálalo con:"
    echo    "      curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi
ok "Ollama encontrado: $(ollama --version 2>/dev/null | head -1)"

# ── Arrancar el servidor si no está corriendo ────────────────────
if ! curl -sf http://localhost:11434/api/tags &>/dev/null; then
    info "Iniciando ollama serve en segundo plano..."
    ollama serve &>/tmp/ollama.log &
    OLLAMA_PID=$!
    echo "  PID del servidor: $OLLAMA_PID"

    # Esperar hasta 30 s a que responda
    for i in $(seq 1 30); do
        curl -sf http://localhost:11434/api/tags &>/dev/null && break
        sleep 1
        [[ $i -eq 30 ]] && { error "Ollama no respondió tras 30 s. Revisa /tmp/ollama.log"; exit 1; }
    done
    ok "Ollama server listo"
else
    ok "Ollama server ya está corriendo"
fi

# ================================================================
section "2 · Descargar modelos"
# ================================================================
pull_model() {
    local model="$1"
    if ollama list 2>/dev/null | grep -q "^${model}"; then
        ok "Modelo '${model}' ya descargado – se omite"
    else
        info "Descargando '${model}'  (puede tomar varios minutos)..."
        ollama pull "$model"
        ok "Modelo '${model}' listo"
    fi
}

pull_model "llama3.2"          # LLM principal para respuestas
pull_model "nomic-embed-text"  # Embeddings para FAISS  ← debe coincidir con ingest.py

# ================================================================
section "3 · Crear directorios necesarios"
# ================================================================
mkdir -p back/data/pdfs back/data/indice_faiss front
ok "Directorios OK"

# ── Avisar si no hay PDFs ────────────────────────────────────────
PDF_COUNT=$(find back/data/pdfs -name "*.pdf" 2>/dev/null | wc -l)
if [[ $PDF_COUNT -eq 0 ]]; then
    warn "No hay PDFs en back/data/pdfs/"
    warn "Copia tus PDFs ahí y luego ejecuta:"
    warn "  python back/rag/ingest.py"
fi

# ================================================================
section "4 · Generar índice FAISS"
# ================================================================
if $SKIP_INGEST; then
    warn "Se omite ingest (--skip-ingest)"
elif [[ $PDF_COUNT -eq 0 ]]; then
    warn "Sin PDFs → se omite la indexación"
else
    info "Ejecutando ingest.py con $PDF_COUNT PDF(s)..."
    python back/rag/ingest.py
    ok "Índice FAISS generado"
fi

# ================================================================
section "5 · Listo"
# ================================================================
echo -e "
${GREEN}${BOLD}✅  Inicialización completada${RESET}

  Ejecuta la app con:
  ${CYAN}streamlit run front/app.py${RESET}

  O el demo rápido con:
  ${CYAN}python back/demo.py${RESET}

  Si agregas PDFs nuevos, regenera el índice:
  ${CYAN}python back/rag/ingest.py${RESET}
"
