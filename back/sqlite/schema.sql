-- Solo una tabla para cumplir con SQL
CREATE TABLE documentos_sueltos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT CHECK(tipo IN ('caso', 'perfil', 'expediente')),
    nombre TEXT NOT NULL,
    descripcion TEXT,
    metadata TEXT,  -- JSON para cualquier cosa extra
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Índice para búsquedas rápidas
CREATE INDEX idx_tipo ON documentos_sueltos(tipo);
CREATE INDEX idx_nombre ON documentos_sueltos(nombre);
