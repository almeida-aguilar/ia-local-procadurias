#!/usr/bin/env bash
# ================================================================
#  init.sh  –  Bootstrap completo de LociaPro (3 capas)
#  Uso: bash init.sh [--skip-ingest] [--seed]
# ================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
ok()      { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
section() { echo -e "\n${BOLD}━━━  $*  ━━━${RESET}"; }

SKIP_INGEST=false
SEED=false
for arg in "$@"; do
  [[ "$arg" == "--skip-ingest" ]] && SKIP_INGEST=true
  [[ "$arg" == "--seed" ]]        && SEED=true
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# ================================================================
section "1 · Verificar dependencias"
# ================================================================
for cmd in uv python3 curl; do
  command -v "$cmd" &>/dev/null && ok "$cmd encontrado" \
    || { error "$cmd no está instalado"; exit 1; }
done

command -v ollama &>/dev/null && ok "ollama encontrado" \
  || { error "Ollama no está instalado → curl -fsSL https://ollama.com/install.sh | sh"; exit 1; }

# ================================================================
section "2 · Instalar dependencias uv (workspace)"
# ================================================================
info "Sincronizando workspace..."
uv sync --all-packages
ok "Dependencias instaladas"

# ================================================================
section "3 · Ollama: servidor y modelos"
# ================================================================
if ! curl -sf http://localhost:11434/api/tags &>/dev/null; then
  info "Iniciando ollama serve..."
  ollama serve &>/tmp/ollama.log &
  for i in $(seq 1 30); do
    curl -sf http://localhost:11434/api/tags &>/dev/null && break
    sleep 1
    [[ $i -eq 30 ]] && { error "Ollama no respondió. Ver /tmp/ollama.log"; exit 1; }
  done
  ok "Ollama server listo"
else
  ok "Ollama ya estaba corriendo"
fi

pull_model() {
  local m="$1"
  if ollama list 2>/dev/null | grep -q "^${m}"; then
    ok "Modelo '${m}' ya descargado"
  else
    info "Descargando '${m}'..."
    ollama pull "$m"
    ok "Modelo '${m}' listo"
  fi
}
pull_model "llama3.2"
pull_model "nomic-embed-text"

# ================================================================
section "4 · Crear directorios de datos"
# ================================================================
mkdir -p data/pdfs data/indice_faiss
ok "Directorios OK"

PDF_COUNT=$(find data/pdfs -name "*.pdf" 2>/dev/null | wc -l | tr -d ' ')
[[ $PDF_COUNT -eq 0 ]] && warn "No hay PDFs en data/pdfs/ — agrega PDFs y re-ejecuta con --seed"

# ================================================================
section "5 · Iniciar capa de datos (background)"
# ================================================================
info "Iniciando datos/ en :8000..."
uv run --package lociapro-datos python datos/main.py &>/tmp/lociapro_datos.log &
DATOS_PID=$!

# Esperar a que arranque
for i in $(seq 1 20); do
  curl -sf http://localhost:8000/health &>/dev/null && break
  sleep 1
  [[ $i -eq 20 ]] && { error "datos/ no respondió. Ver /tmp/lociapro_datos.log"; exit 1; }
done
ok "Capa de datos lista (PID $DATOS_PID)"

# ================================================================
section "6 · Seed de datos iniciales"
# ================================================================
if $SEED; then
  info "Cargando datos de prueba..."
  uv run --package lociapro-datos python3 - <<'PYEOF'
import httpx, json

BASE = "http://localhost:8000"

# Procuradurías
procuradurías = [
  {"nombre": "Procuraduría Pública Nacional",       "tipo": "especializada", "descripcion": "Defensa jurídica del Estado"},
  {"nombre": "Procuraduría Municipal de Lima",       "tipo": "municipal",     "descripcion": "Municipalidad de Lima Metropolitana"},
  {"nombre": "Procuraduría del Ministerio de Justicia", "tipo": "ministerial", "descripcion": "Asuntos judiciales del MINJUS"},
  {"nombre": "Procuraduría Anticorrupción",          "tipo": "especializada", "descripcion": "Delitos de corrupción"},
  {"nombre": "Procuraduría Regional de Arequipa",    "tipo": "regional",      "descripcion": "Gobierno Regional de Arequipa"},
]
ids = {}
for p in procuradurías:
    r = httpx.post(f"{BASE}/procuraduria/", json=p)
    ids[p["nombre"]] = r.json()["id"]
print(f"  ✅ {len(ids)} procuradurías creadas")

# Usuarios (contraseñas hasheadas pre-generadas con bcrypt para 'pass123')
import hashlib
import bcrypt
HASH = bcrypt.hashpw(b"pass123", bcrypt.gensalt(12)).decode()
usuarios = [
  (1, "Dr. Carlos Mendoza",    "carlos.mendoza@procuraduria.gob.pe",   "procurador"),
  (1, "Dra. Ana Flores",       "ana.flores@procuraduria.gob.pe",       "procurador"),
  (2, "Dr. Roberto Sánchez",   "roberto.sanchez@munilima.gob.pe",      "procurador"),
  (2, "Lic. María Torres",     "maria.torres@munilima.gob.pe",         "asistente"),
  (3, "Dra. Patricia Ríos",    "patricia.rios@minjus.gob.pe",          "procurador"),
  (4, "Dr. Luis Castillo",     "luis.castillo@anticorrupcion.gob.pe",  "procurador"),
  (4, "Lic. Elena Ponce",      "elena.ponce@anticorrupcion.gob.pe",    "admin"),
  (5, "Dr. Fernando Quispe",   "fernando.quispe@regionarequipa.gob.pe","procurador"),
  (5, "Lic. Rosa Mamani",      "rosa.mamani@regionarequipa.gob.pe",    "admin"),
]
for pid, nombre, email, rol in usuarios:
    httpx.post(f"{BASE}/usuarios/", json={
        "procuraduria_id": pid, "nombre": nombre,
        "email": email, "rol": rol, "contrasena_hash": HASH,
    })
print(f"  ✅ {len(usuarios)} usuarios creados (contraseña: pass123)")

# Sueltos de ejemplo
sueltos = [
  ("caso",       "Rodríguez vs Empresa X",    "Despido laboral 2023",          {"juzgado": "Lima", "estado": "cerrado"}),
  ("perfil",     "Abogado Juan Pérez",         "Especialista en penal",         {"años_exp": 10}),
  ("expediente", "Exp-2024-001",               "Caso de divorcio contencioso",  {"juzgado": "Callao"}),
  ("expediente", "Exp-2024-002",               "Licitación irregular MTC",      {"juzgado": "Lima", "monto": 500000}),
  ("caso",       "Estado vs Constructora SA",  "Incumplimiento de contrato",    {"estado": "activo"}),
]
for tipo, nombre, desc, meta in sueltos:
    httpx.post(f"{BASE}/sueltos", json={
        "tipo": tipo, "nombre": nombre, "descripcion": desc, "metadata": meta
    })
print(f"  ✅ {len(sueltos)} registros sueltos creados")
PYEOF
  ok "Seed completado"
else
  info "Seed omitido (usa --seed para cargar datos de prueba)"
fi

# ================================================================
section "7 · Indexar PDFs en FAISS"
# ================================================================
if $SKIP_INGEST || [[ $PDF_COUNT -eq 0 ]]; then
  warn "Indexación omitida (sin PDFs o --skip-ingest)"
else
  info "Indexando $PDF_COUNT PDF(s)..."
  curl -sf -X POST http://localhost:8000/faiss/ingest/sync | python3 -c \
    "import sys,json; r=json.load(sys.stdin); print(f'  ✅ {r.get(\"chunks\",\"?\")} fragmentos indexados')"
fi

# Detener capa de datos (será relanzada manualmente por el usuario)
kill $DATOS_PID 2>/dev/null || true

# ================================================================
section "8 · Listo — cómo arrancar"
# ================================================================
echo -e "
${GREEN}${BOLD}✅  Bootstrap completado${RESET}

Abre ${BOLD}3 terminales${RESET} y ejecuta:

  ${CYAN}# Terminal 1 — Capa de datos (puerto 8000)${RESET}
  cd ${ROOT} && uv run --package lociapro-datos python datos/main.py

  ${CYAN}# Terminal 2 — Capa de aplicación (puerto 8001)${RESET}
  cd ${ROOT} && uv run --package lociapro-aplicacion python aplicacion/main.py

  ${CYAN}# Terminal 3 — Presentación (puerto 8501)${RESET}
  cd ${ROOT} && uv run --package lociapro-presentacion streamlit run presentacion/app.py

  ${YELLOW}Credenciales de prueba:${RESET}
    Email:     carlos.mendoza@procuraduria.gob.pe
    Contraseña: pass123

  ${YELLOW}Admin:${RESET}
    Email:     elena.ponce@anticorrupcion.gob.pe
    Contraseña: pass123

  Docs de la API:
    Datos →        http://localhost:8000/docs
    Aplicación →   http://localhost:8001/docs
"
