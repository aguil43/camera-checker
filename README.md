# Sistema Automatizado de Chequeo de Cámaras IP

Sistema en **Python** para la verificación, monitoreo y diagnóstico automatizado de cámaras de seguridad IP (con soporte y auto-detección para interfaces **VIVOTEK Modernas en Quasar/Vue** e **Interfaces Clásicas de Firmware Tradicional**), autenticación HTTP Popup (Basic/Digest), validación de grabaciones activas de los últimos 5 minutos, persistencia en **SQLite** y despacho de alertas por **correo electrónico (SMTP)** con dominio personalizado y captura de evidencia adjunta.

---

## 🚀 Características Principales

- **Automatización Web con Playwright:**
  - Manejo nativo y transparente de credenciales popup (`root` y contraseña).
  - Bypass de advertencias de seguridad SSL / conexión no segura (`ignore_https_errors`).
  - Auto-detección inteligente del tipo de interfaz web de la cámara (**Moderna** vs **Clásica**).
- **Auto-Detección y Soporte Multi-Interfaz:**
  - **Interfaz Moderna (Quasar/Vue):** Navega a `#/file_general`, abre la modal de fecha/hora, calcula y resta 5 minutos a la hora actual de la cámara, aplica el filtro *Custom time interval* y consulta la tabla `.q-table`.
  - **Interfaz Clásica (`/setup/`):** Navega a `storage_searching.html`, ingresa `5` minutos, pulsa el botón `minute(s)` para recalcular las horas de búsqueda, presiona `Search` y valida la presencia de filas en la tabla de resultados.
- **Verificación Rápida y Ligera (Filtro de 5 Minutos):**
  - En lugar de consultar 24 horas continuas (lo cual puede saturar la CPU o tarjeta SD de la cámara), filtra los últimos 5 minutos, logrando verificaciones ultrarrápidas (~10 a 20 segundos).
- **Base de Datos SQLite:**
  - Registro de cámaras (`cameras`), historial de chequeos (`check_logs`) y auditoría de alertas con control de repetición (`alert_history`).
- **Sistema de Alertas por Correo SMTP:**
  - Alertas automáticas para incidentes:
    - 🔴 `OFFLINE`: Cámara inaccesible o caída de red.
    - 🟠 `AUTH_FAILED`: Contraseña incorrecta o error 401.
    - 🟡 `NO_RECORDINGS`: Cero grabaciones en el intervalo verificado.
    - ⚪ `ERROR`: Timeout o error de navegación.
  - Plantillas HTML profesionales y responsivas con **captura de pantalla adjunta como evidencia**.
  - Control de *cooldown* (`COOLDOWN_ALERT_HOURS`) para evitar saturación de correos repetidos.
- **Herramientas de Ejecución:**
  - **CLI interactivo (`cli.py`):** Para registrar, listar, eliminar cámaras y ejecutar pruebas en vivo en pantalla (`--visible`).
  - **Main Runner (`main.py`):** Para chequeo por lotes o ejecución continua como servicio (*daemon*).

---

## 📁 Estructura del Proyecto

```text
camera-checker/
│
├── config/
│   └── config.py              # Configuración y carga de variables de entorno (.env)
│
├── src/
│   ├── README.md              # Documentación general de la arquitectura del código
│   │
│   ├── checker/               # Módulo de automatización web y Playwright
│   │   ├── README.md          # Documentación detallada del módulo checker
│   │   ├── browser_engine.py  # Gestor del navegador Playwright Chromium
│   │   ├── camera_checker.py  # Detección de interfaz, modal de tiempo y validación
│   │   └── selectors.py       # Selectores XPath, CSS y Quasar
│   │
│   ├── database/              # Módulo de base de datos y persistencia
│   │   ├── README.md          # Documentación detallada del módulo database
│   │   ├── connection.py      # Conexión SQLite y esquema de tablas
│   │   ├── models.py          # Modelos de datos Pydantic y enumeraciones
│   │   └── repository.py      # Operaciones CRUD para cámaras, logs y alertas
│   │
│   ├── notifier/              # Módulo de alertas y correo
│   │   ├── README.md          # Documentación detallada del módulo notifier
│   │   ├── email_sender.py    # Despachador SMTP con TLS/SSL y adjuntos
│   │   └── templates.py       # Plantillas HTML responsivas para alertas
│   │
│   └── utils/                 # Módulo de utilidades transversales
│       ├── README.md          # Documentación detallada del módulo utils
│       ├── date_parser.py     # Normalizador de fechas de grabaciones
│       └── logger.py          # Logging rotativo y en consola
│
├── tests/
│   └── test_components.py     # Pruebas unitarias de modelos, base de datos y utilidades
│
├── cli.py                     # CLI interactivo para gestión y pruebas
├── main.py                    # Ejecutor principal (por lotes o daemon)
├── requirements.txt           # Dependencias del proyecto
├── .env.example               # Plantilla de configuración
├── .env                       # Configuración local con credenciales (ignorado en git)
└── .gitignore                 # Exclusiones de git (datos, logs, capturas, temporales)
```

