"""Demo de Capa de Datos - RAG + SQLite para curso de Redes"""

import os
import sys

# Asegurar que 'back/' esté en el path al correr desde la raíz del proyecto
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "back"))

from rag.buscar import consultar_rag

# ✅ insertar_suelto vive en sqlite/insertar.py, no en sqlite/buscar.py
from sqlite.buscar import buscar_sueltos
from sqlite.insertar import insertar_suelto

# 1. Agregar casos de ejemplo
print("Insertando datos de ejemplo...")
insertar_suelto(
    "caso",
    "Rodríguez vs Empresa X",
    "Despido laboral en 2023",
    {"juzgado": "Lima", "estado": "cerrado"},
)
insertar_suelto(
    "perfil",
    "Abogado Juan Pérez",
    "Especialista en penal",
    {"años_exp": 10},
)
insertar_suelto(
    "expediente",
    "Exp-2024-001",
    "Caso de divorcio contencioso",
    {"juzgado": "Callao"},
)

# 2. Consultas SQL
print("\n" + "=" * 50)
print("📁 DOCUMENTOS SUELTOS (SQLite)")
print("=" * 50)
resultados_sql = buscar_sueltos(tipo="caso")
for r in resultados_sql:
    print(f"- {r['nombre']}: {r['descripcion']}")

# 3. Consulta RAG
print("\n" + "=" * 50)
print("⚖️  CONSULTA RAG (Leyes Peruanas)")
print("=" * 50)
pregunta = "¿Qué dice la Constitución sobre la igualdad ante la ley?"
respuesta = consultar_rag(pregunta)
print(f"Pregunta: {pregunta}")
print(f"Respuesta: {respuesta}")

print("\n✅ Capa de Datos funcionando: RAG (FAISS) + SQLite")
