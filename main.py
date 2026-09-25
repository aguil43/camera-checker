import argparse
import sys
import time
from datetime import datetime
from tabulate import tabulate

from config.config import settings
from src.database.connection import init_db
from src.database.models import CameraStatus
from src.database.repository import CameraRepository, LogRepository
from src.checker.browser_engine import BrowserManager
from src.checker.camera_checker import CameraChecker
from src.notifier.email_sender import EmailNotifier
from src.utils.logger import logger

def run_batch_check(headless: bool = True, force_alerts: bool = False):
    """Ejecuta el chequeo secuencial de todas las cámaras activas registradas."""
    init_db()
    active_cameras = CameraRepository.get_active_cameras()
    total = len(active_cameras)

    if total == 0:
        logger.info("No hay cámaras activas registradas para chequear. Usa 'python cli.py add' para registrar cámaras.")
        return []

    logger.info("=== INICIANDO CHEQUEO DE %s CÁMARAS ACTIVAS ===", total)
    results = []

    with BrowserManager(headless=headless) as browser_mgr:
        checker = CameraChecker(browser_mgr)

        for idx, camera in enumerate(active_cameras, 1):
            logger.info("Procesando cámara (%s/%s): [%s]", idx, total, camera.name)
            
            # Ejecutar chequeo
            log = checker.check_camera(camera)
            LogRepository.add_log(log)
            results.append((camera, log))

            # Si ocurrió un incidente, enviar alerta por correo
            if log.status != CameraStatus.OK:
                EmailNotifier.send_incident_alert(camera, log, force=force_alerts)

    # Imprimir resumen
    print("\n" + "="*70)
    print(f"RESUMEN DEL CICLO DE CHEQUEO ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):")
    table = []
    for cam, log in results:
        table.append([
            cam.id,
            cam.name,
            log.status.value,
            log.recordings_count,
            log.latest_recording_time or "-",
            (log.details[:35] + "...") if len(log.details) > 35 else log.details
        ])
    print(tabulate(table, headers=["ID", "Cámara", "Estado", "Grab. 24h", "Última Grabación", "Diagnóstico"], tablefmt="grid"))
    print("="*70 + "\n")

    return results

def run_daemon_loop(interval_hours: int, headless: bool = True):
    """Bucle continuo para ejecución programada cada X horas."""
    logger.info("Iniciando servicio de monitoreo en segundo plano (Frecuencia: cada %s horas)...", interval_hours)
    
    # Primera ejecución inmediata
    run_batch_check(headless=headless)

    interval_seconds = interval_hours * 3600
    while True:
        try:
            logger.info("Próximo chequeo programado en %s horas. Esperando...", interval_hours)
            time.sleep(interval_seconds)
            run_batch_check(headless=headless)
        except KeyboardInterrupt:
            logger.info("Servicio de monitoreo detenido por el usuario.")
            break
        except Exception as e:
            logger.error("Error en ciclo de monitoreo: %s", e, exc_info=True)
            time.sleep(60)

def main():
    parser = argparse.ArgumentParser(description="Ejecutor del Sistema de Verificación de Cámaras de Seguridad")
    parser.add_argument("--daemon", action="store_true", help="Ejecutar en modo servicio continuo")
    parser.add_argument("--interval", type=int, default=settings.CHECK_INTERVAL_HOURS, help=f"Intervalo de horas entre chequeos en modo daemon (defecto: {settings.CHECK_INTERVAL_HOURS})")
    parser.add_argument("--visible", action="store_true", help="Abrir el navegador visible en lugar de headless")
    parser.add_argument("--force-alerts", action="store_true", help="Ignorar cooldown de alertas y enviar siempre correo ante incidentes")
    parser.add_argument("--serve", action="store_true", help="Iniciar el servidor de API y Dashboard Web de monitoreo")
    parser.add_argument("--host", default="0.0.0.0", help="Dirección IP de escucha para el servidor web (defecto: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto TCP para el servidor web (defecto: 8000)")

    args = parser.parse_args()

    if args.serve:
        from src.api.server import start_server
        start_server(host=args.host, port=args.port)
        return

    headless = not args.visible

    if args.daemon:
        run_daemon_loop(interval_hours=args.interval, headless=headless)
    else:
        run_batch_check(headless=headless, force_alerts=args.force_alerts)

if __name__ == "__main__":
    main()
