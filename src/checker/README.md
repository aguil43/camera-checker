# Módulo de Chequeo Web (`src/checker/`)

Este módulo se encarga de la automatización del navegador web mediante **Playwright** para interactuar con las cámaras IP, autenticarse, identificar la versión de firmware e interfaz, y validar si existen grabaciones en el intervalo solicitado.

---

## 📂 Archivos del Módulo

| Archivo | Descripción |
| :--- | :--- |
| `browser_engine.py` | Administrador del ciclo de vida de Playwright Chromium (`launch`, `new_context`, `http_credentials`). |
| `camera_checker.py` | Lógica principal de orquestación, detección de interfaz y verificación de grabaciones. |
| `selectors.py` | Catálogo centralizado de selectores (CSS, XPath y Quasar) para cada tipo de interfaz. |

---

## 🧭 Interfaces Web Soportadas

El sistema clasifica automáticamente la interfaz de la cámara al iniciar la conexión:

### 1. Interfaz Moderna (Quasar Framework / Vue.js)
- **Ruta típica:** `http://<ip_o_url>/home.html#/file_general`
- **Flujo de verificación:**
  1. Abre el selector desplegable de marco de tiempo (`Time frame`).
  2. Selecciona la opción **`Custom time interval`** que despliega el modal `Date & Time` (`.q-dialog`).
  3. Lee la fecha y hora final mostrada por la cámara en los campos *End Time*.
  4. Resta 5 minutos a la hora de la cámara y los ingresa en los campos *Start Time* (para evitar desfaces entre la hora del servidor y la hora de la cámara).
  5. Pulsa el botón `Save` en el diálogo y luego el botón `Search`.
  6. Espera la desaparición del spinner de carga (`.q-loading`) y extrae los registros de la tabla `.q-table tbody tr`.

### 2. Interfaz Clásica (VIVOTEK Firmware Tradicional)
- **Ruta típica:** `http://<ip_o_url>/setup/localstorage/storage_searching.html`
- **Flujo de verificación:**
  1. Navega a la sección de búsqueda de almacenamiento (directamente por URL o a través del menú lateral `Configuration` > `Storage` > `Content management`).
  2. Ingresa `5` en el campo de texto `Search for last [ ] minute(s)`.
  3. Hace clic en el botón `minute(s)` para que el script interno de la cámara recalcule automáticamente los campos `From:` y `to:`.
  4. Presiona el botón `Search`.
  5. Ejecuta una inspección multi-frame en el DOM buscando filas o registros con marcadores activos (`Today at`, `Yesterday at`, `Motion`, `SD`, `mov`).
  6. Si se visualiza al menos un registro en la tabla tras la búsqueda de 5 minutos, confirma el estado como **`OK`**.

---

## 🛡️ Manejo de Autenticación y Seguridad

- **Popup HTTP Basic/Digest:** Playwright maneja las credenciales a nivel de contexto de red mediante `http_credentials={"username": ..., "password": ...}`, evitando que el cuadro de diálogo modal del navegador bloquee la ejecución.
- **Bypass SSL:** Se configuran las opciones `ignore_https_errors=True` para cámaras que utilizan certificados autofirmados o conexiones HTTP simples.
- **Capturas de Evidencia:** Ante cualquier anomalía (`OFFLINE`, `AUTH_FAILED`, `NO_RECORDINGS`, `ERROR`), se genera automáticamente una captura de pantalla guardada en `data/screenshots/`.
