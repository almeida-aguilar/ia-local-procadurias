#!/usr/bin/env bash
# ================================================================
#  security_tests.sh — LociaPro · Tests de seguridad con curl
#  Cubre: capa de datos (:8000) y capa de aplicación (:8001)
#
#  Uso:
#    bash security_tests.sh              # modo normal
#    bash security_tests.sh --verbose    # muestra respuestas completas
# ================================================================
set -uo pipefail

DATOS="http://localhost:8000"
APP="http://localhost:8001"
VERBOSE=false
[[ "${1:-}" == "--verbose" ]] && VERBOSE=true

# ── Colores ──────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

PASS=0; FAIL=0; WARN=0

# ── Helpers ──────────────────────────────────────────────────────
section() { echo -e "\n${BOLD}━━━  $*  ━━━${RESET}"; }

# expect_status <label> <expected_code> <actual_code> [body]
expect_status() {
  local label="$1" expected="$2" actual="$3" body="${4:-}"
  if [[ "$actual" == "$expected" ]]; then
    echo -e "  ${GREEN}✔ PASS${RESET}  $label  (HTTP $actual)"
    (( PASS++ )) || true
  else
    echo -e "  ${RED}✘ FAIL${RESET}  $label  — esperado HTTP $expected, recibido HTTP $actual"
    $VERBOSE && [[ -n "$body" ]] && echo -e "         body: $body"
    (( FAIL++ )) || true
  fi
}

# expect_deny <label> <actual_code> [body]
# Cualquier 4xx es aceptable; 2xx es fallo de seguridad
expect_deny() {
  local label="$1" actual="$2" body="${3:-}"
  if [[ "$actual" =~ ^4 ]]; then
    echo -e "  ${GREEN}✔ PASS${RESET}  $label  (HTTP $actual — acceso denegado)"
    (( PASS++ )) || true
  elif [[ "$actual" =~ ^5 ]]; then
    echo -e "  ${YELLOW}⚠ WARN${RESET}  $label  (HTTP $actual — error de servidor, revisar)"
    (( WARN++ )) || true
  else
    echo -e "  ${RED}✘ FAIL${RESET}  $label  — HTTP $actual (ACCESO CONCEDIDO — BRECHA DE SEGURIDAD)"
    $VERBOSE && [[ -n "$body" ]] && echo -e "         body: $body"
    (( FAIL++ )) || true
  fi
}

# curl helper: devuelve "<http_code> <body>"
req() {
  local method="$1"; shift
  local url="$1";    shift
  local out
  out=$(curl -sk -X "$method" "$url" "$@" \
        -w '\n__STATUS__%{http_code}' 2>/dev/null) || true
  local body status
  body=$(echo "$out" | sed '$d')
  status=$(echo "$out" | tail -1 | sed 's/__STATUS__//')
  echo "$status|$body"
}

# ── Obtener token válido de prueba ────────────────────────────────
get_token() {
  local email="$1" pass="$2"
  local out
  out=$(curl -sk -X POST "$APP/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$email\",\"password\":\"$pass\"}" \
        -w '\n__STATUS__%{http_code}' 2>/dev/null) || true
  local body status
  body=$(echo "$out" | sed '$d')
  status=$(echo "$out" | tail -1 | sed 's/__STATUS__//')
  if [[ "$status" == "200" ]]; then
    echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo ""
  else
    echo ""
  fi
}

echo -e "\n${BOLD}${CYAN}LociaPro · Suite de tests de seguridad${RESET}"
echo -e "Datos → ${DATOS}   Aplicación → ${APP}\n"

# ================================================================
# TOKENS DE PRUEBA
# ================================================================
echo -e "${CYAN}[INFO]${RESET}  Obteniendo tokens de prueba..."

TOKEN_ASISTENTE=$(get_token "maria.torres@munilima.gob.pe" "pass123")   # rol: asistente
TOKEN_ADMIN=$(get_token "elena.ponce@anticorrupcion.gob.pe" "pass123")     # rol: admin

if [[ -z "$TOKEN_ASISTENTE" ]]; then
  echo -e "${YELLOW}[WARN]${RESET}  No se pudo obtener token de asistente — algunos tests se saltarán"
fi
if [[ -z "$TOKEN_ADMIN" ]]; then
  echo -e "${YELLOW}[WARN]${RESET}  No se pudo obtener token de admin — algunos tests se saltarán"
fi

