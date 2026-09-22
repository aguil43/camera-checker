import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from config.config import settings
from src.database.models import Camera, CheckLog, CameraStatus, RecordingItem
from src.checker.browser_engine import BrowserManager
from src.checker.selectors import VIVOTEK_QUASAR_SELECTORS, VIVOTEK_CLASSIC_SELECTORS
from src.utils.logger import logger
from src.utils.date_parser import parse_camera_datetime, is_within_last_hours

class CameraChecker:
    def __init__(self, browser_manager: Optional[BrowserManager] = None):
        self.browser_manager = browser_manager or BrowserManager()

    def check_camera(self, camera: Camera, save_screenshot_on_ok: bool = False) -> CheckLog:
        """Ejecuta el chequeo de la cámara detectando automáticamente su tipo de interfaz."""
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

            # 1. Conexión inicial
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

            # 4. Detectar qué tipo de interfaz tiene la cámara (Moderna Quasar vs Clásica /setup/)
            interface_type = self._detect_interface_type(page, target_url)
            logger.info("[%s] Interfaz detectada: %s", camera.name, interface_type)

            interval_mins = settings.CUSTOM_INTERVAL_MINUTES

            if interface_type == "CLASSIC":
                recordings = self._handle_classic_interface(page, target_url, interval_mins)
            else:
                recordings = self._handle_quasar_interface(page, target_url, interval_mins)

            # 5. Evaluar grabaciones detectadas
            latest_time_str = recordings[0].start_time_str if recordings else None

            if recordings:
                count = len(recordings)
                details = f"Chequeo exitoso ({interface_type}). Grabaciones activas detectadas en los últimos {interval_mins} min ({count} archivos). Más reciente: {latest_time_str}"
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
                details = f"No se encontraron grabaciones (0 resultados) en los últimos {interval_mins} minutos ({interface_type})."
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
        """Bypass de advertencias SSL/HTTP de Chrome."""
        try:
            btn = page.locator("xpath=//button[contains(text(), 'Continuar al sitio') or contains(text(), 'Proceed to') or @id='proceed-button']").first
            if btn.is_visible(timeout=2000):
                logger.info("Detectada advertencia de conexión no segura. Continuando...")
                btn.click()
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                time.sleep(2)
        except Exception:
            pass

    def _detect_interface_type(self, page: Page, base_url: str) -> str:
        """Determina con precisión si la cámara usa la interfaz Clásica o Quasar (esperando la carga del SPA)."""
        logger.info("Identificando tipo de interfaz web de la cámara (esperando carga)...")
        
        # Esperar hasta 6 segundos mientras la cámara resuelve su redirección SPA
        max_wait = 6
        start_t = time.time()
        
        while time.time() - start_t < max_wait:
            current_url = page.url.lower()
            
            # 1. Si la URL ya resolvió al hash SPA (#/) o fcms
            if "#/" in current_url or "fcms" in current_url:
                logger.info("Interfaz detectada como QUASAR (por hash SPA: %s)", page.url)
                return "QUASAR"
            
            # 2. Si el contenedor raíz de Quasar ya apareció en el DOM
            try:
                if page.locator("#q-app, .q-layout, .q-page-container").first.is_visible(timeout=500):
                    logger.info("Interfaz detectada como QUASAR (por contenedor #q-app en DOM)")
                    return "QUASAR"
            except Exception:
                pass

            # 3. Si la URL es explícitamente /setup/ o storage_searching
            if "/setup/" in current_url or "storage_searching" in current_url:
                logger.info("Interfaz detectada como CLASSIC (por ruta /setup/: %s)", page.url)
                return "CLASSIC"

            time.sleep(1.0)

        # Si tras esperar no apareció ningún indicador de Quasar (#/ o #q-app):
        current_url = page.url.lower()
        if "#/" in current_url:
            logger.info("Interfaz detectada como QUASAR (%s)", page.url)
            return "QUASAR"

        logger.info("Interfaz detectada como CLASSIC (%s)", page.url)
        return "CLASSIC"

    # =========================================================================
    # MANEJO DE INTERFAZ 1: QUASAR (MODERNA)
    # =========================================================================
    def _handle_quasar_interface(self, page: Page, base_url: str, interval_minutes: int) -> List[RecordingItem]:
        """Flujo para la interfaz moderna Quasar."""
        logger.info("[Quasar] Iniciando verificación en interfaz moderna...")
        target_file_url = f"{base_url.rstrip('/')}/home.html#/file_general"

        if "file_general" not in page.url:
            logger.info("[Quasar] Navegando a URL de archivos: %s", target_file_url)
            try:
                page.goto(target_file_url, wait_until="domcontentloaded", timeout=settings.PAGE_LOAD_TIMEOUT_MS)
                time.sleep(3)
            except Exception as e:
                logger.debug("[Quasar] Aviso en goto: %s", e)

        # Esperar máscara inicial si aparece
        try:
            mask = page.locator(".q-loading, .connecting-mask").first
            if mask.is_visible(timeout=2000):
                mask.wait_for(state="hidden", timeout=settings.PAGE_LOAD_TIMEOUT_MS)
        except Exception:
            pass

        time.sleep(2)

        # Asegurar hash #/file_general
        if "file_general" not in page.url:
            try:
                page.evaluate("window.location.hash = '#/file_general'")
                time.sleep(3)
            except Exception:
                pass

        # 1. Paso 1: Abrir el selector de marco de tiempo (Time frame)
        logger.info("[Quasar] Paso 1: Localizando y abriendo selector Time frame...")
        time_frame_loc = page.locator(".q-field").filter(has_text="Time frame").first
        if not time_frame_loc.is_visible(timeout=2000):
            time_frame_loc = page.locator(".q-field").filter(has_text="Last").first
        if not time_frame_loc.is_visible(timeout=2000):
            time_frame_loc = page.locator("text=Last 24 hours").first

        time_frame_loc.wait_for(state="visible", timeout=settings.ELEMENT_WAIT_TIMEOUT_MS)
        time_frame_loc.click(force=True)
        logger.info("[Quasar] Selector Time frame clickeado.")
        time.sleep(1)

        # 2. Paso 2: Seleccionar 'Custom time interval' del menú desplegado
        logger.info("[Quasar] Paso 2: Seleccionando 'Custom time interval'...")
        custom_opt = page.locator(".q-menu .q-item, .q-item").filter(has_text="Custom time interval").first
        if not custom_opt.is_visible(timeout=3000):
            custom_opt = page.locator("text=Custom time interval").first

        custom_opt.wait_for(state="visible", timeout=settings.ELEMENT_WAIT_TIMEOUT_MS)
        custom_opt.click(force=True)
        logger.info("[Quasar] 'Custom time interval' clickeado.")
        time.sleep(1.5)

        # 3. Paso 3: Configurar hora en el modal 'Date & Time'
        logger.info("[Quasar] Paso 3: Esperando modal Date & Time para configurar %s minutos...", interval_minutes)
        modal = page.locator(".q-dialog").first
        modal.wait_for(state="visible", timeout=settings.ELEMENT_WAIT_TIMEOUT_MS)

        inputs = modal.locator("input")
        inputs.first.wait_for(state="visible", timeout=settings.ELEMENT_WAIT_TIMEOUT_MS)
        time.sleep(0.5)

        input_count = inputs.count()
        logger.info("[Quasar] Modal Date & Time detectado con %s campos input", input_count)

        if input_count >= 4:
            end_time_str = inputs.nth(3).input_value().strip()
            logger.info("[Quasar] Hora final en cámara: '%s'", end_time_str)

            start_time_val = None
            if end_time_str and ":" in end_time_str:
                try:
                    clean_time = end_time_str.split()[0] if " " in end_time_str else end_time_str
                    parts = [int(p) for p in clean_time.split(":")[:2]]
                    end_dt = datetime.now().replace(hour=parts[0], minute=parts[1], second=0)
                    start_dt = end_dt - timedelta(minutes=interval_minutes)
                    start_time_val = start_dt.strftime("%H:%M")
                except Exception as ex:
                    logger.debug("[Quasar] Error calculando Start Time: %s", ex)

            if not start_time_val:
                start_time_val = (datetime.now() - timedelta(minutes=interval_minutes)).strftime("%H:%M")

            logger.info("[Quasar] Escribiendo Start Time: '%s'...", start_time_val)
            start_input = inputs.nth(1)
            start_input.click(force=True)
            start_input.press("Control+A")
            start_input.fill(start_time_val)
            start_input.press("Tab")
            time.sleep(0.5)

        # Clic en Save dentro del modal
        logger.info("[Quasar] Guardando configuración del modal (Save)...")
        save_btn = modal.locator("button, .q-btn").filter(has_text="Save").first
        save_btn.wait_for(state="visible", timeout=settings.ELEMENT_WAIT_TIMEOUT_MS)
        save_btn.click(force=True)
        
        try:
            modal.wait_for(state="hidden", timeout=5000)
        except Exception:
            time.sleep(1.5)

        # 4. Paso 4: Clic en el botón Search en la vista de archivos
        logger.info("[Quasar] Paso 4: Presionando botón Search...")
        search_btn = page.locator(".q-page button, button, .q-btn").filter(has_text="Search").first
        search_btn.wait_for(state="visible", timeout=settings.ELEMENT_WAIT_TIMEOUT_MS)
        search_btn.click(force=True)

        logger.info("[Quasar] Búsqueda iniciada. Esperando resultados...")
        time.sleep(2)

        try:
            spinner = page.locator(".q-spinner, .q-loading, text='Searching...'").first
            if spinner.is_visible(timeout=3000):
                spinner.wait_for(state="hidden", timeout=settings.SEARCH_WAIT_TIMEOUT_MS)
        except Exception:
            pass

        time.sleep(2)
        return self._parse_quasar_table(page)

    def _parse_quasar_table(self, page: Page) -> List[RecordingItem]:
        """Extrae las grabaciones de la interfaz Quasar."""
        recordings: List[RecordingItem] = []
        max_wait = 20
        start_t = time.time()

        while time.time() - start_t < max_wait:
            found_rows = page.evaluate("""() => {
                const rows = Array.from(document.querySelectorAll("table.q-table tbody tr, .q-table tbody tr, table tbody tr, .q-table__grid-item"));
                const items = [];
                for (const r of rows) {
                    const txt = (r.innerText || "").trim();
                    if (!txt || txt.includes("No data") || txt.includes("No search results") || txt.includes("0 results") || txt.length > 500) {
                        continue;
                    }
                    const cells = Array.from(r.querySelectorAll("td, .q-td, div.cell")).map(c => (c.innerText || "").trim()).filter(t => t.length > 0);
                    if (cells.length >= 2 || (txt.includes("mov") || txt.includes("Motion") || txt.includes("Today at") || txt.includes("202"))) {
                        items.push({
                            text: txt,
                            cells: cells.length > 0 ? cells : [txt]
                        });
                    }
                }
                return items;
            }""")

            if found_rows and len(found_rows) > 0:
                logger.info("[Quasar] ¡Grabaciones detectadas en la tabla! (Total: %s registros)", len(found_rows))
                for i, row_data in enumerate(found_rows):
                    cells = row_data.get("cells", [])
                    txt = row_data.get("text", "")
                    
                    start_time_str = "Activo"
                    file_name = f"File_{i+1}"
                    
                    for c in cells:
                        dt = parse_camera_datetime(c)
                        if dt:
                            start_time_str = c
                            break
                        if c.startswith("mov") or ".mp4" in c or ".avi" in c:
                            file_name = c

                    if start_time_str == "Activo":
                        dt = parse_camera_datetime(txt)
                        if dt:
                            start_time_str = dt.strftime("%Y/%m/%d %H:%M:%S")

                    recordings.append(RecordingItem(
                        file_name=file_name,
                        storage="SD",
                        trigger_type="Motion",
                        start_time_str=start_time_str,
                        end_time_str=None,
                        media_type="Video clip",
                        start_time=parse_camera_datetime(start_time_str) if start_time_str != "Activo" else datetime.now()
                    ))
                return recordings

            time.sleep(1.0)

        logger.info("[Quasar] No se encontraron grabaciones tras esperar los 20 segundos.")
        return recordings

    # =========================================================================
    # MANEJO DE INTERFAZ 2: CLASSIC (/setup/)
    # =========================================================================
    def _handle_classic_interface(self, page: Page, base_url: str, interval_minutes: int) -> List[RecordingItem]:
        """Flujo para la interfaz clásica VIVOTEK (/setup/localstorage/storage_searching.html)."""
        search_page_url = f"{base_url.rstrip('/')}/setup/localstorage/storage_searching.html"
        logger.info("[Clásica] Navegando a página de búsqueda: %s", search_page_url)
        try:
            page.goto(search_page_url, wait_until="domcontentloaded", timeout=settings.PAGE_LOAD_TIMEOUT_MS)
            time.sleep(2)
        except Exception:
            pass

        if "storage_searching" not in page.url:
            logger.info("[Clásica] Navegando mediante menú lateral...")
            try:
                config_tab = page.locator(VIVOTEK_CLASSIC_SELECTORS["tab_configuration"]).first
                if config_tab.is_visible(timeout=5000):
                    config_tab.click()
                    time.sleep(2)

                storage_menu = page.locator(VIVOTEK_CLASSIC_SELECTORS["menu_storage"]).first
                if storage_menu.is_visible(timeout=10000):
                    storage_menu.click()
                    time.sleep(1.5)

                content_mgmt = page.locator(VIVOTEK_CLASSIC_SELECTORS["menu_content_management"]).first
                if content_mgmt.is_visible(timeout=10000):
                    content_mgmt.click()
                    time.sleep(2)
            except Exception as e:
                logger.warning("[Clásica] Aviso al navegar por menú: %s", e)

        # 1. Escribir los minutos en el campo de texto
        logger.info("[Clásica] Configurando búsqueda de los últimos %s minutos...", interval_minutes)
        try:
            input_mins = page.locator(VIVOTEK_CLASSIC_SELECTORS["input_minutes"]).first
            input_mins.wait_for(state="visible", timeout=settings.ELEMENT_WAIT_TIMEOUT_MS)
            input_mins.click()
            input_mins.press("Control+A")
            input_mins.fill(str(interval_minutes))
            input_mins.press("Tab")
            time.sleep(0.5)
            logger.info("[Clásica] Minutos ingresados: %s", interval_minutes)
        except Exception as ex:
            logger.warning("[Clásica] No se pudo escribir en el campo de minutos: %s", ex)

        # 2. Hacer clic en el botón 'minute(s)' para activar el cálculo de fecha/hora de 5 minutos
        try:
            btn_min = page.locator(VIVOTEK_CLASSIC_SELECTORS["btn_minutes"]).first
            if btn_min.is_visible(timeout=5000):
                btn_min.click()
                logger.info("[Clásica] Botón 'minute(s)' clickeado para activar el cálculo de 5 minutos.")
                time.sleep(1)
        except Exception as ex:
            logger.warning("[Clásica] No se pudo hacer clic en el botón 'minute(s)': %s", ex)

        # 3. Clic en el botón Search
        search_btn = page.locator(VIVOTEK_CLASSIC_SELECTORS["btn_search"]).first
        search_btn.wait_for(state="visible", timeout=settings.ELEMENT_WAIT_TIMEOUT_MS)
        search_btn.click()
        logger.info("[Clásica] Botón Search presionado. Esperando resultados...")

        # 4. Esperar y verificar si aparecen filas con grabaciones en la tabla de Search results
        time.sleep(2.5)
        recordings: List[RecordingItem] = []

        max_wait = 20
        start_t = time.time()
        while time.time() - start_t < max_wait:
            all_found_items = []
            
            # Buscar en el frame principal y en cualquier sub-frame (iframe/frameset)
            for f in page.frames:
                try:
                    items = f.evaluate("""() => {
                        const results = [];
                        // 1. Buscar filas de tabla convencionales o contenedores de fila
                        const allRows = Array.from(document.querySelectorAll("tr, div.row, div.grid-row, div[role='row']"));
                        for (const r of allRows) {
                            const txt = (r.innerText || "").trim();
                            // Ignorar cabeceras y textos largos del formulario superior
                            if (!txt || txt.length > 300 || txt.includes("Search for last") || txt.includes("Content management")) {
                                continue;
                            }
                            if ((txt.includes("Today at") || txt.includes("Yesterday at") || txt.includes("mov")) && 
                                (txt.includes("Motion") || txt.includes("SD") || txt.includes("PM") || txt.includes("AM"))) {
                                results.push(txt);
                            }
                        }

                        // 2. Si no encontró por filas completas, buscar celdas o elementos de fecha/hora de resultados
                        if (results.length === 0) {
                            const timeElements = Array.from(document.querySelectorAll("td, div, span, p, font, nobr, a"));
                            for (const el of timeElements) {
                                const txt = (el.innerText || "").trim();
                                if (txt.length > 5 && txt.length < 80 && (txt.includes("Today at") || txt.includes("Yesterday at"))) {
                                    results.push(txt);
                                }
                            }
                        }

                        return results;
                    }""")
                    if items:
                        all_found_items.extend(items)
                except Exception:
                    pass

            if all_found_items:
                logger.info("[Clásica] ¡Grabaciones detectadas en la interfaz! (%s elementos encontrados)", len(all_found_items))
                # Extraer la fecha/hora más representativa
                latest_str = "Activo (Reciente)"
                for itm in all_found_items:
                    if "Today at" in itm or "Yesterday at" in itm:
                        # Si es un texto de fila completa con múltiples líneas, tomar la línea con la hora
                        lines = [line.strip() for line in itm.split("\n") if "Today at" in line or "Yesterday at" in line]
                        if lines:
                            latest_str = lines[0]
                        else:
                            latest_str = itm.strip()
                        break

                for idx, itm in enumerate(all_found_items[:20]):
                    file_name = f"movRecord_{idx+1}"
                    for part in itm.split():
                        if part.startswith("mov") or ".mp4" in part:
                            file_name = part
                            break

                    recordings.append(RecordingItem(
                        file_name=file_name,
                        storage="SD",
                        trigger_type="Motion",
                        start_time_str=latest_str,
                        end_time_str=None,
                        media_type="Video clip",
                        start_time=datetime.now()
                    ))
                return recordings

            time.sleep(1.0)

        logger.info("[Clásica] No se encontraron filas de grabaciones tras la búsqueda.")
        return recordings

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
