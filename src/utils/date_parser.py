import re
from datetime import datetime, timedelta
from typing import Optional

DATE_PATTERNS = [
    # YYYY/MM/DD HH:MM:SS (formato común Vivotek)
    r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})",
    # MM/DD/YYYY o DD/MM/YYYY con hora y opcional AM/PM
    r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?\s*(am|pm)?",
    # YYYYMMDD_HHMMSS (nombres de archivo)
    r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})",
]

def parse_camera_datetime(date_str: str) -> Optional[datetime]:
    """Parsea una cadena de texto a un objeto datetime reconociendo formatos clásicos y modernos."""
    if not date_str:
        return None

    clean_str = date_str.strip()
    now = datetime.now()

    # 1. Manejar formatos relativos tipo 'Today at 5:30 PM' o 'Yesterday at 5:30 PM'
    today_match = re.search(r"(today|hoy)\s+(?:at|a\s+las)?\s*(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?\s*(am|pm)?", clean_str, re.IGNORECASE)
    if today_match:
        h, m = int(today_match.group(2)), int(today_match.group(3))
        s = int(today_match.group(4)) if today_match.group(4) else 0
        ampm = today_match.group(5)
        if ampm:
            if ampm.lower() == "pm" and h < 12:
                h += 12
            elif ampm.lower() == "am" and h == 12:
                h = 0
        return now.replace(hour=h, minute=m, second=s, microsecond=0)

    yesterday_match = re.search(r"(yesterday|ayer)\s+(?:at|a\s+las)?\s*(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?\s*(am|pm)?", clean_str, re.IGNORECASE)
    if yesterday_match:
        h, m = int(yesterday_match.group(2)), int(yesterday_match.group(3))
        s = int(yesterday_match.group(4)) if yesterday_match.group(4) else 0
        ampm = yesterday_match.group(5)
        if ampm:
            if ampm.lower() == "pm" and h < 12:
                h += 12
            elif ampm.lower() == "am" and h == 12:
                h = 0
        yesterday = now - timedelta(days=1)
        return yesterday.replace(hour=h, minute=m, second=s, microsecond=0)

    # 2. Formatos directos con strptime (incluyendo MM/DD/YYYY de la interfaz clásica)
    formats_to_try = [
        # Formatos año primero
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %I:%M:%S %p",
        "%Y/%m/%d %I:%M %p",
        "%Y-%m-%d %I:%M:%S %p",
        "%Y-%m-%d %I:%M %p",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M",
        
        # Formatos mes primero (MM/DD/YYYY - Vivotek Clásica)
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%m-%d-%Y %I:%M:%S %p",
        "%m-%d-%Y %I:%M %p",
        "%m/%d/%Y %H:%M:%S",
        "%m-%d-%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m-%d-%Y %H:%M",

        # Formatos día primero (DD/MM/YYYY)
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M",
        
        # Nombres de archivo y horas simples
        "%Y%m%d_%H%M%S",
        "%Y%m%d%H%M%S",
        "%I:%M:%S %p",
        "%I:%M %p",
        "%H:%M:%S",
        "%H:%M"
    ]

    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(clean_str, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=now.year, month=now.month, day=now.day)
            return dt
        except ValueError:
            continue

    # 3. Buscar con Regex para fechas con espaciados variables
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, clean_str, re.IGNORECASE)
        if match:
            raw_groups = match.groups()
            try:
                if len(raw_groups) == 7: # MM/DD/YYYY HH:MM:SS AM/PM
                    g1, g2, year, h, m, s, ampm = raw_groups
                    g1, g2, year = int(g1), int(g2), int(year)
                    h, m = int(h), int(m)
                    s = int(s) if s else 0
                    if ampm:
                        if ampm.lower() == "pm" and h < 12:
                            h += 12
                        elif ampm.lower() == "am" and h == 12:
                            h = 0
                    # Asumir MM/DD si g1 <= 12
                    if g1 <= 12 and g2 <= 31:
                        return datetime(year, g1, g2, h, m, s)
                    else:
                        return datetime(year, g2, g1, h, m, s)
            except Exception:
                continue

    return None

def is_within_last_hours(dt: datetime, hours: int = 24) -> bool:
    """Verifica si un datetime está dentro de las últimas N horas respecto a ahora."""
    if not dt:
        return False
    now = datetime.now()
    cutoff = now - timedelta(hours=hours)
    future_buffer = now + timedelta(hours=2)
    return cutoff <= dt <= future_buffer