---

## ⚙️ Instalación y Configuración

### 1. Clonar el repositorio e instalar dependencias:
```bash
pip install -r requirements.txt
```

### 2. Instalar el navegador Chromium de Playwright:
```bash
python -m playwright install chromium
```

### 3. Configurar el archivo `.env`:
Copia `.env.example` a `.env` (si aún no existe) y ajusta los parámetros de tu servidor SMTP y preferencias:
```ini
# Configuración SMTP (Servidor de correo propio o corporativo)
SMTP_HOST=mail.tudominio.com
SMTP_PORT=587
SMTP_USER=alertas@tudominio.com
SMTP_PASSWORD=tu_contrasena
SMTP_USE_TLS=False
SMTP_USE_SSL=False

EMAIL_FROM=Monitor de Camaras <alertas@tudominio.com>
EMAIL_TO=admin@tudominio.com

# Intervalo de verificación rápida (en minutos)
CUSTOM_INTERVAL_MINUTES=5

# Horas de espera antes de repetir una misma alerta (cooldown)
COOLDOWN_ALERT_HOURS=4

# Tiempos de espera para cámaras con hardware lento (milisegundos)
PAGE_LOAD_TIMEOUT_MS=60000
ELEMENT_WAIT_TIMEOUT_MS=30000
SEARCH_WAIT_TIMEOUT_MS=75000
```

### 4. Inicializar la base de datos SQLite:
```bash
python cli.py init-db
```

---

## 🖥️ Uso de la Herramienta CLI (`cli.py`)

### Probar una URL directamente (sin guardar en base de datos):
```bash
# Cámara con interfaz moderna (Quasar - interface=1)
python cli.py test-url --url "http://fwcdnazas.mine.nu" --username "root" --interface 1 --visible

# Cámara con interfaz clásica (VIVOTEK tradicional - interface=0)
python cli.py test-url --url "http://fwcoyote.mine.nu" --username "root" --interface 0 --visible
```
> **Nota:** El parámetro opcional `--visible` abre la ventana del navegador en pantalla para ver el flujo en tiempo real.

### Registrar una cámara en la base de datos:
```bash
python cli.py add
```
*(Solicita interactivamente el nombre, URL/IP, usuario, contraseña y tipo de interfaz: `1`=Moderna, `0`=Clásica).*

O mediante parámetros:
```bash
python cli.py add --name "Cámara Cemento" --url "http://fwcemento.mine.nu" --username "root" --interface 1
```

### Listar cámaras registradas y su tipo de interfaz:
```bash
python cli.py list
```

### Cambiar tipo de interfaz de una cámara registrada:
```bash
# Cambiar cámara #4 a interfaz clásica (0)
python cli.py set-interface 4 0

# Cambiar cámara #1 a interfaz moderna (1)
python cli.py set-interface 1 1
```

### Probar una cámara registrada por su ID:
```bash
python cli.py test 1 --visible
```

### Habilitar / Deshabilitar una cámara:
```bash
python cli.py toggle 1
```

### Ver historial de chequeos recientes:
```bash
python cli.py logs --limit 20
```

### Probar la conexión del servidor de correo SMTP:
```bash
python cli.py test-email --to "tu_correo@tudominio.com"
```

---

## ⏱️ Ejecución del Monitor Automático (`main.py`)

### Chequeo único de todas las cámaras activas:
Ideal para ejecutarse como **Tarea Programada de Windows (Task Scheduler)** o **Cron en Linux**:
```bash
python main.py
```

### Monitoreo continuo en segundo plano (Modo Daemon):
```bash
# Chequeo continuo cada 24 horas (o el número de horas deseado)
python main.py --daemon --interval 24
```

---

## 🧪 Ejecución de Pruebas Unitarias

Para ejecutar el conjunto de pruebas automáticas del sistema:
```bash
python -m unittest tests/test_components.py
```
