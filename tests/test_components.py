from datetime import datetime, timedelta
from src.utils.date_parser import parse_camera_datetime, is_within_last_hours
from src.database.models import Camera, CheckLog, CameraStatus
from src.notifier.templates import render_email_template

def test_date_parser():
    now = datetime.now()
    now_str = now.strftime("%Y/%m/%d %H:%M:%S")
    parsed = parse_camera_datetime(now_str)
    assert parsed is not None, "Failed to parse YYYY/MM/DD HH:MM:SS"
    assert is_within_last_hours(parsed, 24) is True, "Should be within 24 hours"

    old_date = now - timedelta(days=2)
    old_str = old_date.strftime("%Y/%m/%d %H:%M:%S")
    parsed_old = parse_camera_datetime(old_str)
    assert parsed_old is not None, "Failed to parse old date"
    assert is_within_last_hours(parsed_old, 24) is False, "Should NOT be within 24 hours"

    # Format from video: 2026/09/09 15:55:40
    test_vivotek_fmt = "2026/09/09 15:55:40"
    parsed_vivotek = parse_camera_datetime(test_vivotek_fmt)
    assert parsed_vivotek is not None and parsed_vivotek.year == 2026 and parsed_vivotek.month == 9, "Vivotek format parsing failed"
    print("[OK] Date parser tests passed!")

def test_email_template_rendering():
    cam = Camera(id=1, name="Camara Acceso Principal", ip_or_url="http://192.168.1.50", username="root", password="xxx")
    log_offline = CheckLog(
        camera_id=1,
        camera_name=cam.name,
        status=CameraStatus.OFFLINE,
        details="Tiempo de espera agotado al conectar.",
        screenshot_path=None
    )
    subject, html, plain = render_email_template(cam, log_offline, has_screenshot=False)
    assert "Camara Fuera de Linea" in subject or "ALERTA" in subject
    assert "Camara Acceso Principal" in html
    assert "Tiempo de espera agotado" in plain
    print("[OK] Email template rendering tests passed!")

if __name__ == "__main__":
    test_date_parser()
    test_email_template_rendering()
    print("\nTodos los tests unitarios pasaron exitosamente.")

