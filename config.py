# config.py
import os

URL = "https://naves.dpworldcallao.com.pe/programacion/"
DATA_FILE = "etb_data.json"
SENT_NOTIFICATIONS_FILE = "sent_notifications.json"
ERROR_STATE_FILE = "error_state.json"
ETD_FILTER_DAYS = 15

# Credenciales seguras leídas desde GitHub Secrets
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

# Configuración del comportamiento del script
ETB_CHANGE_THRESHOLD_HOURS = 2
CAMPOS_A_MONITORIAR = [
    "ETB", "MANIFEST", "ATA", "ETD", "ATD", "SERVICE", 
    "DRY CUTOFF", "REEFER CUTOFF"
]
# Configuración del servidor de correo
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
