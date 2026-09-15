import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

class Settings:
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / os.getenv("DB_PATH", "data/camera_checker.db")
    SCREENSHOT_DIR: Path = BASE_DIR / os.getenv("SCREENSHOT_DIR", "data/screenshots")
    LOGS_DIR: Path = BASE_DIR / "data/logs"

    # SMTP Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.tudominio.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "False").lower() in ("true", "1", "yes")

    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "alertas@tudominio.com")
    EMAIL_TO_RAW: str = os.getenv("EMAIL_TO", "")

    @property
    def EMAIL_TO(self) -> List[str]:
        if not self.EMAIL_TO_RAW:
            return []
        return [email.strip() for email in self.EMAIL_TO_RAW.split(",") if email.strip()]

    # Browser & Checker Settings (Optimizados para cámaras con interfaces lentas)
    BROWSER_HEADLESS: bool = os.getenv("BROWSER_HEADLESS", "True").lower() in ("true", "1", "yes")
    BROWSER_TIMEOUT_MS: int = int(os.getenv("BROWSER_TIMEOUT_MS", "60000"))
    PAGE_LOAD_TIMEOUT_MS: int = int(os.getenv("PAGE_LOAD_TIMEOUT_MS", "60000"))
    ELEMENT_WAIT_TIMEOUT_MS: int = int(os.getenv("ELEMENT_WAIT_TIMEOUT_MS", "30000"))
    SEARCH_WAIT_TIMEOUT_MS: int = int(os.getenv("SEARCH_WAIT_TIMEOUT_MS", "75000"))
    CHECK_INTERVAL_HOURS: int = int(os.getenv("CHECK_INTERVAL_HOURS", "24"))
    CUSTOM_INTERVAL_MINUTES: int = int(os.getenv("CUSTOM_INTERVAL_MINUTES", "5"))
    COOLDOWN_ALERT_HOURS: int = int(os.getenv("COOLDOWN_ALERT_HOURS", "4"))

    def ensure_directories(self):
        """Asegura que los directorios de almacenamiento existan."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
