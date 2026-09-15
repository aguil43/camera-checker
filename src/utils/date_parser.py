import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

DATE_PATTERNS = [
    # YYYY/MM/DD HH:MM:SS (formato común Vivotek)
    r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})",
    # DD/MM/YYYY HH:MM:SS
    r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})",
    # YYYYMMDD_HHMMSS (nombres de archivo)
    r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})",
]

def parse_camera_datetime(date_str: str) -> Optional[datetime]:
    """Parsea una cadena de texto a un objeto datetime reconociendo múltiples formatos."""
    if not date_str:
        return None

    clean_str = date_str.strip()

    # Formatos directos con strptime
    formats_to_try = [
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y%m%d_%H%M%S",
        "%Y%m%d%H%M%S",
    ]

    for fmt in formats_to_try:
        try:
            return datetime.strptime(clean_str, fmt)
        except ValueError:
            continue

    # Si no coincide exactamente, buscar con Regex
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, clean_str)
        if match:
            groups = [int(g) for g in match.groups()]
            try:
                if len(groups) == 6:
                    # Detectar si el primer grupo es el año (> 1900)
                    if groups[0] > 1900:
                        year, month, day, hour, minute, second = groups
                    else:
                        day, month, year, hour, minute, second = groups
                    return datetime(year, month, day, hour, minute, second)
            except ValueError:
                continue

    return None

def is_within_last_hours(dt: datetime, hours: int = 24) -> bool:
    """Verifica si un datetime está dentro de las últimas N horas respecto a ahora."""
    if not dt:
        return False
    now = datetime.now()
    cutoff = now - timedelta(hours=hours)
    # También asegurar que no sea del futuro lejano por desajuste horario leve
    future_buffer = now + timedelta(hours=2)
    return cutoff <= dt <= future_buffer
