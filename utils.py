# utils.py
import json
import pytz
from datetime import datetime
import config

def is_in_error_state():
    """Comprueba si el script está actualmente en estado de error."""
    try:
        with open(config.ERROR_STATE_FILE, 'r') as f:
            return json.load(f).get("in_error_state", False)
    except (FileNotFoundError, json.JSONDecodeError):
        return False

def set_error_state(status: bool):
    """Establece el estado de error del script."""
    with open(config.ERROR_STATE_FILE, 'w') as f:
        json.dump({"in_error_state": status}, f)

def cargar_notificaciones_enviadas():
    """Carga el registro de notificaciones de plazo ya enviadas."""
    try:
        with open(config.SENT_NOTIFICATIONS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_notificaciones_enviadas(data):
    """Guarda el registro actualizado de notificaciones enviadas."""
    with open(config.SENT_NOTIFICATIONS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def cargar_rate_limit_state():
    """Carga el estado del control de límite de correos."""
    try:
        with open(config.RATE_LIMIT_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"change_emails_sent_today": 0, "last_change_email_timestamp": None, "today_date": None}

def guardar_rate_limit_state(data):
    """Guarda el estado del control de límite de correos."""
    with open(config.RATE_LIMIT_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def parse_date(date_str):
    """Convierte un string de fecha a un objeto datetime con zona horaria."""
    if not date_str or date_str == '---': return None
    try:
        lima_tz = pytz.timezone('America/Lima')
        dt = datetime.strptime(date_str, '%d-%m-%Y %H:%M:%S')
        return lima_tz.localize(dt)
    except (ValueError, TypeError): return None