FAKE_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5OTkiLCJlbWFpbCI6ImZha2VAZXZpbC5jb20iLCJyb2wiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.INVALIDSIGNATURE"
EXPIRED_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxfQ.abc"

# ================================================================
section "1 · AUTENTICACIÓN — Capa de aplicación (:8001)"
# ================================================================

# 1.1 Credenciales incorrectas → 401
r=$(req POST "$APP/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"carlos.mendoza@procuraduria.gob.pe","password":"WRONG"}')
expect_status "1.1  Contraseña incorrecta" "401" "${r%%|*}" "${r##*|}"

# 1.2 Usuario inexistente → 401
r=$(req POST "$APP/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"noexiste@evil.com","password":"pass123"}')
expect_status "1.2  Usuario inexistente" "401" "${r%%|*}" "${r##*|}"

# 1.3 Payload vacío → 422
r=$(req POST "$APP/auth/login" \
    -H "Content-Type: application/json" \
    -d '{}')
expect_status "1.3  Payload vacío" "422" "${r%%|*}" "${r##*|}"

# 1.4 Sin cabecera Content-Type → 422
r=$(req POST "$APP/auth/login" \
    -d '{"email":"carlos.mendoza@procuraduria.gob.pe","password":"pass123"}')
expect_status "1.4  Sin Content-Type" "422" "${r%%|*}" "${r##*|}"

# 1.5 Ruta /me sin token → 403/401
r=$(req GET "$APP/auth/me")
expect_deny "1.5  GET /auth/me sin token" "${r%%|*}" "${r##*|}"

# 1.6 /me con token falso → 401
r=$(req GET "$APP/auth/me" -H "Authorization: Bearer TOKENBASURA")
expect_deny "1.6  GET /auth/me con token inválido" "${r%%|*}" "${r##*|}"

# 1.7 /me con token expirado → 401
r=$(req GET "$APP/auth/me" -H "Authorization: Bearer $EXPIRED_TOKEN")
expect_deny "1.7  GET /auth/me con token expirado" "${r%%|*}" "${r##*|}"

# 1.8 Esquema Bearer incorrecto (Basic) → 403/401
r=$(req GET "$APP/auth/me" -H "Authorization: Basic dXNlcjpwYXNz")
expect_deny "1.8  Esquema Basic en lugar de Bearer" "${r%%|*}" "${r##*|}"

# 1.9 Token manipulado (firma incorrecta) → 401
r=$(req GET "$APP/auth/me" -H "Authorization: Bearer $FAKE_TOKEN")
expect_deny "1.9  JWT con firma falsa (rol=admin inyectado)" "${r%%|*}" "${r##*|}"

# ================================================================
section "2 · AUTORIZACIÓN — Escalada de privilegios (:8001)"
# ================================================================

if [[ -n "$TOKEN_ASISTENTE" ]]; then
  # 2.1 Asistente intenta re-indexar FAISS (solo admin/procurador) → 403
  r=$(req POST "$APP/gestion/faiss/ingest" \
      -H "Authorization: Bearer $TOKEN_ASISTENTE")
  expect_deny "2.1  Asistente → POST /gestion/faiss/ingest" "${r%%|*}" "${r##*|}"

  # 2.2 Asistente intenta listar procuradurías (solo admin) → 403
  r=$(req GET "$APP/gestion/procuraduria" \
      -H "Authorization: Bearer $TOKEN_ASISTENTE")
  expect_deny "2.2  Asistente → GET /gestion/procuraduria" "${r%%|*}" "${r##*|}"

  # 2.3 Asistente elimina suelto ajeno (solo admin/procurador) → 403
  r=$(req DELETE "$APP/gestion/sueltos/1" \
      -H "Authorization: Bearer $TOKEN_ASISTENTE")
  expect_deny "2.3  Asistente → DELETE /gestion/sueltos/1" "${r%%|*}" "${r##*|}"

  # 2.4 Asistente accede a chat de otro usuario → 403
  r=$(req GET "$APP/consultas/chats/9999/mensajes" \
      -H "Authorization: Bearer $TOKEN_ASISTENTE")
  expect_deny "2.4  Asistente → chat de otro usuario (id=9999)" "${r%%|*}" "${r##*|}"
fi

if [[ -n "$TOKEN_ADMIN" ]]; then
  # 2.5 Admin puede listar procuradurías → 200
  r=$(req GET "$APP/gestion/procuraduria" \
      -H "Authorization: Bearer $TOKEN_ADMIN")
  expect_status "2.5  Admin → GET /gestion/procuraduria" "200" "${r%%|*}" "${r##*|}"
fi

# ================================================================
section "3 · INYECCIÓN — SQL & JSON (:8001 y :8000)"
# ================================================================

# 3.1 SQL injection en login (email) → 401/422, nunca 200
r=$(req POST "$APP/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"'"'"' OR 1=1 --","password":"x"}')
expect_deny "3.1  SQLi en email de login" "${r%%|*}" "${r##*|}"

# 3.2 SQL injection en password → 401/422, nunca 200
r=$(req POST "$APP/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"carlos.mendoza@procuraduria.gob.pe","password":"'"'"' OR '"'"'1'"'"'='"'"'1"}')
expect_deny "3.2  SQLi en password de login" "${r%%|*}" "${r##*|}"

# 3.3 SQLi en query param de sueltos (:8000) → no debe exponer datos
r=$(req GET "$DATOS/sueltos?nombre=%27%20OR%201%3D1%20--")
# Aquí cualquier 2xx es aceptable SIEMPRE QUE no devuelva TODOS los registros
# Solo verificamos que responde (no crash 5xx)
code="${r%%|*}"
if [[ "$code" == "200" ]]; then
  echo -e "  ${YELLOW}⚠ WARN${RESET}  3.3  SQLi en ?nombre — HTTP 200 (verificar manualmente que no devuelve todo)"
  (( WARN++ )) || true
elif [[ "$code" =~ ^4 ]]; then
  echo -e "  ${GREEN}✔ PASS${RESET}  3.3  SQLi en ?nombre= — HTTP $code"
  (( PASS++ )) || true
else
  echo -e "  ${RED}✘ FAIL${RESET}  3.3  SQLi en ?nombre= — HTTP $code (posible error de servidor)"
  (( FAIL++ )) || true
fi

# 3.4 JSON con campos extra (mass assignment) no debe cambiar rol
if [[ -n "$TOKEN_ASISTENTE" ]]; then
  r=$(req POST "$APP/auth/register" \
      -H "Content-Type: application/json" \
      -d '{"procuraduria_id":1,"nombre":"Hacker","email":"hacker+'"$$"'@evil.com","password":"pass123","rol":"admin","extra_field":"injected"}')
  code="${r%%|*}"
  body="${r##*|}"
  if [[ "$code" == "201" ]]; then
    rol=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('rol','?'))" 2>/dev/null || echo "?")
    if [[ "$rol" == "admin" ]]; then
      echo -e "  ${RED}✘ FAIL${RESET}  3.4  Mass assignment — usuario creado con rol=admin"
      (( FAIL++ )) || true
    else
      echo -e "  ${GREEN}✔ PASS${RESET}  3.4  Mass assignment — rol asignado: $rol (no admin)"
      (( PASS++ )) || true
    fi
  else
    echo -e "  ${GREEN}✔ PASS${RESET}  3.4  Mass assignment — HTTP $code (registro rechazado)"
    (( PASS++ )) || true
  fi
fi

# ================================================================
section "4 · EXPOSICIÓN DE DATOS — Capa de datos (:8000)"
# ================================================================

# 4.1 La capa de datos NO debe ser accesible desde el exterior
#     (en producción debería estar en red privada; aquí advertimos)
r=$(req GET "$DATOS/health")
code="${r%%|*}"
if [[ "$code" == "200" ]]; then
  echo -e "  ${YELLOW}⚠ WARN${RESET}  4.1  Capa de datos accesible en $DATOS — en producción debe estar en red privada"
  (( WARN++ )) || true
else
  echo -e "  ${GREEN}✔ PASS${RESET}  4.1  Capa de datos no accesible externamente (HTTP $code)"
  (( PASS++ )) || true
fi

# 4.2 El hash de contraseña no debe aparecer en /usuarios/{id}
r=$(req GET "$DATOS/usuarios/1")
code="${r%%|*}"; body="${r##*|}"
if [[ "$code" == "200" ]]; then
  if echo "$body" | grep -q "contrasena_hash"; then
    echo -e "  ${RED}✘ FAIL${RESET}  4.2  /usuarios/1 expone contrasena_hash"
    (( FAIL++ )) || true
  else
    echo -e "  ${GREEN}✔ PASS${RESET}  4.2  /usuarios/1 no expone contrasena_hash"
    (( PASS++ )) || true
  fi
else
  echo -e "  ${YELLOW}⚠ WARN${RESET}  4.2  /usuarios/1 devolvió HTTP $code — verificar manualmente"
  (( WARN++ )) || true
fi

# 4.3 El hash de contraseña no debe aparecer en /auth/me (:8001)
if [[ -n "$TOKEN_ASISTENTE" ]]; then
  r=$(req GET "$APP/auth/me" -H "Authorization: Bearer $TOKEN_ASISTENTE")
  body="${r##*|}"
  if echo "$body" | grep -q "contrasena_hash"; then
    echo -e "  ${RED}✘ FAIL${RESET}  4.3  /auth/me expone contrasena_hash"
    (( FAIL++ )) || true
  else
    echo -e "  ${GREEN}✔ PASS${RESET}  4.3  /auth/me no expone contrasena_hash"
    (( PASS++ )) || true
  fi
fi

# 4.4 Enumeration de usuarios por ID → debe ser consistente (no 200 vs 404 diferencial)
r1=$(req GET "$DATOS/usuarios/1");  c1="${r1%%|*}"
r2=$(req GET "$DATOS/usuarios/9999"); c2="${r2%%|*}"
if [[ "$c1" == "200" && "$c2" == "404" ]]; then
  echo -e "  ${YELLOW}⚠ WARN${RESET}  4.4  Enumeración de usuarios posible — /usuarios/1→200 /usuarios/9999→404"
  (( WARN++ )) || true
else
  echo -e "  ${GREEN}✔ PASS${RESET}  4.4  Enumeración de usuarios no diferencial ($c1 vs $c2)"
  (( PASS++ )) || true
fi

# ================================================================
section "5 · HEADERS DE SEGURIDAD — Capa de aplicación (:8001)"
# ================================================================

check_header() {
  local label="$1" header="$2"
  local val
  val=$(curl -sk --max-time 5 -X GET "$APP/health" -D - -o /dev/null 2>/dev/null \
        | grep -i "^$header:" | head -1 | tr -d '\r')
  if [[ -n "$val" ]]; then
    echo -e "  ${GREEN}✔ PASS${RESET}  $label  → $val"
    (( PASS++ )) || true
  else
    echo -e "  ${YELLOW}⚠ WARN${RESET}  $label  — header ausente (recomendado en producción)"
    (( WARN++ )) || true
  fi
}

check_header "5.1  X-Content-Type-Options"    "x-content-type-options"
check_header "5.2  X-Frame-Options"           "x-frame-options"
check_header "5.3  Strict-Transport-Security" "strict-transport-security"
check_header "5.4  Content-Security-Policy"   "content-security-policy"

# 5.5 Server header no debe revelar versión exacta
server=$(curl -sk --max-time 5 -X GET "$APP/health" -D - -o /dev/null 2>/dev/null \
         | grep -i "^server:" | head -1 | tr -d '\r')
if echo "$server" | grep -qiE "uvicorn|python|fastapi"; then
  echo -e "  ${YELLOW}⚠ WARN${RESET}  5.5  Header Server revela stack: $server"
  (( WARN++ )) || true
else
  echo -e "  ${GREEN}✔ PASS${RESET}  5.5  Header Server no revela stack técnico"
  (( PASS++ )) || true
fi

# ================================================================
section "6 · RATE LIMITING & BRUTE FORCE — Capa de aplicación (:8001)"
# ================================================================

echo -n "  Enviando 20 intentos de login fallido..."
block_detected=false
for i in $(seq 1 20); do
  r=$(req POST "$APP/auth/login" \
      -H "Content-Type: application/json" \
      -d '{"email":"carlos.mendoza@procuraduria.gob.pe","password":"WRONG"}')
  code="${r%%|*}"
  if [[ "$code" == "429" || "$code" == "423" ]]; then
    block_detected=true
    echo ""
    echo -e "  ${GREEN}✔ PASS${RESET}  6.1  Rate limiting activo en intento $i (HTTP $code)"
    (( PASS++ )) || true
    break
  fi
done
if ! $block_detected; then
  echo ""
  echo -e "  ${YELLOW}⚠ WARN${RESET}  6.1  Sin rate limiting detectado — implementar slowdown/bloqueo tras N intentos"
  (( WARN++ )) || true
fi

# ================================================================
section "7 · IDOR (Insecure Direct Object Reference) (:8001)"
# ================================================================

if [[ -n "$TOKEN_ASISTENTE" ]]; then
  # 7.1 Intentar leer mensajes de un chat que no pertenece al usuario
  r=$(req GET "$APP/consultas/chats/1/mensajes" \
      -H "Authorization: Bearer $TOKEN_ASISTENTE")
  code="${r%%|*}"
  # Si devuelve 200, podría ser el propio chat del usuario → adveritmos
  if [[ "$code" == "200" ]]; then
    echo -e "  ${YELLOW}⚠ WARN${RESET}  7.1  GET /chats/1/mensajes → 200 (verificar que chat_id=1 pertenece al usuario)"
    (( WARN++ )) || true
  elif [[ "$code" =~ ^4 ]]; then
    echo -e "  ${GREEN}✔ PASS${RESET}  7.1  Acceso a chat ajeno rechazado (HTTP $code)"
    (( PASS++ )) || true
  fi

  # 7.2 Intentar eliminar chat ajeno
  r=$(req DELETE "$APP/consultas/chats/9999" \
      -H "Authorization: Bearer $TOKEN_ASISTENTE")
  code="${r%%|*}"
  if [[ "$code" == "204" ]]; then
    echo -e "  ${YELLOW}⚠ WARN${RESET}  7.2  DELETE /chats/9999 → 204 (verificar si el chat existía y era ajeno)"
    (( WARN++ )) || true
  else
    echo -e "  ${GREEN}✔ PASS${RESET}  7.2  DELETE chat inexistente/ajeno → HTTP $code"
    (( PASS++ )) || true
  fi
fi

# ================================================================
section "8 · RUTAS SENSIBLES SIN PROTECCIÓN — Capa de datos (:8000)"
# ================================================================

sensitive_routes=(
  "/usuarios/"
  "/procuraduria/"
  "/chats/"
  "/documentos"
  "/sueltos"
)

for route in "${sensitive_routes[@]}"; do
  r=$(req GET "$DATOS$route")
  code="${r%%|*}"
  # La capa de datos no implementa auth propia — documentamos la exposición
  if [[ "$code" == "200" ]]; then
    echo -e "  ${YELLOW}⚠ WARN${RESET}  8.x  $DATOS$route → HTTP 200 sin autenticación (solo interna)"
    (( WARN++ )) || true
  else
    echo -e "  ${GREEN}✔ PASS${RESET}  8.x  $DATOS$route → HTTP $code"
    (( PASS++ )) || true
  fi
done

# ================================================================
section "9 · CORS — Origen arbitrario (:8001)"
# ================================================================

# 9.1 Origen malicioso → no debe recibir ACAO: *
cors=$(curl -sk --max-time 5 -X GET "$APP/health" -D - -o /dev/null \
       -H "Origin: https://evil.com" 2>/dev/null \
       | grep -i "access-control-allow-origin" | tr -d '\r')

if echo "$cors" | grep -q "\*"; then
  echo -e "  ${YELLOW}⚠ WARN${RESET}  9.1  CORS abierto (Access-Control-Allow-Origin: *) — restringir en producción"
  (( WARN++ )) || true
elif [[ -z "$cors" ]]; then
  echo -e "  ${GREEN}✔ PASS${RESET}  9.1  Sin CORS header para origen evil.com"
  (( PASS++ )) || true
else
  echo -e "  ${YELLOW}⚠ WARN${RESET}  9.1  CORS header presente: $cors — verificar política"
  (( WARN++ )) || true
fi

# ================================================================
# RESUMEN FINAL
# ================================================================
TOTAL=$(( PASS + FAIL + WARN ))
echo -e "\n${BOLD}━━━  Resumen  ━━━${RESET}"
echo -e "  Total tests : $TOTAL"
echo -e "  ${GREEN}✔ PASS${RESET}       : $PASS"
echo -e "  ${RED}✘ FAIL${RESET}       : $FAIL  ← brechas de seguridad"
echo -e "  ${YELLOW}⚠ WARN${RESET}       : $WARN  ← revisar antes de producción"

if (( FAIL > 0 )); then
  echo -e "\n${RED}${BOLD}Se encontraron $FAIL fallo(s) crítico(s). Corregir antes de desplegar.${RESET}"
  exit 1
elif (( WARN > 0 )); then
  echo -e "\n${YELLOW}Sin fallos críticos, pero hay $WARN advertencia(s) a resolver.${RESET}"
  exit 0
else
  echo -e "\n${GREEN}${BOLD}Todos los tests pasaron.${RESET}"
  exit 0
fi
