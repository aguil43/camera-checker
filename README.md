# Sistema Automatizado de Chequeo de Cámaras IP

Sistema en **Python** para la verificación y monitoreo automatizado de cámaras de seguridad (especializado en interfaces **VIVOTEK** basadas en Quasar/Vue y clásicas), autenticación en cuadros de diálogo HTTP Popup (Basic/Digest), validación de grabaciones activas, persistencia en **SQLite** y despacho de alertas por **correo electrónico (SMTP)** con dominio personalizado.

---

## Características Principales

- **Automatización Web con Playwright:**
  - Manejo nativo y transparente de credenciales popup (`root` y contraseña).
  - Bypass de advertencias de seguridad SSL / conexión no segura.
  - Navegación optimizada a la sección de archivos (`/home.html#/file_general`).
- **Verificación Rápida de Grabaciones (Intervalo de 5 Minutos):**
  - Configura automáticamente el filtro **`Custom time interval`** en la ventana **`Date & Time`**.
  - Resta 5 minutos a la hora actual de la cámara para realizar una consulta ligera y ultrarrápida (~10-15s), evitando sobrecargar el procesador o almacenamiento de la cámara.
- **Base de Datos SQLite:**
  - Registro de cámaras (`cameras`), historial de chequeos (`check_logs`) y auditoría de alertas (`alert_history`).
- **Sistema de Alertas por Correo SMTP:**
  - Alertas automáticas para incidentes:
    - `OFFLINE`: Cámara inaccesible o error de conexión.
    - `AUTH_FAILED`: Contraseña incorrecta o error 401.
    - `NO_RECORDINGS`: Cero grabaciones en el intervalo verificado.
    - `ERROR`: Timeout o error de navegación.
  - Plantillas HTML profesionales y responsivas con **captura de pantalla adjunta como evidencia**.
  - Control de *cooldown* para evitar saturación de correos repetidos.
- **Herramientas de Ejecución:**
  - **CLI interactivo (`cli.py`):** Para registrar, listar, eliminar cámaras y ejecutar pruebas en vivo en pantalla (`--visible`).
  - **Main Runner (`main.py`):** Para chequeo por lotes o ejecución continua como servicio (*daemon*).

---

## Estructura del Proyecto

```text
camera-checker/
│
├── config/
│   └── config.py              # Configuración y variables de entorno
│
├── src/
│   ├── database/
│   │   ├── connection.py      # Conexión SQLite y esquema de tablas
│   │   ├── models.py          # Modelos de datos Pydantic y estados
│   │   └── repository.py      # Operaciones CRUD para cámaras, logs y alertas
│   │
│   ├── checker/
│   │   ├── browser_engine.py  # Gestor de Playwright Chromium
│   │   ├── camera_checker.py  # Lógica de navegación, modal de tiempo y validación
│   │   └── selectors.py       # Selectores XPath y Quasar para VIVOTEK
│   │
│   ├── notifier/
│   │   ├── email_sender.py    # Despachador SMTP con TLS/SSL y adjuntos
│   │   └── templates.py       # Plantillas HTML responsivas para alertas
│   │
│   └── utils/
│       ├── date_parser.py     # Parser de fechas de grabaciones
│       └── logger.py          # Logging rotativo y en consola
│
├── cli.py                     # CLI para gestión de cámaras y pruebas
├── main.py                    # Ejecutor de monitoreo en lote y modo daemon
├── requirements.txt           # Dependencias del proyecto
├── .env.example               # Plantilla de configuración
├── .env                       # Configuración local con credenciales
└── .gitignore                 # Exclusiones de git (datos, logs, capturas)
```

---

## Instalación y Configuración

### 1. Clonar el repositorio e instalar dependencias:
```bash
pip install -r requirements.txt
```

### 2. Instalar el navegador Chromium de Playwright:
```bash
python -m playwright install chromium
```

### 3. Configurar el archivo `.env`:
Copia `.env.example` a `.env` (si aún no existe) y define tus parámetros SMTP y preferencias:
```ini
# Configuración SMTP (Correo corporativo)
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

# Tiempos de espera (milisegundos)
PAGE_LOAD_TIMEOUT_MS=60000
ELEMENT_WAIT_TIMEOUT_MS=30000
SEARCH_WAIT_TIMEOUT_MS=75000
```

### 4. Inicializar la base de datos SQLite:
```bash
python cli.py init-db
```

---

## Uso de la Herramienta CLI (`cli.py`)

### Probar una URL directamente (sin guardar en base de datos):
```bash
python cli.py test-url --url "http://fwcdnazas.mine.nu" --username "root" --visible
```
> **Nota:** El parámetro `--visible` abre la ventana de Chromium en tu pantalla para observar todo el proceso en tiempo real.

### Registrar una cámara en la base de datos:
```bash
python cli.py add
```
*(Solicita de forma interactiva el nombre, URL/IP, usuario y contraseña).*

O mediante parámetros:
```bash
python cli.py add --name "Cámara CDN" --url "http://fwcdnazas.mine.nu" --username "root"
```

### Listar cámaras registradas:
```bash
python cli.py list
```

### Probar una cámara registrada por su ID:
```bash
python cli.py test 1 --visible
```

### Ver historial de chequeos recientes:
```bash
python cli.py logs --limit 20
```

### Probar la configuración del servidor de correo SMTP:
```bash
python cli.py test-email --to "tu_correo@tudominio.com"
```

---

## Ejecución del Monitor Automático (`main.py`)

### Chequeo único de todas las cámaras activas (para Tarea Programada de Windows):
```bash
python main.py
```

### Monitoreo continuo en segundo plano (cada 24 horas o intervalo deseado):
```bash
python main.py --daemon --interval 24
```
