import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from config.config import settings
from src.database.models import Camera, CheckLog, CameraStatus, RecordingItem
from src.checker.browser_engine import BrowserManager
from src.checker.selectors import VIVOTEK_SELECTORS
from src.utils.logger import logger
from src.utils.date_parser import parse_camera_datetime, is_within_last_hours

class CameraChecker:
    def __init__(self, browser_manager: Optional[BrowserManager] = None):
        self.browser_manager = browser_manager or BrowserManager()

    def check_camera(self, camera: Camera, save_screenshot_on_ok: bool = False) -> CheckLog:
        """Ejecuta el chequeo optimizado de una cámara individual usando intervalo de 5 minutos."""
        logger.info("Iniciando chequeo de cámara: [%s] (%s)", camera.name, camera.ip_or_url)
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None
        screenshot_path: Optional[str] = None
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Asegurar formato de URL
        target_url = camera.ip_or_url.strip()
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = f"http://{target_url}"

        try:
            context = self.browser_manager.create_camera_context(camera.username, camera.password)
            page = context.new_page()
            page.set_default_timeout(settings.ELEMENT_WAIT_TIMEOUT_MS)

            # 1. Navegación inicial
            logger.info("[%s] Conectando a %s ...", camera.name, target_url)
            try:
                response = page.goto(target_url, timeout=settings.PAGE_LOAD_TIMEOUT_MS, wait_until="domcontentloaded")
            except PlaywrightTimeoutError:
                return self._create_log_and_screenshot(
                    camera, CameraStatus.OFFLINE, 0, None,
                    f"Tiempo de espera agotado al conectar a {target_url} (Timeout {settings.PAGE_LOAD_TIMEOUT_MS/1000}s)",
                    page, timestamp_str
                )
            except PlaywrightError as e:
                return self._create_log_and_screenshot(
                    camera, CameraStatus.OFFLINE, 0, None,
                    f"Fallo de conexión / Cámara fuera de línea: {str(e)}",
                    page, timestamp_str
                )

            # 2. Verificar código HTTP de respuesta
            if response and response.status in (401, 403):
                return self._create_log_and_screenshot(
                    camera, CameraStatus.AUTH_FAILED, 0, None,
                    f"Error de autenticación HTTP {response.status}: Usuario o contraseña incorrectos",
                    page, timestamp_str
                )

            # 3. Superar posibles advertencias de seguridad de Chrome ("Continuar al sitio")
            self._handle_insecure_warning(page)

            # 4. Esperar inicialización de la interfaz web
            logger.info("[%s] Esperando renderizado de la interfaz web...", camera.name)
            self._wait_for_ui_to_render(page, camera.name)

            # 5. Navegar a la sección de archivos (File)
            logger.info("[%s] Navegando al menú de archivos (File)...", camera.name)
            self._navigate_to_file_section(page, target_url)

            # 6. Configurar filtro rápido de últimos 5 minutos (Custom time interval) y buscar
            interval_mins = settings.CUSTOM_INTERVAL_MINUTES
            logger.info("[%s] Configurando filtro rápido de los últimos %s minutos...", camera.name, interval_mins)
            self._execute_search_custom_interval(page, interval_minutes=interval_mins)

            # 7. Analizar la tabla de resultados
            logger.info("[%s] Analizando lista de grabaciones recibidas...", camera.name)
            recordings, raw_text = self._parse_recordings_table(page)

            # 8. Evaluar grabaciones detectadas
            latest_time_str = recordings[0].start_time_str if recordings else None

            if recordings:
                count = len(recordings)
                details = f"Chequeo exitoso. Se encontraron {count} grabaciones en los últimos {interval_mins} min. Más reciente: {latest_time_str}"
                logger.info("[%s] %s", camera.name, details)
                if save_screenshot_on_ok:
                    screenshot_path = self._take_screenshot(page, camera.id or 0, timestamp_str, "OK")
                return CheckLog(
                    camera_id=camera.id or 0,
                    camera_name=camera.name,
                    status=CameraStatus.OK,
                    recordings_count=count,
                    latest_recording_time=latest_time_str,
                    details=details,
                    screenshot_path=screenshot_path
                )
            else:
                # 0 resultados
                details = f"No se encontraron grabaciones (0 resultados) en los últimos {interval_mins} minutos."
                logger.warning("[%s] %s", camera.name, details)
                screenshot_path = self._take_screenshot(page, camera.id or 0, timestamp_str, "NO_RECORDINGS")
                return CheckLog(
                    camera_id=camera.id or 0,
                    camera_name=camera.name,
                    status=CameraStatus.NO_RECORDINGS,
                    recordings_count=0,
                    latest_recording_time=None,
                    details=details,
                    screenshot_path=screenshot_path
                )

        except PlaywrightTimeoutError as te:
            logger.error("[%s] Timeout durante la interacción: %s", camera.name, te)
            return self._create_log_and_screenshot(
                camera, CameraStatus.ERROR, 0, None,
                f"Tiempo de espera agotado interactuando con la interfaz: {str(te)}",
                page, timestamp_str
            )
        except Exception as ex:
            logger.error("[%s] Error inesperado durante el chequeo: %s", camera.name, ex, exc_info=True)
            return self._create_log_and_screenshot(
                camera, CameraStatus.ERROR, 0, None,
                f"Error inesperado: {str(ex)}",
                page, timestamp_str
            )
        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass

    def _handle_insecure_warning(self, page: Page):
        """Intenta hacer clic en 'Continuar al sitio' o bypass de advertencias de Chrome si aparecen."""
        try:
            btn = page.locator("xpath=//button[contains(text(), 'Continuar al sitio') or contains(text(), 'Proceed to') or @id='proceed-button']").first
            if btn.is_visible(timeout=2000):
                logger.info("Detectada advertencia de conexión no segura. Continuando...")
                btn.click()
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                time.sleep(2)
        except Exception:
            pass

    def _wait_for_ui_to_render(self, page: Page, camera_name: str):
        """Espera a que los scripts de la interfaz de la cámara terminen de renderizar la página."""
        try:
            page.wait_for_selector(
                "xpath=//span[contains(text(), 'System')] | //div[contains(text(), 'System')] | //li[contains(., 'System')] | //span[contains(text(), 'VIVOTEK')] | //div[contains(text(), 'File')]",
                state="visible",
                timeout=25000
            )
            logger.info("[%s] Elementos de la interfaz web detectados.", camera_name)
        except Exception:
            logger.warning("[%s] Interfaz tardó en renderizar, continuando...", camera_name)
            time.sleep(4)

    def _navigate_to_file_section(self, page: Page, base_url: str):
        """Navega a la sección File/#/file_general con esperas y manejo de fallbacks."""
        current_url = page.url

        if "file_general" not in current_url:
            navigated = False
            # 1. Intentar navegación directa hash que es la más rápida y confiable en Quasar
            direct_urls = [
                f"{base_url.rstrip('/')}/home.html#/file_general",
                f"{base_url.rstrip('/')}/fcms.html#/file_general",
                f"{base_url.rstrip('/')}/#/file_general"
            ]
            for u in direct_urls:
                try:
                    logger.info("Navegando directamente a URL de archivos: %s", u)
                    page.goto(u, wait_until="domcontentloaded", timeout=settings.PAGE_LOAD_TIMEOUT_MS)
                    time.sleep(2)
                    if "file_general" in page.url:
                        navigated = True
                        break
                except Exception:
                    pass

            # 2. Fallback por clics en menú si no funcionó la URL directa
            if not navigated or "file_general" not in page.url:
                try:
                    system_menu = page.locator(VIVOTEK_SELECTORS["menu_system"]).first
                    if system_menu.is_visible(timeout=5000):
                        system_menu.click()
                        time.sleep(1.5)
                        file_menu = page.locator(VIVOTEK_SELECTORS["menu_file"]).first
                        if file_menu.is_visible(timeout=10000):
                            file_menu.click()
                            time.sleep(2)
                except Exception as e:
                    logger.warning("Aviso en navegación por menú: %s", e)

        # Esperar a que desaparezca 'Connecting to the web'
        try:
            connecting_mask = page.locator(VIVOTEK_SELECTORS["connecting_mask"]).first
            if connecting_mask.is_visible(timeout=3000):
                connecting_mask.wait_for(state="hidden", timeout=settings.PAGE_LOAD_TIMEOUT_MS)
        except Exception:
            pass

        time.sleep(2)

    def _execute_search_custom_interval(self, page: Page, interval_minutes: int = 5):
        """Selecciona 'Custom time interval', ajusta la hora inicio restando N minutos y busca."""
        # 1. Localizar y abrir el dropdown de Time frame
        logger.info("Localizando selector de rango de tiempo (Time frame)...")
        dropdown = None
        
        # Intentar varias formas de encontrar el dropdown de Time frame
        locators_to_try = [
            page.locator(VIVOTEK_SELECTORS["time_frame_dropdown"]).first,
            page.locator("xpath=//*[contains(text(), 'Time frame')]/ancestor::div[contains(@class, 'q-field')]").first,
            page.locator("xpath=//*[contains(text(), 'Last 24 hours')]/ancestor::div[contains(@class, 'q-field') or contains(@class, 'q-select')]").first,
            page.locator("text='Last 24 hours'").first,
            page.locator("text='Time frame'").first
        ]

        for loc in locators_to_try:
            try:
                if loc.is_visible(timeout=2000):
                    dropdown = loc
                    break
            except Exception:
                continue

        if dropdown:
            logger.info("Haciendo clic en selector Time frame...")
            dropdown.click()
        else:
            # Si no se detectó por contenedor, forzar clic por texto
            page.click("text=Last 24 hours", timeout=5000)

        time.sleep(1)

        # 2. Hacer clic en 'Custom time interval'
        logger.info("Seleccionando 'Custom time interval'...")
        option_custom = page.locator(VIVOTEK_SELECTORS["option_custom_interval"]).first
        try:
            option_custom.wait_for(state="visible", timeout=10000)
            option_custom.click()
        except Exception:
            page.click("text=Custom time interval", timeout=5000)

        logger.info("Esperando ventana modal 'Date & Time'...")
        time.sleep(1.5)

        # 3. Interactuar con el diálogo modal 'Date & Time'
        modal = page.locator(VIVOTEK_SELECTORS["modal_date_time"]).first
        modal.wait_for(state="visible", timeout=10000)
        
        # Obtener los inputs del diálogo [Start Date, Start Time, End Date, End Time]
        inputs = modal.locator("input")
        input_count = inputs.count()
        logger.debug("Campos de entrada detectados en modal: %s", input_count)

        if input_count >= 4:
            # Leer el End Time actual de la cámara (ej. 17:15)
            end_time_str = inputs.nth(3).input_value().strip()
            logger.info("Hora final actual en cámara (End Time): '%s'", end_time_str)

            # Calcular la hora de inicio restando N minutos (ej. 17:10)
            start_time_val = None
            if end_time_str and ":" in end_time_str:
                try:
                    parts = [int(p) for p in end_time_str.split(":")[:2]]
                    end_dt = datetime.now().replace(hour=parts[0], minute=parts[1], second=0)
                    start_dt = end_dt - timedelta(minutes=interval_minutes)
                    start_time_val = start_dt.strftime("%H:%M")
                except Exception as ex:
                    logger.debug("Error calculando desde End Time: %s", ex)

            if not start_time_val:
                # Fallback con hora local
                start_time_val = (datetime.now() - timedelta(minutes=interval_minutes)).strftime("%H:%M")

            logger.info("Estableciendo Start Time a '%s' (hace %s minutos)...", start_time_val, interval_minutes)
            
            # Escribir el nuevo Start Time en el segundo input (inputs.nth(1))
            start_time_input = inputs.nth(1)
            start_time_input.click()
            start_time_input.press("Control+A")
            start_time_input.fill(start_time_val)
            start_time_input.press("Tab")
            time.sleep(0.5)

        # 4. Guardar la configuración en el modal
        save_btn = modal.locator(VIVOTEK_SELECTORS["modal_btn_save"]).first
        save_btn.wait_for(state="visible", timeout=5000)
        save_btn.click()
        logger.info("Intervalo guardado. Esperando cierre del modal...")
        time.sleep(1.5)

        # 5. Clic en el botón azul 'Search'
        search_btn = page.locator(VIVOTEK_SELECTORS["btn_search"]).first
        try:
            search_btn.wait_for(state="visible", timeout=10000)
            search_btn.click()
        except Exception:
            page.click("text=Search", timeout=5000)

        logger.info("Botón 'Search' presionado. Consultando grabaciones de los últimos %s minutos...", interval_minutes)

        # 6. Esperar a que el spinner 'Searching...' termine
        time.sleep(1.5)
        try:
            spinner = page.locator(VIVOTEK_SELECTORS["searching_spinner"]).first
            if spinner.is_visible(timeout=3000):
                logger.info("Búsqueda en proceso ('Searching...'). Esperando respuesta de la cámara...")
                spinner.wait_for(state="hidden", timeout=settings.SEARCH_WAIT_TIMEOUT_MS)
                logger.info("La cámara ha completado la búsqueda.")
        except Exception:
            logger.debug("Spinner finalizó rápidamente.")

        # Pausa breve para renderizar la tabla
        time.sleep(2)

    def _parse_recordings_table(self, page: Page) -> Tuple[List[RecordingItem], str]:
        """Espera a que los registros se rendericen y extrae las grabaciones."""
        recordings: List[RecordingItem] = []
        raw_text = ""

        # Bucle de espera de hasta 20s para leer los resultados
        max_wait_seconds = 20
        start_wait = time.time()

        while time.time() - start_wait < max_wait_seconds:
            # 1. Verificar si hay filas de datos
            rows = page.locator(VIVOTEK_SELECTORS["table_rows"])
            row_count = rows.count()

            # 2. Verificar si aparece explícitamente "No search results" o "0 results"
            no_results = page.locator(VIVOTEK_SELECTORS["no_results_text"]).first
            is_no_results = False
            try:
                if no_results.is_visible(timeout=500):
                    is_no_results = True
            except Exception:
                pass

            if row_count > 0:
                logger.info("¡Resultados encontrados! Se detectaron %s filas en la tabla.", row_count)
                for i in range(row_count):
                    try:
                        row = rows.nth(i)
                        cells = row.locator("xpath=.//td | .//div[contains(@class, 'cell')]")
                        cell_count = cells.count()

                        row_texts = [cells.nth(j).inner_text().strip() for j in range(cell_count)]
                        
                        start_time_str = ""
                        end_time_str = ""
                        file_name = f"File_{i+1}"
                        storage = None
                        trigger_type = None
                        media_type = None

                        for text in row_texts:
                            dt = parse_camera_datetime(text)
                            if dt:
                                if not start_time_str:
                                    start_time_str = text
                                elif not end_time_str:
                                    end_time_str = text

                        if start_time_str:
                            start_dt = parse_camera_datetime(start_time_str)
                            if len(row_texts) >= 2:
                                file_name = row_texts[1]
                            if len(row_texts) >= 3:
                                storage = row_texts[2]
                            if len(row_texts) >= 4:
                                trigger_type = row_texts[3]

                            recordings.append(RecordingItem(
                                file_name=file_name,
                                storage=storage,
                                trigger_type=trigger_type,
                                start_time_str=start_time_str,
                                end_time_str=end_time_str,
                                media_type=media_type,
                                start_time=start_dt
                            ))
                    except Exception as e:
                        logger.debug("Error procesando fila %s: %s", i, e)

                if recordings:
                    return recordings, ""

            elif is_no_results:
                logger.info("La cámara reportó: 0 resultados / No search results.")
                return [], "No search results"

            time.sleep(1.5)

        return recordings, raw_text

    def _take_screenshot(self, page: Optional[Page], camera_id: int, timestamp_str: str, suffix: str) -> Optional[str]:
        """Captura de pantalla como evidencia."""
        if not page:
            return None
        try:
            settings.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"cam_{camera_id}_{timestamp_str}_{suffix}.png"
            filepath = settings.SCREENSHOT_DIR / filename
            page.screenshot(path=str(filepath), full_page=False)
            logger.info("Captura de evidencia guardada en: %s", filepath)
            return str(filepath)
        except Exception as e:
            logger.debug("No se pudo tomar la captura de pantalla: %s", e)
            return None

    def _create_log_and_screenshot(
        self, camera: Camera, status: CameraStatus, count: int,
        latest_time: Optional[str], details: str, page: Optional[Page], timestamp_str: str
    ) -> CheckLog:
        screenshot_path = self._take_screenshot(page, camera.id or 0, timestamp_str, status.value)
        return CheckLog(
            camera_id=camera.id or 0,
            camera_name=camera.name,
            status=status,
            recordings_count=count,
            latest_recording_time=latest_time,
            details=details,
            screenshot_path=screenshot_path
        )
