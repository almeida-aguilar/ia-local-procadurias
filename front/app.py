import json
import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st

# 🔧 Agregar 'back/' al path  (front/app.py está un nivel más abajo que la raíz)
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_ROOT, "back"))

from rag.buscar import consultar_rag
from sqlite.buscar import buscar_sueltos
from sqlite.insertar import insertar_suelto  # ✅ importación correcta

# ⚙️ Configuración de la página
st.set_page_config(
    page_title="Cerebro Digital - Asistente Legal",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .main-header { font-size: 2.5rem; color: #1E3A8A; text-align: center; margin-bottom: 1rem; }
        .sub-header  { font-size: 1.2rem; color: #475569; text-align: center; }
    </style>
    """,
    unsafe_allow_html=True,
)

# 🧠 Sidebar
with st.sidebar:
    st.title("⚖️ Cerebro Digital")
    st.markdown("---")
    st.markdown("**Estado del Sistema**")
    st.success("✅ RAG (FAISS) activo")
    st.info("📄 SQLite documentos sueltos activo")
    st.markdown("---")
    st.caption("v1.0 - Proyecto PC3 Redes y Protocolos")
    st.caption("Sede Central: Palacio de Justicia - Lima")

tab1, tab2, tab3 = st.tabs(
    [
        "🤖 Asistente Legal (RAG)",
        "📂 Buscar Documentos Sueltos",
        "📝 Agregar Documento Suelto",
    ]
)

# ================================================================
# TAB 1: ASISTENTE LEGAL (RAG)
# ================================================================
with tab1:
    st.markdown(
        '<p class="main-header">🤖 Consulta Jurídica con IA</p>', unsafe_allow_html=True
    )
    st.markdown(
        '<p class="sub-header">Basado en la Constitución, Códigos y jurisprudencia peruana</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Buenos días. Soy el asistente legal del 'Cerebro Digital'. ¿En qué puedo ayudarle con la legislación peruana?",
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escribe tu consulta legal aquí..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🔍 Buscando en expedientes y jurisprudencia..."):
                try:
                    respuesta = consultar_rag(prompt)
                    if not respuesta or len(respuesta) < 5:
                        respuesta = "No encontré información específica. Reformule su consulta o verifique que el índice FAISS esté generado."
                    st.markdown(respuesta)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": respuesta}
                    )
                except Exception as e:
                    st.error(f"❌ Error al consultar la IA: {e}")
                    st.info(
                        "Asegúrese de que Ollama esté corriendo (`ollama serve`) y el modelo `llama3.2` descargado."
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": f"Error: {e}"}
                    )

    if st.button("🗑️ Limpiar conversación"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Conversación reiniciada. ¿En qué puedo ayudarle?",
            }
        ]
        st.rerun()

# ================================================================
# TAB 2: BUSCAR DOCUMENTOS SUELTOS
# ================================================================
with tab2:
    st.markdown(
        '<p class="main-header">📂 Documentos Sueltos</p>', unsafe_allow_html=True
    )
    st.markdown("Casos, perfiles y expedientes almacenados en SQLite")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        tipo_filter = st.selectbox(
            "Filtrar por tipo", ["Todos", "caso", "perfil", "expediente"]
        )
    with col2:
        nombre_filter = st.text_input(
            "Filtrar por nombre (contiene)", placeholder="Ej: Rodríguez"
        )

    if st.button("🔍 Buscar", use_container_width=True):
        with st.spinner("Consultando SQLite..."):
            try:
                tipo_param = None if tipo_filter == "Todos" else tipo_filter
                nombre_param = nombre_filter if nombre_filter else None
                resultados = buscar_sueltos(
                    tipo=tipo_param, nombre_contiene=nombre_param
                )

                if resultados:
                    df = pd.DataFrame(resultados)
                    st.success(f"✅ Se encontraron {len(resultados)} registros")
                    st.dataframe(df, use_container_width=True)
                    for row in resultados:
                        with st.expander(
                            f"📄 {row.get('nombre', 'Sin nombre')} (ID: {row.get('id', 'N/A')})"
                        ):
                            st.json(row)
                else:
                    st.warning("⚠️ No se encontraron documentos con esos filtros.")
            except Exception as e:
                st.error(f"❌ Error al buscar en SQLite: {e}")

# ================================================================
# TAB 3: AGREGAR DOCUMENTO SUELTO
# ================================================================
with tab3:
    st.markdown(
        '<p class="main-header">📝 Agregar Nuevo Documento Suelto</p>',
        unsafe_allow_html=True,
    )
    st.markdown("Ingrese la información de un nuevo caso, perfil o expediente.")
    st.markdown("---")

    with st.form("form_agregar_suelto"):
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo de documento *", ["caso", "perfil", "expediente"])
            nombre = st.text_input(
                "Nombre *", placeholder="Ej: Caso Rodríguez vs Estado"
            )
        with col2:
            descripcion = st.text_area(
                "Descripción", placeholder="Breve resumen del documento..."
            )
            metadata_str = st.text_area(
                "Metadatos (JSON)",
                placeholder='{"juzgado": "Lima", "año": 2024, "estado": "activo"}',
                value="{}",
            )

        submitted = st.form_submit_button(
            "💾 Guardar en SQLite", use_container_width=True
        )
        if submitted:
            if not nombre:
                st.error("❌ El campo 'Nombre' es obligatorio.")
            else:
                try:
                    metadata = json.loads(metadata_str) if metadata_str else {}
                    nuevo_id = insertar_suelto(tipo, nombre, descripcion, metadata)
                    st.success(
                        f"✅ Documento insertado correctamente con ID: {nuevo_id}"
                    )
                    st.balloons()
                except json.JSONDecodeError:
                    st.error(
                        "❌ El formato de Metadatos no es JSON válido. Revise comillas y llaves."
                    )
                except Exception as e:
                    st.error(f"❌ Error al guardar: {e}")
