"""
Selectores y rutas de navegación para cámaras VIVOTEK (interfaz basada en Quasar/Vue y clásicas).
"""

VIVOTEK_SELECTORS = {
    # URLs directas de navegación hash
    "file_hash_url": "home.html#/file_general",
    
    # Elementos indicadores de que la interfaz cargó
    "ui_loaded_indicators": (
        "text=VIVOTEK, text=System, text=Live View, text=Installation, "
        "div.menu, nav, div.main-container, .q-layout"
    ),

    # Menú lateral System
    "menu_system": (
        "xpath=//div[contains(@class, 'q-expansion-item')][.//div[normalize-space()='System']] "
        "| //div[contains(@class, 'q-item')][.//div[normalize-space()='System']] "
        "| //span[normalize-space()='System'] "
        "| //div[normalize-space()='System']"
    ),
    
    # Opción File dentro del submenú
    "menu_file": (
        "xpath=//a[contains(@href, 'file_general')] "
        "| //div[contains(@class, 'q-item')][.//div[normalize-space()='File']] "
        "| //span[normalize-space()='File'] "
        "| //div[normalize-space()='File']"
    ),
    
    # Dropdown de Time frame
    "time_frame_dropdown": (
        "xpath=//div[contains(@class, 'q-select') or contains(@class, 'dropdown') or contains(@class, 'select')]"
        "[.//span[contains(text(), 'Time frame') or contains(text(), 'Last') or contains(text(), 'Custom') or contains(text(), '202')]] "
        "| //*[contains(text(), 'Time frame')]/ancestor::div[contains(@class, 'q-select') or contains(@class, 'q-field')] "
        "| //div[contains(@class, 'q-field')][.//span[contains(text(), 'Last 24 hours') or contains(text(), 'Custom') or contains(text(), 'Time frame')]]"
    ),
    
    # Opciones de Time frame
    "option_custom_interval": (
        "xpath=//div[contains(@class, 'q-item')][.//div[contains(text(), 'Custom time interval')]] "
        "| //li[contains(text(), 'Custom time interval')] "
        "| //span[contains(text(), 'Custom time interval')] "
        "| //div[normalize-space()='Custom time interval']"
    ),
    "option_last_24_hours": (
        "xpath=//div[contains(@class, 'q-item')][.//div[contains(text(), 'Last 24 hours')]] "
        "| //li[contains(text(), 'Last 24 hours')] "
        "| //div[contains(text(), 'Last 24 hours')]"
    ),
    
    # Modal Date & Time (Custom time interval)
    "modal_date_time": (
        "xpath=//div[contains(@class, 'q-dialog') or contains(@class, 'modal')][.//div[contains(text(), 'Date & Time') or contains(., 'Start time')]]"
    ),
    "modal_inputs": "xpath=//div[contains(@class, 'q-dialog') or contains(@class, 'modal')]//input",
    "modal_btn_save": (
        "xpath=//div[contains(@class, 'q-dialog') or contains(@class, 'modal')]//button[contains(., 'Save')] "
        "| //div[contains(@class, 'q-dialog')]//div[contains(@class, 'q-btn') and contains(., 'Save')] "
        "| //div[contains(@class, 'q-dialog')]//span[normalize-space()='Save']"
    ),
    "modal_btn_cancel": (
        "xpath=//div[contains(@class, 'q-dialog') or contains(@class, 'modal')]//button[contains(., 'Cancel')] "
        "| //div[contains(@class, 'q-dialog')]//div[contains(@class, 'q-btn') and contains(., 'Cancel')]"
    ),

    # Botón Search
    "btn_search": (
        "xpath=//button[contains(., 'Search')] "
        "| //div[contains(@class, 'q-btn') and contains(., 'Search')] "
        "| //div[contains(@class, 'btn') and contains(., 'Search')]"
    ),
    
    # Indicadores de carga y overlays
    "loading_indicator": "xpath=//*[contains(text(), 'Searching...') or contains(text(), 'Connecting to the web') or contains(@class, 'loading') or contains(@class, 'spinner')]",
    "connecting_mask": "xpath=//*[contains(text(), 'Connecting to the web')]",
    "searching_spinner": "xpath=//*[contains(text(), 'Searching...') or contains(@class, 'q-spinner') or contains(@class, 'spinner')]",
    
    # Resultados y tabla
    "no_results_text": "xpath=//*[contains(text(), 'No search results') or contains(text(), '0 results') or contains(text(), 'No data')]",
    "results_counter": "xpath=//*[contains(text(), 'results')]",
    "table_rows": "xpath=//table//tbody/tr | //div[contains(@class, 'table-row') or contains(@class, 'grid-row') or contains(@class, 'q-table__grid-item')]",
}
