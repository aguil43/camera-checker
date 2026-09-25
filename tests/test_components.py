import unittest
from datetime import datetime, timedelta
from src.utils.date_parser import parse_camera_datetime, is_within_last_hours
from src.database.models import Camera, CheckLog, CameraStatus
from src.notifier.templates import render_email_template

class TestCameraCheckerComponents(unittest.TestCase):
    def test_date_parser(self):
        now = datetime.now()
        now_str = now.strftime("%Y/%m/%d %H:%M:%S")
        parsed = parse_camera_datetime(now_str)
        self.assertIsNotNone(parsed, "Failed to parse YYYY/MM/DD HH:MM:SS")
        self.assertTrue(is_within_last_hours(parsed, 24), "Should be within 24 hours")

        old_date = now - timedelta(days=2)
        old_str = old_date.strftime("%Y/%m/%d %H:%M:%S")
        parsed_old = parse_camera_datetime(old_str)
        self.assertIsNotNone(parsed_old, "Failed to parse old date")
        self.assertFalse(is_within_last_hours(parsed_old, 24), "Should NOT be within 24 hours")

        # Format from video: 2026/09/09 15:55:40
        test_vivotek_fmt = "2026/09/09 15:55:40"
        parsed_vivotek = parse_camera_datetime(test_vivotek_fmt)
        self.assertIsNotNone(parsed_vivotek)
        self.assertEqual(parsed_vivotek.year, 2026)
        self.assertEqual(parsed_vivotek.month, 9)

        # Format from classic interface: 08/26/2026 4:07 PM
        test_classic_fmt = "08/26/2026 4:07 PM"
        parsed_classic = parse_camera_datetime(test_classic_fmt)
        self.assertIsNotNone(parsed_classic)
        self.assertEqual(parsed_classic.year, 2026)
        self.assertEqual(parsed_classic.month, 8)
        self.assertEqual(parsed_classic.day, 26)
        self.assertEqual(parsed_classic.hour, 16)

    def test_email_template_rendering(self):
        cam = Camera(id=1, name="Camara Acceso Principal", ip_or_url="http://192.168.1.50", username="root", password="xxx")
        log_offline = CheckLog(
            camera_id=1,
            camera_name=cam.name,
            status=CameraStatus.OFFLINE,
            details="Tiempo de espera agotado al conectar.",
            screenshot_path=None
        )
        subject, html, plain = render_email_template(cam, log_offline, has_screenshot=False)
        self.assertTrue("Camara Fuera de Linea" in subject or "ALERTA" in subject)
        self.assertIn("Camara Acceso Principal", html)
        self.assertIn("Tiempo de espera agotado", plain)

    def test_api_endpoints(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        
        # Test summary endpoint
        res_sum = client.get("/api/summary")
        self.assertEqual(res_sum.status_code, 200)
        data_sum = res_sum.json()
        self.assertIn("total_cameras", data_sum)
        self.assertIn("health_percentage", data_sum)

        # Test cameras endpoint
        res_cams = client.get("/api/cameras")
        self.assertEqual(res_cams.status_code, 200)
        self.assertIsInstance(res_cams.json(), list)

        # Test static frontend index
        res_index = client.get("/")
        self.assertEqual(res_index.status_code, 200)
        self.assertIn("SentinelCam", res_index.text)

if __name__ == "__main__":
    unittest.main()

