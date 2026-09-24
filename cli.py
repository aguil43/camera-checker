import argparse
import getpass
import sys
from tabulate import tabulate

from config.config import settings
from src.database.connection import init_db
from src.database.models import Camera, CameraStatus
from src.database.repository import CameraRepository, LogRepository
from src.checker.browser_engine import BrowserManager
from src.checker.camera_checker import CameraChecker
from src.notifier.email_sender import EmailNotifier
from src.utils.logger import logger

def cmd_init_db(args):
    init_db()
    print("Base de datos inicializada correctamente.")

def cmd_add_camera(args):
    init_db()
    name = args.name or input("Nombre de la cámara (ej. Acceso Principal): ").strip()
    url = args.url or input("IP o URL de la cámara (ej. http://192.168.1.100 o dominio.mine.nu): ").strip()
    username = args.username or input("Usuario (ej. root): ").strip()
    
    if args.password:
        password = args.password
    else:
        password = getpass.getpass("Contraseña: ").strip()

    vendor = args.vendor or "vivotek"

    if args.interface is not None:
        interface_val = args.interface
    else:
        raw_int = input("Tipo de interfaz [1=Moderna/Quasar, 0=Clásica] (defecto 1): ").strip()
        interface_val = int(raw_int) if raw_int in ("0", "1") else 1

    cam = Camera(
        name=name,
        ip_or_url=url,
        username=username,
        password=password,
        vendor_type=vendor,
        interface=interface_val,
        enabled=True
    )
    cam_id = CameraRepository.add_camera(cam)
    print(f"Cámara agregada exitosamente con ID #{cam_id} (Interfaz: {'Moderna [1]' if interface_val == 1 else 'Clásica [0]'})")

def cmd_list_cameras(args):
    init_db()
    cameras = CameraRepository.get_all_cameras()
    if not cameras:
        print("No hay cámaras registradas en la base de datos.")
        return

    table = []
    for c in cameras:
        table.append([
            c.id,
            c.name,
            c.ip_or_url,
            c.username,
            "********",
            c.vendor_type,
            "Moderna (1)" if c.interface == 1 else "Clásica (0)",
            "Activa" if c.enabled else "Pausada"
        ])

    headers = ["ID", "Nombre", "IP / URL", "Usuario", "Clave", "Fabricante", "Interfaz", "Estado"]
    print("\n" + tabulate(table, headers=headers, tablefmt="grid") + "\n")

def cmd_set_interface(args):
    init_db()
    cam = CameraRepository.get_camera_by_id(args.id)
    if not cam:
        print(f"No se encontró la cámara con ID {args.id}")
        return
    if args.interface not in (0, 1):
        print("El valor de interfaz debe ser 1 (Moderna/Quasar) o 0 (Clásica).")
        return
    CameraRepository.set_camera_interface(args.id, args.interface)
    print(f"Cámara #{cam.id} '{cam.name}' actualizada a interfaz: {'Moderna (1)' if args.interface == 1 else 'Clásica (0)'}")

def cmd_delete_camera(args):
    init_db()
    cam = CameraRepository.get_camera_by_id(args.id)
    if not cam:
        print(f"No se encontró la cámara con ID {args.id}")
        return

    confirm = input(f"¿Seguro que deseas eliminar la cámara #{cam.id} '{cam.name}'? (s/n): ").strip().lower()
    if confirm in ("s", "si", "y", "yes"):
        CameraRepository.delete_camera(args.id)
        print("Cámara eliminada.")

def cmd_toggle_camera(args):
    init_db()
    cam = CameraRepository.get_camera_by_id(args.id)
    if not cam:
        print(f"No se encontró la cámara con ID {args.id}")
        return

    new_state = not cam.enabled
    CameraRepository.set_camera_enabled(args.id, new_state)
    print(f"Cámara #{cam.id} ahora está {'Activa' if new_state else 'Pausada'}.")

def cmd_test_camera(args):
    init_db()
    cam = CameraRepository.get_camera_by_id(args.id)
    if not cam:
        print(f"No se encontró la cámara con ID {args.id}")
        return

    headless = not args.visible
    print(f"Probando cámara #{cam.id} '{cam.name}' ({cam.ip_or_url}) - [Interfaz: {'Moderna (1)' if cam.interface == 1 else 'Clásica (0)'}, Navegador {'Visible' if args.visible else 'Headless'}]...")

    with BrowserManager(headless=headless) as browser_mgr:
        checker = CameraChecker(browser_mgr)
        log = checker.check_camera(cam, save_screenshot_on_ok=True)

        print("\n" + "="*50)
        print(f"RESULTADO DEL CHEQUEO:")
        print(f"Estado: {log.status.value}")
        print(f"Grabaciones en 24h: {log.recordings_count}")
        print(f"Última grabación: {log.latest_recording_time or 'N/A'}")
        print(f"Detalles: {log.details}")
        if log.screenshot_path:
            print(f"Evidencia capturada en: {log.screenshot_path}")
        print("="*50 + "\n")

        LogRepository.add_log(log)

        if log.status != CameraStatus.OK and args.send_alert:
            print("Enviando alerta de prueba por correo...")
            EmailNotifier.send_incident_alert(cam, log, force=True)

