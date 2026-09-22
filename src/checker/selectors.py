"""
Selectores y rutas de navegación para cámaras VIVOTEK:
- Interfaz 1: Quasar / Vue (Moderna)
- Interfaz 2: Classic Web UI (/setup/localstorage/storage_searching.html)
"""

# ==========================================
# INTERFAZ 1: VIVOTEK QUASAR / MODERNA
# ==========================================
VIVOTEK_QUASAR_SELECTORS = {
    "direct_url": "home.html#/file_general",
    
    # Menú lateral
    "menu_system": (
        "xpath=//div[contains(@class, 'q-expansion-item')][.//*[normalize-space()='System' or normalize-space()='Sistema']] "
        "| //div[contains(@class, 'q-item')][.//*[normalize-space()='System' or normalize-space()='Sistema']] "
        "| //*[normalize-space()='System'] "
        "| //*[normalize-space()='Sistema']"
    ),
    "menu_file": (
        "xpath=//a[contains(@href, 'file_general')] "
        "| //div[contains(@class, 'q-item')][.//*[normalize-space()='File' or normalize-space()='Archivo' or normalize-space()='Archivos']] "
        "| //*[normalize-space()='File'] "
        "| //*[normalize-space()='Archivos']"
    ),
    
    # Dropdown Time frame
    "time_frame_dropdown": (
        "xpath=//div[contains(@class, 'q-select') or contains(@class, 'q-field')]"
        "[.//*[contains(text(), 'Time frame') or contains(text(), 'Last') or contains(text(), 'Custom') or contains(text(), '202') or contains(text(), 'hour')]] "
        "| //*[contains(text(), 'Time frame')]/ancestor::div[contains(@class, 'q-field') or contains(@class, 'q-select')][1] "
        "| //div[contains(@class, 'q-select')]"
    ),
    "option_custom_interval": (
        "xpath=//div[contains(@class, 'q-item') or contains(@class, 'q-menu') or contains(@class, 'q-list')]//*[contains(text(), 'Custom') or contains(text(), 'custom') or contains(text(), 'Personalizado')] "
        "| //*[contains(text(), 'Custom time interval')] "
        "| //div[normalize-space()='Custom time interval']"
    ),
    
    # Modal Date & Time
    "modal_date_time": (
        "xpath=//div[contains(@class, 'q-dialog') or contains(@class, 'modal') or contains(@class, 'q-card')]"
        "[.//*[contains(text(), 'Date & Time') or contains(., 'Start time') or contains(., 'End time')]] "
        "| //div[contains(@class, 'q-dialog')]"
    ),
    "modal_inputs": "xpath=//div[contains(@class, 'q-dialog') or contains(@class, 'modal')]//input",
    "modal_btn_save": (
        "xpath=//div[contains(@class, 'q-dialog') or contains(@class, 'modal') or contains(@class, 'q-card')]//*[(self::button or contains(@class, 'q-btn')) and (contains(., 'Save') or contains(., 'Guardar'))] "
        "| //div[contains(@class, 'q-dialog')]//button[contains(., 'Save')] "
        "| //div[contains(@class, 'q-dialog')]//span[normalize-space()='Save']"
    ),
    
    # Botón Search y Spinners
    "btn_search": (
        "xpath=//button[contains(., 'Search') or contains(., 'Buscar')] "
        "| //div[contains(@class, 'q-btn') and (contains(., 'Search') or contains(., 'Buscar'))] "
        "| //div[contains(@class, 'btn') and contains(., 'Search')]"
    ),
    "connecting_mask": "xpath=//*[contains(text(), 'Connecting to the web')]",
    "searching_spinner": "xpath=//*[contains(text(), 'Searching...') or contains(@class, 'q-spinner') or contains(@class, 'spinner')]",
    
    # Resultados
    "no_results_text": "xpath=//*[contains(text(), 'No search results') or contains(text(), '0 results') or contains(text(), 'No data')]",
    "table_rows": "xpath=//table//tbody/tr[td and not(.//th)] | //div[contains(@class, 'table-row') or contains(@class, 'grid-row') or contains(@class, 'q-table__grid-item')]",
}

# ==========================================
# INTERFAZ 2: VIVOTEK CLÁSICA (/setup/)
# ==========================================
VIVOTEK_CLASSIC_SELECTORS = {
    "direct_url": "setup/localstorage/storage_searching.html",
    
    # Pestañas superiores
    "tab_configuration": "xpath=//a[contains(text(), 'Configuration')] | //span[contains(text(), 'Configuration')] | //td[contains(., 'Configuration')]//a",
    
    # Menú lateral Storage -> Content management
    "menu_storage": "xpath=//a[normalize-space()='Storage'] | //span[normalize-space()='Storage'] | //td[contains(., 'Storage')] | //div[contains(text(), 'Storage')]",
    "menu_content_management": "xpath=//a[contains(text(), 'Content management')] | //span[contains(text(), 'Content management')] | //td[contains(., 'Content management')]",
    
    # Filtro de tiempo por minutos (Search for last [ X ] [ minute(s) ])
    "input_minutes": (
        "xpath=//input[@type='text' and (following-sibling::text()[contains(., 'minute')] or ../text()[contains(., 'minute')])] "
        "| //td[contains(., 'Search for last')]//input[@type='text'] "
        "| //input[contains(@id, 'min') or contains(@name, 'min')] "
        "| //input[@type='text'][following-sibling::input[@value='minute(s)'] or following-sibling::input[contains(@value, 'minute')]]"
    ),
    "btn_minutes": (
        "xpath=//input[@type='button' and contains(@value, 'minute')] "
        "| //button[contains(., 'minute')] "
        "| //span[contains(text(), 'minute(s)')] "
        "| //div[contains(text(), 'minute(s)')] "
        "| //input[contains(@value, 'minute')]"
    ),
    
    # Botón Search
    "btn_search": (
        "xpath=//button[contains(., 'Search')] "
        "| //input[@type='button' and contains(@value, 'Search')] "
        "| //input[@type='submit' and contains(@value, 'Search')] "
        "| //a[contains(., 'Search') or contains(@class, 'search')]"
    ),
    
    # Resultados y tabla específica de grabaciones
    "table_rows": (
        "xpath=//fieldset[.//legend[contains(text(), 'Search results')]]//table//tr[td and (not(.//th) and not(.//select) and not(.//input[@value='Download']))] "
        "| //table[.//th[contains(text(), 'Starting time') or contains(text(), 'Name')]]//tr[td and not(.//th) and not(.//select)] "
        "| //div[contains(@class, 'search_result')]//table//tr[td and not(.//th)]"
    ),
    "no_results_text": "xpath=//*[contains(text(), 'No search results') or contains(text(), '0 results') or contains(text(), 'No record') or contains(text(), 'No data')]",
}
