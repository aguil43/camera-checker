import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
from typing import List, Optional

from config.config import settings
from src.database.models import Camera, CheckLog, AlertHistory, CameraStatus
from src.database.repository import AlertRepository
from src.notifier.templates import render_email_template
from src.utils.logger import logger

class EmailNotifier:
    @staticmethod
    def send_incident_alert(camera: Camera, log: CheckLog, force: bool = False) -> bool:
        """Envía un correo de alerta si ocurrió un incidente y no está en período de enfriamiento (cooldown)."""
        if log.status == CameraStatus.OK:
            return False

        recipients = settings.EMAIL_TO
        if not recipients:
            logger.warning("No se configuraron destinatarios de correo (EMAIL_TO) en .env. Alerta no enviada.")
            return False

        if not settings.SMTP_HOST or not settings.SMTP_USER:
            logger.warning("Configuración SMTP incompleta en .env. Alerta no enviada.")
            return False

        # Verificar cooldown si no se fuerza
        if not force and camera.id:
            if AlertRepository.is_in_cooldown(camera.id, log.status, settings.COOLDOWN_ALERT_HOURS):
                logger.info("[%s] Alerta %s omitida por período de enfriamiento (cooldown de %s h).",
                            camera.name, log.status.value, settings.COOLDOWN_ALERT_HOURS)
                return False

        # Verificar captura de pantalla
        has_screenshot = False
        screenshot_path = None
        if log.screenshot_path and Path(log.screenshot_path).exists():
            has_screenshot = True
            screenshot_path = Path(log.screenshot_path)

        subject, html_body, plain_body = render_email_template(camera, log, has_screenshot=has_screenshot)

        success = EmailNotifier._dispatch_email(recipients, subject, html_body, plain_body, screenshot_path)

        if success and camera.id:
            for recipient in recipients:
                AlertRepository.add_alert(AlertHistory(
                    camera_id=camera.id,
                    alert_type=log.status,
                    recipient=recipient,
                    details=log.details
                ))
            logger.info("Alerta de correo enviada exitosamente a %s para la cámara [%s]", recipients, camera.name)

        return success

    @staticmethod
    def _dispatch_email(
        recipients: List[str],
        subject: str,
        html_body: str,
        plain_body: str,
        screenshot_path: Optional[Path] = None
    ) -> bool:
        """Despacha el correo a través del servidor SMTP configurado."""
        try:
            msg = MIMEMultipart("related")
            msg["Subject"] = subject
            msg["From"] = settings.EMAIL_FROM
            msg["To"] = ", ".join(recipients)

            msg_alternative = MIMEMultipart("alternative")
            msg.attach(msg_alternative)

            # Versión texto plano
            msg_alternative.attach(MIMEText(plain_body, "plain", "utf-8"))
            # Versión HTML
            msg_alternative.attach(MIMEText(html_body, "html", "utf-8"))

            # Adjuntar imagen embebida si existe
            if screenshot_path and screenshot_path.exists():
                try:
                    with open(screenshot_path, "rb") as img_file:
                        img_data = img_file.read()
                        mime_img = MIMEImage(img_data)
                        mime_img.add_header("Content-ID", "<screenshot_evidence>")
                        mime_img.add_header("Content-Disposition", "inline", filename=screenshot_path.name)
                        msg.attach(mime_img)
                except Exception as img_err:
                    logger.warning("No se pudo adjuntar la captura al correo: %s", img_err)

            # Conexión SMTP
            if settings.SMTP_USE_SSL:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)

            server.ehlo()
            if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                server.starttls()
                server.ehlo()

            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.sendmail(settings.EMAIL_FROM, recipients, msg.as_string())
            server.quit()
            return True

        except Exception as e:
            logger.error("Error enviando correo SMTP a %s: %s", recipients, e, exc_info=True)
            return False

    @staticmethod
    def test_smtp_connection(test_recipient: Optional[str] = None) -> bool:
        """Prueba de conexión y envío de correo de test."""
        recipient = test_recipient or (settings.EMAIL_TO[0] if settings.EMAIL_TO else None)
        if not recipient:
            logger.error("No hay destinatario configurado para la prueba SMTP.")
            return False

        subject = "🧪 [TEST] Verificación de Notificaciones de Cámaras de Seguridad"
        html_body = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #10b981; border-radius: 8px;">
            <h2 style="color: #10b981; margin-top: 0;">✔ Prueba de Conexión SMTP Exitosa</h2>
            <p>Este correo confirma que la configuración de envío de alertas por correo electrónico con dominio personalizado está funcionando correctamente.</p>
            <p><strong>Servidor SMTP:</strong> {settings.SMTP_HOST}:{settings.SMTP_PORT}</p>
            <p><strong>Remitente:</strong> {settings.EMAIL_FROM}</p>
        </div>
        """
        plain_body = f"Prueba de Conexión SMTP Exitosa. Servidor: {settings.SMTP_HOST}:{settings.SMTP_PORT}"

        logger.info("Enviando correo de prueba a %s...", recipient)
        return EmailNotifier._dispatch_email([recipient], subject, html_body, plain_body)
