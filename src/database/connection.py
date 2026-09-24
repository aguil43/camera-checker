import sqlite3
from pathlib import Path
from config.config import settings
from src.utils.logger import logger

def get_db_connection() -> sqlite3.Connection:
    """Retorna una conexión a la base de datos SQLite configurada con row_factory."""
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa el esquema de la base de datos si no existe."""
    settings.ensure_directories()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabla cameras
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cameras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        ip_or_url TEXT NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        vendor_type TEXT NOT NULL DEFAULT 'vivotek',
        interface INTEGER NOT NULL DEFAULT 1,
        enabled BOOLEAN NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Migración automática: verificar si la columna 'interface' existe
    cursor.execute("PRAGMA table_info(cameras)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "interface" not in columns:
        cursor.execute("ALTER TABLE cameras ADD COLUMN interface INTEGER NOT NULL DEFAULT 1;")
        logger.info("Migración aplicada: Columna 'interface' agregada a la tabla cameras (Default: 1)")

    # Tabla check_logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS check_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        camera_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        recordings_count INTEGER DEFAULT 0,
        latest_recording_time TEXT,
        details TEXT,
        screenshot_path TEXT,
        checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (camera_id) REFERENCES cameras (id) ON DELETE CASCADE
    );
    """)

    # Tabla alert_history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alert_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        camera_id INTEGER NOT NULL,
        alert_type TEXT NOT NULL,
        recipient TEXT NOT NULL,
        details TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (camera_id) REFERENCES cameras (id) ON DELETE CASCADE
    );
    """)

    # Índices para consultas rápidas
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_camera ON check_logs(camera_id, checked_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_camera ON alert_history(camera_id, sent_at);")

    conn.commit()
    conn.close()
    logger.debug("Base de datos SQLite inicializada correctamente en %s", settings.DB_PATH)

if __name__ == "__main__":
    init_db()
