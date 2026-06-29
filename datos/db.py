import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "lociapro.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS procuradurias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL,
    tipo        TEXT,
    descripcion TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuarios (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    procuraduria_id  INTEGER NOT NULL,
    nombre           TEXT NOT NULL,
    email            TEXT UNIQUE NOT NULL,
    rol              TEXT CHECK(rol IN ('procurador', 'asistente', 'admin')),
    contrasena_hash  TEXT NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (procuraduria_id) REFERENCES procuradurias(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER NOT NULL,
    titulo      TEXT,
    estado      TEXT DEFAULT 'activo' CHECK(estado IN ('activo', 'cerrado', 'archivado')),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mensajes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id   INTEGER NOT NULL,
    rol       TEXT NOT NULL CHECK(rol IN ('usuario', 'asistente', 'sistema')),
    contenido TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata  TEXT,
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documentos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT NOT NULL,
    descripcion  TEXT,
    ruta_archivo TEXT,
    tipo_mime    TEXT,
    tamanio      INTEGER,
    metadata     TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mensaje_documento (
    mensaje_id   INTEGER NOT NULL,
    documento_id INTEGER NOT NULL,
    PRIMARY KEY (mensaje_id, documento_id),
    FOREIGN KEY (mensaje_id)   REFERENCES mensajes(id)   ON DELETE CASCADE,
    FOREIGN KEY (documento_id) REFERENCES documentos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documentos_sueltos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo         TEXT CHECK(tipo IN ('caso', 'perfil', 'expediente')),
    nombre       TEXT NOT NULL,
    descripcion  TEXT,
    metadata     TEXT,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mensajes_chat_id  ON mensajes(chat_id);
CREATE INDEX IF NOT EXISTS idx_mensajes_timestamp ON mensajes(timestamp);
CREATE INDEX IF NOT EXISTS idx_chats_usuario_id  ON chats(usuario_id);
CREATE INDEX IF NOT EXISTS idx_documentos_nombre ON documentos(nombre);
CREATE INDEX IF NOT EXISTS idx_sueltos_tipo      ON documentos_sueltos(tipo);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.executescript(SCHEMA)


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    d[k] = parsed
            except (json.JSONDecodeError, ValueError):
                pass
    return d
