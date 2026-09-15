from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Playwright
from config.config import settings
from src.utils.logger import logger

class BrowserManager:
    """Gestiona el ciclo de vida del navegador Playwright."""
    def __init__(self, headless: Optional[bool] = None):
        self.headless = headless if headless is not None else settings.BROWSER_HEADLESS
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        """Inicia la instancia de Playwright y el navegador Chromium."""
        if not self._playwright:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--ignore-certificate-errors",
                    "--allow-running-insecure-content",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            logger.debug("Navegador Playwright iniciado (headless=%s)", self.headless)

    def stop(self):
        """Cierra el navegador y detiene Playwright."""
        if self._browser:
            try:
                self._browser.close()
            except Exception as e:
                logger.debug("Error cerrando navegador: %s", e)
            self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception as e:
                logger.debug("Error deteniendo Playwright: %s", e)
            self._playwright = None

    def create_camera_context(self, username: str, password: str) -> BrowserContext:
        """Crea un contexto de navegación aislado con credenciales HTTP Basic/Digest Auth."""
        if not self._browser:
            self.start()

        return self._browser.new_context(
            http_credentials={
                "username": username,
                "password": password
            },
            ignore_https_errors=True,
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
