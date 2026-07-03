import httpx
import pandas as pd
import streamlit as st

APP_URL = "http://localhost:8001"

st.set_page_config(
    page_title="Cerebro Digital · LociaPro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f5f7fb;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stSidebar"] {
        background-color: #eef2f7;
        border-right: 1px solid #dfe5ee;
    }
    div[data-testid="stSidebar"] .st-bb {
        background-color: #eef2f7;
    }
    .stTextInput > div > div > input,
    .stTextArea > div > textarea,
    .stSelectbox > div > div,
    .stNumberInput > div > div > input {
        background-color: #ffffff;
        border: 1px solid #d0d7e2;
        border-radius: 6px;
    }
    .stButton > button {
        background-color: #2f4b66;
        color: white;
        border: 1px solid #2f4b66;
        border-radius: 6px;
    }
    .stButton > button:hover {
        background-color: #264156;
        color: white;
        border: 1px solid #264156;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f3f8;
        color: #2f4b66;
        border-radius: 6px 6px 0 0;
        padding: 8px 12px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        border-bottom: 2px solid #2f4b66;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── HTTP helpers ─────────────────────────────────────────────────


def _headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_get(path: str, params: dict = None):
    r = httpx.get(f"{APP_URL}{path}", headers=_headers(), params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def api_post(path: str, json: dict = None):
    r = httpx.post(f"{APP_URL}{path}", headers=_headers(), json=json, timeout=120)
    r.raise_for_status()
    return r.json()


def api_delete(path: str):
    r = httpx.delete(f"{APP_URL}{path}", headers=_headers(), timeout=30)
    r.raise_for_status()


# ── Session defaults ─────────────────────────────────────────────

for key, val in {
    "token": None,
    "user": None,
    "chat_id": None,
    "mensajes": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ════════════════════════════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════════════════════════════


def page_login():
    st.markdown("## Sistema de gestión legal")
    st.markdown("### Acceso al sistema")
    st.caption("Ingrese sus credenciales para continuar.")
    st.markdown("<hr style='margin: 0.5rem 0 1rem 0; border: 0; border-top: 1px solid #dfe5ee;'>", unsafe_allow_html=True)

    st.markdown("""
    <div style="background-color:#f4f6fa;padding:16px;border-radius:8px;border:1px solid #dfe5ee;margin-bottom:20px;">
    <strong>Acceso institucional</strong><br>
    Este portal permite consultar información jurídica, revisar expedientes sueltos y gestionar conversaciones de apoyo legal.
    </div>
    """, unsafe_allow_html=True)

    with st.form("login"):
        email = st.text_input("Correo institucional")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar", use_container_width=True)

    if submit:
        try:
            data = api_post("/auth/login", {"email": email, "password": password})
            st.session_state.token = data["access_token"]
            st.session_state.user = data["user"]
            st.rerun()
        except httpx.HTTPStatusError as e:
            st.error(
                "Credenciales incorrectas."
                if e.response.status_code == 401
                else f"Error: {e.response.text}"
            )
        except Exception as e:
            st.error(f"No se pudo conectar con la capa de aplicación: {e}")


# ════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════


def sidebar():
    user = st.session_state.user
    with st.sidebar:
        st.markdown("### LociaPro")
        st.caption(f"{user['nombre']}")
        st.caption(f"{user['email']}")
        st.caption(f"Rol: {user['rol']}")
        st.divider()

        opciones = ["Asistente legal", "Expedientes sueltos", "Mis conversaciones"]
        if user["rol"] == "admin":
            opciones.append("Administración")

        page = st.radio("Navegación", opciones, label_visibility="collapsed")

        if user["rol"] == "admin":
            st.divider()
            if st.button("Re-indexar FAISS", use_container_width=True):
                with st.spinner("Indexando PDFs..."):
                    try:
                        r = api_post("/gestion/faiss/ingest")
                        st.success(f"{r.get('chunks', '?')} fragmentos indexados")
                    except Exception as e:
                        st.error(str(e))

        st.divider()
        if st.button("Cerrar sesión", use_container_width=True):
            for k in ["token", "user", "chat_id", "mensajes"]:
                st.session_state[k] = None if k != "mensajes" else []
            st.rerun()

    return page


# ════════════════════════════════════════════════════════════════
# PAGE: ASISTENTE LEGAL (RAG)
# ════════════════════════════════════════════════════════════════


def page_chat():
    st.markdown("## Asistente legal")
    st.caption("Respuestas basadas en la Constitución, códigos y registros internos.")
    st.markdown("<hr style='margin: 0.4rem 0 1rem 0; border: 0; border-top: 1px solid #dfe5ee;'>", unsafe_allow_html=True)

    col_chat, col_hist = st.columns([3, 1])

    # ── Panel derecho: historial de chats ──
    with col_hist:
        st.markdown("**Conversaciones**")
        try:
            chats = api_get("/consultas/chats")
        except Exception:
            chats = []

        if st.button("Nueva consulta", use_container_width=True):
            st.session_state.chat_id = None
            st.session_state.mensajes = []
            st.rerun()

        for c in chats:
            label = f"{'🟢' if c['estado'] == 'activo' else '⚫'} {c['titulo'] or 'Sin título'}"
            if st.button(label, key=f"chat_{c['id']}", use_container_width=True):
                st.session_state.chat_id = c["id"]
                try:
                    st.session_state.mensajes = api_get(
                        f"/consultas/chats/{c['id']}/mensajes"
                    )
                except Exception:
                    st.session_state.mensajes = []
                st.rerun()

    # ── Panel izquierdo: chat activo ──
    with col_chat:
        for msg in st.session_state.mensajes:
            role = "user" if msg["rol"] == "usuario" else "assistant"
            with st.chat_message(role):
                st.markdown(msg["contenido"])

        if prompt := st.chat_input("Escribe tu consulta legal..."):
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🔍 Consultando normativa y registros..."):
                    try:
                        resp = api_post(
                            "/consultas/",
                            {
                                "pregunta": prompt,
                                "chat_id": st.session_state.chat_id,
                            },
                        )
                        st.session_state.chat_id = resp["chat_id"]
                        answer = resp["respuesta"]
                        st.markdown(answer)

                        st.session_state.mensajes.extend(
                            [
                                {"rol": "usuario", "contenido": prompt},
                                {"rol": "asistente", "contenido": answer},
                            ]
                        )
                    except Exception as e:
                        st.error(f"Error: {e}")


# ════════════════════════════════════════════════════════════════
# PAGE: EXPEDIENTES SUELTOS
# ════════════════════════════════════════════════════════════════


def page_sueltos():
    st.markdown("## Expedientes y registros sueltos")
    st.caption("Gestión de casos, perfiles y expedientes de forma organizada.")
    st.markdown("<hr style='margin: 0.4rem 0 1rem 0; border: 0; border-top: 1px solid #dfe5ee;'>", unsafe_allow_html=True)

    tab_ver, tab_nuevo = st.tabs(["Buscar", "Agregar"])

    with tab_ver:
        c1, c2 = st.columns(2)
        with c1:
            tipo_f = st.selectbox("Tipo", ["Todos", "caso", "perfil", "expediente"])
        with c2:
            nombre_f = st.text_input("Nombre contiene")

        if st.button("Buscar", use_container_width=True):
            params = {}
            if tipo_f != "Todos":
                params["tipo"] = tipo_f
            if nombre_f:
                params["nombre"] = nombre_f
            try:
                items = api_get("/gestion/sueltos", params=params)
                if items:
                    st.success(f"{len(items)} registro(s) encontrado(s)")
                    df = pd.DataFrame(items)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("Sin resultados")
            except Exception as e:
                st.error(str(e))

    with tab_nuevo:
        with st.form("form_suelto"):
            tipo = st.selectbox("Tipo *", ["caso", "perfil", "expediente"])
            nombre = st.text_input("Nombre *")
            desc = st.text_area("Descripción")
            meta = st.text_area("Metadata JSON", value="{}")
            ok = st.form_submit_button("Guardar", use_container_width=True)

        if ok:
            if not nombre:
                st.error("El nombre es obligatorio")
            else:
                import json

                try:
                    metadata = json.loads(meta)
                    r = api_post(
                        "/gestion/sueltos",
                        {
                            "tipo": tipo,
                            "nombre": nombre,
                            "descripcion": desc,
                            "metadata": metadata,
                        },
                    )
                    st.success(f"Registro guardado correctamente con ID {r['id']}")
                except json.JSONDecodeError:
                    st.error("Metadata no es JSON válido")
                except Exception as e:
                    st.error(str(e))


# ════════════════════════════════════════════════════════════════
# PAGE: MIS CONVERSACIONES
# ════════════════════════════════════════════════════════════════


def page_conversaciones():
    st.markdown("## Historial de conversaciones")
    st.caption("Consulta el registro de interacciones previas del usuario.")
    st.markdown("<hr style='margin: 0.4rem 0 1rem 0; border: 0; border-top: 1px solid #dfe5ee;'>", unsafe_allow_html=True)
    try:
        chats = api_get("/consultas/chats")
    except Exception as e:
        st.error(str(e))
        return

    if not chats:
        st.info("No tienes conversaciones aún.")
        return

    for c in chats:
        with st.expander(
            f"{'🟢' if c['estado'] == 'activo' else '⚫'} {c['titulo'] or 'Sin título'} — {c['updated_at']}"
        ):
            try:
                msgs = api_get(f"/consultas/chats/{c['id']}/mensajes")
                for m in msgs:
                    prefix = "Usuario" if m["rol"] == "usuario" else "Asistente"
                    st.markdown(
                        f"{prefix} **{m['rol'].capitalize()}**: {m['contenido']}"
                    )
                    st.caption(m.get("timestamp", ""))
            except Exception as e:
                st.error(str(e))

            if st.button(f"Eliminar", key=f"del_{c['id']}"):
                try:
                    api_delete(f"/consultas/chats/{c['id']}")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))


def page_admin():
    st.markdown("## Administración")
    st.caption("El registro de usuarios está habilitado únicamente para administradores.")
    st.markdown("<hr style='margin: 0.4rem 0 1rem 0; border: 0; border-top: 1px solid #dfe5ee;'>", unsafe_allow_html=True)

    st.markdown("""
    <div style="background-color:#f4f6fa;padding:14px;border-radius:8px;border:1px solid #dfe5ee;margin-bottom:16px;">
    <strong>Módulo de administración</strong><br>
    Desde aquí se pueden crear nuevas cuentas con permisos definidos para el sistema.
    </div>
    """, unsafe_allow_html=True)

    with st.form("register_user"):
        procuraduria_id = st.number_input(
            "ID de procuraduría", min_value=1, step=1, value=1
        )
        nombre = st.text_input("Nombre completo")
        email = st.text_input("Correo institucional")
        password = st.text_input("Contraseña", type="password")
        rol = st.selectbox("Rol", ["asistente", "procurador"])
        submit = st.form_submit_button("Crear usuario", use_container_width=True)

    if submit:
        if not nombre or not email or not password:
            st.error("Complete todos los campos obligatorios.")
        else:
            try:
                api_post(
                    "/auth/register",
                    {
                        "procuraduria_id": int(procuraduria_id),
                        "nombre": nombre,
                        "email": email,
                        "password": password,
                        "rol": rol,
                    },
                )
                st.success("Usuario creado correctamente.")
            except httpx.HTTPStatusError as e:
                detail = e.response.text
                st.error(
                    "No se pudo crear el usuario."
                    if e.response.status_code == 409
                    else detail
                )
            except Exception as e:
                st.error(f"No se pudo completar el registro: {e}")


# ════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ════════════════════════════════════════════════════════════════

if not st.session_state.token:
    page_login()
else:
    page = sidebar()
    if page == "Asistente legal":
        page_chat()
    elif page == "Expedientes sueltos":
        page_sueltos()
    elif page == "Mis conversaciones":
        page_conversaciones()
    elif page == "Administración":
        page_admin()


def start():
    import subprocess
    import sys

    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])
