# Módulo de Utilidades (`src/utils/`)

Este módulo proporciona utilidades de soporte transversal utilizadas por todos los componentes del sistema, incluyendo análisis de fechas y sistema de logging.

---

## 📂 Archivos del Módulo

| Archivo | Descripción |
| :--- | :--- |
| `date_parser.py` | Parser y normalizador de fechas y marcas de tiempo de las interfaces de las cámaras. |
| `logger.py` | Sistema de logging centralizado con salida en consola a color y archivo de log rotativo. |

---

## 🛠️ Detalles de Implementación

### `date_parser.py`
Convierte cadenas de texto de fecha mostradas por las cámaras a objetos `datetime` de Python. Soporta formatos como:
- **Formatos Relativos de VIVOTEK:**
  - `"Today at 5:04 PM"` -> Fecha actual a las 17:04:00.
  - `"Yesterday at 11:30 AM"` -> Fecha de ayer a las 11:30:00.
- **Nombres de archivo estándar de VIVOTEK:**
  - `"movFWcemento_20260920_165318_0.mp4"` -> `2026-09-20 16:53:18`.
- **Formatos estándar:**
  - `YYYY/MM/DD HH:MM:SS`, `YYYY-MM-DD HH:MM:SS`, `DD/MM/YYYY HH:MM:SS`.

### `logger.py`
- Genera logs estructurados con formato: `[YYYY-MM-DD HH:MM:SS] [NIVEL] [MÓDULO]: MENSAJE`.
- Escribe simultáneamente en la consola y en el archivo `data/logs/checker.log`.
- Configurable en niveles `DEBUG`, `INFO`, `WARNING`, `ERROR` y `CRITICAL`.
