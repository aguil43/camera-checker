# Módulo Principal (`src/`)

Este directorio contiene el núcleo del sistema automatizado de verificación y monitoreo de cámaras de seguridad IP. La arquitectura está desacoplada en cuatro módulos especializados:

---

## 📁 Estructura del Código

```text
src/
├── checker/      # Automatización de navegación web (Playwright) y detección de interfaces
├── database/     # Modelos de datos, conexión SQLite y capa de persistencia (Repository)
├── notifier/     # Despacho de alertas por correo SMTP con capturas adjuntas y plantillas HTML
└── utils/        # Parsers de fecha/hora, helpers y sistema de logging
```

---

## 🔄 Flujo de Ejecución del Sistema

1. **Recuperación de Cámaras (`src/database`):**
   - El sistema carga las cámaras activas registradas en la base de datos SQLite.

2. **Automatización Web (`src/checker`):**
   - `browser_engine.py` lanza una instancia de Chromium (Headless o Visible) configurando las credenciales HTTP (Basic/Digest) para el diálogo nativo del navegador.
   - `camera_checker.py` se conecta a la URL de la cámara y detecta automáticamente el tipo de interfaz web:
     - **Moderna (Quasar/Vue):** Navega a `#/file_general`, abre la modal de fecha/hora, selecciona *Custom time interval*, calcula y resta 5 minutos a la hora de la cámara y ejecuta la búsqueda.
     - **Clásica (VIVOTEK `/setup/`):** Navega a `storage_searching.html`, escribe `5` en el campo de minutos, presiona `minute(s)` para recalcular las horas y pulsa `Search`.
   - Verifica la presencia de grabaciones en los resultados de la búsqueda.
   - En caso de anomalía (`OFFLINE`, `AUTH_FAILED`, `NO_RECORDINGS`, `ERROR`), toma una captura de pantalla como evidencia.

3. **Registro y Auditoría (`src/database`):**
   - Guarda el resultado del chequeo en la tabla `check_logs`.

4. **Notificación de Incidentes (`src/notifier`):**
   - Si el estado no es `OK` y no se encuentra en período de *cooldown*, se genera un correo HTML responsivo con la captura adjunta y se despacha vía SMTP.

---

## 📖 Documentación por Módulo

Para más detalles sobre la implementación y funcionamiento de cada componente, consulta sus respectivos README:
- [src/checker/README.md](checker/README.md): Automatización web, selectores y detección de interfaces.
- [src/database/README.md](database/README.md): Esquema SQLite, modelos Pydantic y repositorios.
- [src/notifier/README.md](notifier/README.md): Servicio de correo SMTP, plantillas HTML y cooldown.
- [src/utils/README.md](utils/README.md): Normalización de fechas y configuración de logs.