def cmd_test_url(args):
    """Permite probar una URL o IP directamente sin guardarla previamente."""
    url = args.url or input("IP o URL de la cámara: ").strip()
    username = args.username or input("Usuario (ej. root): ").strip()
    password = args.password or getpass.getpass("Contraseña: ").strip()
    headless = not args.visible
    interface_val = args.interface if args.interface is not None else 1

    cam = Camera(
        id=0,
        name="Prueba Temporal",
        ip_or_url=url,
        username=username,
        password=password,
        vendor_type="vivotek",
        interface=interface_val
    )

    print(f"\nIniciando prueba directa contra {url} (Interfaz: {'Moderna (1)' if interface_val == 1 else 'Clásica (0)'}, Navegador {'Visible' if args.visible else 'Headless'})...")
    with BrowserManager(headless=headless) as browser_mgr:
        checker = CameraChecker(browser_mgr)
        log = checker.check_camera(cam, save_screenshot_on_ok=True)

        print("\n" + "="*50)
        print(f"RESULTADO DE LA PRUEBA:")
        print(f"Estado: {log.status.value}")
        print(f"Grabaciones en 24h: {log.recordings_count}")
        print(f"Última grabación: {log.latest_recording_time or 'N/A'}")
        print(f"Detalles: {log.details}")
        if log.screenshot_path:
            print(f"Captura guardada en: {log.screenshot_path}")
        print("="*50 + "\n")

def cmd_list_logs(args):
    init_db()
    logs = LogRepository.get_recent_logs(limit=args.limit)
    if not logs:
        print("No hay registros de chequeo en la base de datos.")
        return

    table = []
    for l in logs:
        table.append([
            l.id,
            l.camera_name,
            l.status.value,
            l.recordings_count,
            l.latest_recording_time or "-",
            l.checked_at.strftime("%Y-%m-%d %H:%M:%S") if l.checked_at else "-",
            (l.details[:40] + "...") if len(l.details) > 40 else l.details
        ])

    headers = ["ID", "Cámara", "Estado", "Grabaciones 24h", "Último Registro", "Fecha", "Detalles"]
    print("\n" + tabulate(table, headers=headers, tablefmt="grid") + "\n")

def cmd_test_email(args):
    print("Probando envío de correo...")
    success = EmailNotifier.test_smtp_connection(args.to)
    if success:
        print("Correo de prueba enviado con éxito.")
    else:
        print("Fallo al enviar correo de prueba. Revisa la configuración en .env y los logs.")

def main():
    parser = argparse.ArgumentParser(description="CLI de Gestión y Verificación de Cámaras de Seguridad")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # init-db
    subparsers.add_parser("init-db", help="Inicializar la base de datos SQLite")

    # add
    p_add = subparsers.add_parser("add", help="Agregar una nueva cámara")
    p_add.add_argument("--name", help="Nombre descriptivo de la cámara")
    p_add.add_argument("--url", help="IP o URL de la cámara")
    p_add.add_argument("--username", help="Usuario de acceso")
    p_add.add_argument("--password", help="Contraseña")
    p_add.add_argument("--vendor", default="vivotek", help="Fabricante (defecto: vivotek)")
    p_add.add_argument("--interface", type=int, choices=[0, 1], default=None, help="Tipo de interfaz: 1=Moderna (Quasar), 0=Clásica")

    # set-interface
    p_set_int = subparsers.add_parser("set-interface", help="Cambiar tipo de interfaz de una cámara (1=Moderna, 0=Clásica)")
    p_set_int.add_argument("id", type=int, help="ID de la cámara")
    p_set_int.add_argument("interface", type=int, choices=[0, 1], help="Tipo de interfaz: 1=Moderna (Quasar), 0=Clásica")

    # list
    subparsers.add_parser("list", help="Listar cámaras registradas")

    # delete
    p_del = subparsers.add_parser("delete", help="Eliminar cámara por ID")
    p_del.add_argument("id", type=int, help="ID de la cámara")

    # toggle
    p_tog = subparsers.add_parser("toggle", help="Activar/desactivar cámara por ID")
    p_tog.add_argument("id", type=int, help="ID de la cámara")

    # test
    p_test = subparsers.add_parser("test", help="Probar chequeo de una cámara por ID")
    p_test.add_argument("id", type=int, help="ID de la cámara")
    p_test.add_argument("--visible", action="store_true", help="Mostrar el navegador en pantalla durante la prueba")
    p_test.add_argument("--send-alert", action="store_true", help="Enviar correo de alerta si falla")

    # test-url
    p_test_url = subparsers.add_parser("test-url", help="Probar directamente una URL de cámara")
    p_test_url.add_argument("--url", help="IP o URL de la cámara")
    p_test_url.add_argument("--username", help="Usuario")
    p_test_url.add_argument("--password", help="Contraseña")
    p_test_url.add_argument("--interface", type=int, choices=[0, 1], default=1, help="Tipo de interfaz: 1=Moderna (Quasar), 0=Clásica (defecto: 1)")
    p_test_url.add_argument("--visible", action="store_true", help="Mostrar el navegador en pantalla durante la prueba")

    # logs
    p_logs = subparsers.add_parser("logs", help="Ver historial de chequeos")
    p_logs.add_argument("--limit", type=int, default=20, help="Límite de registros a mostrar")

    # test-email
    p_email = subparsers.add_parser("test-email", help="Probar configuración SMTP de correo")
    p_email.add_argument("--to", help="Correo destinatario para la prueba")

    args = parser.parse_args()

    commands = {
        "init-db": cmd_init_db,
        "add": cmd_add_camera,
        "set-interface": cmd_set_interface,
        "list": cmd_list_cameras,
        "delete": cmd_delete_camera,
        "toggle": cmd_toggle_camera,
        "test": cmd_test_camera,
        "test-url": cmd_test_url,
        "logs": cmd_list_logs,
        "test-email": cmd_test_email
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
