from datetime import datetime, timedelta
from typing import List, Optional
from src.database.connection import get_db_connection
from src.database.models import Camera, CheckLog, AlertHistory, CameraStatus
from src.utils.logger import logger

class CameraRepository:
    @staticmethod
    def add_camera(camera: Camera) -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cameras (name, ip_or_url, username, password, vendor_type, interface, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (camera.name, camera.ip_or_url, camera.username, camera.password, camera.vendor_type, camera.interface, 1 if camera.enabled else 0))
        camera_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info("Cámara registrada con ID %s: %s (%s, interface=%s)", camera_id, camera.name, camera.ip_or_url, camera.interface)
        return camera_id

    @staticmethod
    def get_all_cameras() -> List[Camera]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cameras ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        return [
            Camera(
                id=row["id"],
                name=row["name"],
                ip_or_url=row["ip_or_url"],
                username=row["username"],
                password=row["password"],
                vendor_type=row["vendor_type"],
                interface=row["interface"] if "interface" in row.keys() and row["interface"] is not None else 1,
                enabled=bool(row["enabled"]),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            )
            for row in rows
        ]

    @staticmethod
    def get_active_cameras() -> List[Camera]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cameras WHERE enabled = 1 ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        return [
            Camera(
                id=row["id"],
                name=row["name"],
                ip_or_url=row["ip_or_url"],
                username=row["username"],
                password=row["password"],
                vendor_type=row["vendor_type"],
                interface=row["interface"] if "interface" in row.keys() and row["interface"] is not None else 1,
                enabled=bool(row["enabled"]),
            )
            for row in rows
        ]

    @staticmethod
    def get_camera_by_id(camera_id: int) -> Optional[Camera]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return Camera(
            id=row["id"],
            name=row["name"],
            ip_or_url=row["ip_or_url"],
            username=row["username"],
            password=row["password"],
            vendor_type=row["vendor_type"],
            interface=row["interface"] if "interface" in row.keys() and row["interface"] is not None else 1,
            enabled=bool(row["enabled"]),
        )

    @staticmethod
    def delete_camera(camera_id: int) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
        affected = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return affected

    @staticmethod
    def set_camera_enabled(camera_id: int, enabled: bool) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE cameras SET enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (1 if enabled else 0, camera_id))
        affected = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return affected

    @staticmethod
    def set_camera_interface(camera_id: int, interface: int) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE cameras SET interface = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (interface, camera_id))
        affected = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return affected

class LogRepository:
    @staticmethod
    def add_log(log: CheckLog) -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO check_logs (camera_id, status, recordings_count, latest_recording_time, details, screenshot_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (log.camera_id, log.status.value, log.recordings_count, log.latest_recording_time, log.details, log.screenshot_path))
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id

    @staticmethod
    def get_recent_logs(limit: int = 50) -> List[CheckLog]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT l.*, c.name as camera_name 
            FROM check_logs l
            JOIN cameras c ON l.camera_id = c.id
            ORDER BY l.checked_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [
            CheckLog(
                id=row["id"],
                camera_id=row["camera_id"],
                camera_name=row["camera_name"],
                status=CameraStatus(row["status"]),
                recordings_count=row["recordings_count"],
                latest_recording_time=row["latest_recording_time"],
                details=row["details"],
                screenshot_path=row["screenshot_path"],
                checked_at=datetime.fromisoformat(row["checked_at"]) if row["checked_at"] else None
            )
            for row in rows
        ]

    @staticmethod
    def get_last_log_for_camera(camera_id: int) -> Optional[CheckLog]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM check_logs 
            WHERE camera_id = ?
            ORDER BY checked_at DESC
            LIMIT 1
        """, (camera_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return CheckLog(
            id=row["id"],
            camera_id=row["camera_id"],
            status=CameraStatus(row["status"]),
            recordings_count=row["recordings_count"],
            latest_recording_time=row["latest_recording_time"],
            details=row["details"],
            screenshot_path=row["screenshot_path"],
            checked_at=datetime.fromisoformat(row["checked_at"]) if row["checked_at"] else None
        )

class AlertRepository:
    @staticmethod
    def add_alert(alert: AlertHistory) -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alert_history (camera_id, alert_type, recipient, details)
            VALUES (?, ?, ?, ?)
        """, (alert.camera_id, alert.alert_type.value, alert.recipient, alert.details))
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return alert_id

    @staticmethod
    def is_in_cooldown(camera_id: int, alert_type: CameraStatus, cooldown_hours: int = 4) -> bool:
        """Verifica si ya se envió una alerta del mismo tipo para esta cámara en las últimas N horas."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sent_at FROM alert_history
            WHERE camera_id = ? AND alert_type = ?
            ORDER BY sent_at DESC
            LIMIT 1
        """, (camera_id, alert_type.value))
        row = cursor.fetchone()
        conn.close()
        if not row or not row["sent_at"]:
            return False

        try:
            sent_at = datetime.fromisoformat(row["sent_at"])
        except ValueError:
            return False

        return datetime.now() - sent_at < timedelta(hours=cooldown_hours)
