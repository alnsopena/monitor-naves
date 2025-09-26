# config.py
import os

URL = "https://naves.dpworldcallao.com.pe/programacion/"
DATA_FILE = "etb_data.json"
SENT_NOTIFICATIONS_FILE = "sent_notifications.json"
ERROR_STATE_FILE = "error_state.json"

# --- CONFIGURACIÓN DE CORREO ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
EMAIL_FORWARD_ADDRESS = os.getenv("EMAIL_FORWARD_ADDRESS")

# --- OTRAS CONFIGURACIONES ---
ETD_FILTER_DAYS = 15
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
ETB_CHANGE_THRESHOLD_HOURS = 2
CAMPOS_A_MONITORIAR = ["ETB", "MANIFEST", "ATA", "ETD", "ATD", "SERVICE", "DRY CUTOFF", "REEFER CUTOFF"]
