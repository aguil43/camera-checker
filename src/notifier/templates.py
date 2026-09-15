from datetime import datetime
from jinja2 import Template
from src.database.models import Camera, CheckLog, CameraStatus

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Alerta de Cámara de Seguridad</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #f4f6f9;
      margin: 0;
      padding: 24px;
      color: #1f2937;
    }
    .container {
      max-width: 650px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      border: 1px solid #e5e7eb;
    }
    .header {
      padding: 24px;
      text-align: center;
      color: #ffffff;
      background: {{ header_bg }};
    }
    .header h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }
    .badge {
      display: inline-block;
      margin-top: 10px;
      padding: 4px 12px;
      background: rgba(255, 255, 255, 0.25);
      border-radius: 20px;
      font-size: 13px;
      font-weight: 600;
      text-transform: uppercase;
    }
    .content {
      padding: 24px;
    }
    .alert-box {
      background-color: {{ alert_box_bg }};
      border-left: 4px solid {{ alert_border }};
      padding: 14px 16px;
      border-radius: 6px;
      margin-bottom: 20px;
      font-size: 14px;
      line-height: 1.5;
    }
    .info-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 20px;
    }
    .info-table th, .info-table td {
      padding: 10px 12px;
      text-align: left;
      border-bottom: 1px solid #f1f5f9;
      font-size: 14px;
    }
    .info-table th {
      color: #64748b;
      width: 35%;
      font-weight: 600;
    }
    .info-table td {
      color: #0f172a;
      font-weight: 500;
    }
    .screenshot-card {
      margin-top: 20px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 12px;
      background: #fafafa;
      text-align: center;
    }
    .screenshot-card h3 {
      margin: 0 0 10px 0;
      font-size: 13px;
      color: #64748b;
      text-transform: uppercase;
    }
    .screenshot-card img {
      max-width: 100%;
      height: auto;
      border-radius: 6px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    .footer {
      background: #f8fafc;
      padding: 16px;
      text-align: center;
      font-size: 12px;
      color: #94a3b8;
      border-top: 1px solid #e2e8f0;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>SISTEMA DE MONITOREO DE CÁMARAS</h1>
      <div class="badge">{{ status_title }}</div>
    </div>
    <div class="content">
      <div class="alert-box">
        <strong>Diagnóstico:</strong> {{ log.details }}
      </div>

      <table class="info-table">
        <tr>
          <th>Cámara:</th>
          <td><strong>{{ camera.name }}</strong></td>
        </tr>
        <tr>
          <th>Dirección / IP:</th>
          <td><code>{{ camera.ip_or_url }}</code></td>
        </tr>
        <tr>
          <th>Estado Detectado:</th>
          <td><strong style="color: {{ alert_border }};">{{ log.status.value }}</strong></td>
        </tr>
        <tr>
          <th>Grabaciones en 24h:</th>
          <td>{{ log.recordings_count }} archivos</td>
        </tr>
        <tr>
          <th>Último Registro:</th>
          <td>{{ log.latest_recording_time or 'Ninguno detectado' }}</td>
        </tr>
        <tr>
          <th>Fecha de Chequeo:</th>
          <td>{{ checked_at_str }}</td>
        </tr>
      </table>

      {% if has_screenshot %}
      <div class="screenshot-card">
        <h3>Captura de Evidencia al Momento del Chequeo</h3>
        <img src="cid:screenshot_evidence" alt="Captura de Pantalla">
      </div>
      {% endif %}
    </div>
    <div class="footer">
      Este es un mensaje automático generado por el servicio de verificación de cámaras IP.
    </div>
  </div>
</body>
</html>
"""

def render_email_template(camera: Camera, log: CheckLog, has_screenshot: bool = False) -> tuple[str, str, str]:
    """Genera el asunto, cuerpo HTML y texto plano para el correo de alerta."""
    status = log.status

    if status == CameraStatus.OFFLINE:
        subject = f"🔴 [ALERTA] Cámara Fuera de Línea: {camera.name}"
        status_title = "Cámara Inaccesible / Fuera de Línea"
        header_bg = "linear-gradient(135deg, #dc2626 0%, #991b1b 100%)"
        alert_box_bg = "#fef2f2"
        alert_border = "#dc2626"
    elif status == CameraStatus.AUTH_FAILED:
        subject = f"🔒 [ALERTA] Error de Autenticación en Cámara: {camera.name}"
        status_title = "Fallo de Acceso / Contraseña Incorrecta"
        header_bg = "linear-gradient(135deg, #ea580c 0%, #c2410c 100%)"
        alert_box_bg = "#fff7ed"
        alert_border = "#ea580c"
    elif status == CameraStatus.NO_RECORDINGS:
        subject = f"⚠️ [ALERTA] Sin Grabaciones Recientes: {camera.name}"
        status_title = "Sin Grabaciones en las Últimas 24 Horas"
        header_bg = "linear-gradient(135deg, #d97706 0%, #b45309 100%)"
        alert_box_bg = "#fffbeb"
        alert_border = "#d97706"
    else:
        subject = f"❌ [INCIDENTE] Error en Chequeo de Cámara: {camera.name}"
        status_title = "Error en Chequeo Automático"
        header_bg = "linear-gradient(135deg, #4b5563 0%, #1f2937 100%)"
        alert_box_bg = "#f3f4f6"
        alert_border = "#4b5563"

    checked_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    template = Template(HTML_TEMPLATE)
    html_content = template.render(
        camera=camera,
        log=log,
        status_title=status_title,
        header_bg=header_bg,
        alert_box_bg=alert_box_bg,
        alert_border=alert_border,
        checked_at_str=checked_at_str,
        has_screenshot=has_screenshot
    )

    plain_content = f"""
SISTEMA DE MONITOREO DE CÁMARAS - ALERTA
==========================================
Estado: {status_title} ({log.status.value})
Cámara: {camera.name}
Dirección: {camera.ip_or_url}
Grabaciones 24h: {log.recordings_count}
Último registro: {log.latest_recording_time or 'Ninguno'}
Fecha: {checked_at_str}

Detalles:
{log.details}
==========================================
    """.strip()

    return subject, html_content, plain_content
