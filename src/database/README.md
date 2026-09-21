# Módulo de Base de Datos (`src/database/`)

Este módulo proporciona la capa de persistencia mediante **SQLite** y modelos fuertemente tipados con **Pydantic**.

---

## 📂 Archivos del Módulo

| Archivo | Descripción |
| :--- | :--- |
| `connection.py` | Gestión de la conexión SQLite, inicialización automática del esquema y claves foráneas. |
| `models.py` | Definición de enumeraciones (`CameraStatus`, `VendorType`) y modelos Pydantic (`Camera`, `CheckLog`, `AlertHistory`, `RecordingItem`). |
| `repository.py` | Métodos CRUD estáticos para administrar cámaras, consultar logs históricos y verificar el *cooldown* de alertas. |

---

## 🗄️ Esquema de la Base de Datos SQLite

### Tabla: `cameras`
Almacena el catálogo de cámaras registradas para el monitoreo.
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `name` (TEXT NOT NULL)
- `ip_or_url` (TEXT NOT NULL UNIQUE)
- `username` (TEXT NOT NULL DEFAULT 'root')
- `password` (TEXT NOT NULL)
- `vendor_type` (TEXT DEFAULT 'VIVOTEK_MODERN')
- `enabled` (INTEGER DEFAULT 1)
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

### Tabla: `check_logs`
Historial de todas las verificaciones realizadas a cada cámara.
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `camera_id` (INTEGER REFERENCES cameras(id) ON DELETE CASCADE)
- `camera_name` (TEXT NOT NULL)
- `status` (TEXT NOT NULL): `OK`, `NO_RECORDINGS`, `OFFLINE`, `AUTH_FAILED`, `ERROR`.
- `recordings_count` (INTEGER DEFAULT 0)
- `latest_recording_time` (TEXT)
- `details` (TEXT)
- `screenshot_path` (TEXT)
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

### Tabla: `alert_history`
Registro de los correos electrónicos de alerta despachados para control de repetición (*cooldown*).
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `camera_id` (INTEGER REFERENCES cameras(id) ON DELETE CASCADE)
- `status` (TEXT NOT NULL)
- `recipient` (TEXT NOT NULL)
- `sent_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

---

## 💡 Métodos Principales de Repositorio (`repository.py`)

- `CameraRepository.add_camera(...)`: Registra o actualiza una cámara.
- `CameraRepository.get_active_cameras()`: Obtiene la lista de cámaras habilitadas (`enabled = 1`).
- `CameraRepository.toggle_camera(camera_id, enabled)`: Habilita o deshabilita el chequeo de una cámara.
- `CheckLogRepository.add_log(check_log)`: Guarda el resultado del chequeo.
- `AlertRepository.is_in_cooldown(camera_id, status, cooldown_hours)`: Verifica si ya se envió una alerta similar dentro de la ventana de horas configurada (`COOLDOWN_ALERT_HOURS`).
