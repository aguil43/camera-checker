# Módulo de Notificaciones (`src/notifier/`)

Este módulo gestiona la creación y envío de alertas por correo electrónico mediante **SMTP** cuando se detecta una anomalía en una cámara de seguridad.

---

## 📂 Archivos del Módulo

| Archivo | Descripción |
| :--- | :--- |
| `email_sender.py` | Cliente SMTP con soporte para TLS/SSL, autenticación, gestión de destinatarios y adjuntos de capturas. |
| `templates.py` | Generador de plantillas HTML y texto plano con diseño responsivo, tablas diagnósticas y badges de estado. |

---

## 🚀 Características del Notificador

1. **Soporte para Servidores SMTP Propios:**
   - Compatible con servidores de correo con dominio personalizado (`mail.tudominio.com`), cPanel, Postfix, Office 365, Gmail y servicios de relay.
   - Soporte para puertos estándar: `587` (STARTTLS), `465` (SSL) y `25` (Sin encriptación interna).

2. **Diseño Visual de las Alertas (`templates.py`):**
   - **Badges por estado:**
     - 🔴 `OFFLINE`: Cámara inaccesible.
     - 🟠 `AUTH_FAILED`: Credenciales incorrectas / 401.
     - 🟡 `NO_RECORDINGS`: Sin grabaciones recientes en el intervalo de 5 minutos.
     - ⚪ `ERROR`: Falla de navegación o timeout.
   - **Resumen diagnóstico:** Nombre de la cámara, IP/URL, fecha/hora del incidente y detalles técnicos.
   - **Captura de pantalla incrustada / adjunta:** La imagen de evidencia se incluye en el cuerpo del correo para rápida inspección visual desde clientes móviles o de escritorio.

3. **Prevención de Spam (*Cooldown*):**
   - Antes de enviar un correo, consulta la tabla `alert_history`. Si ya se despachó una alerta para esa misma cámara y con el mismo estado en las últimas $N$ horas (`COOLDOWN_ALERT_HOURS` en `.env`), se omite el envío duplicado y se registra en logs.
