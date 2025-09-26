# config.py
import os

URL = "https://naves.dpworldcallao.com.pe/programacion/"
DATA_FILE = "etb_data.json"
SENT_NOTIFICATIONS_FILE = "sent_notifications.json"
ERROR_STATE_FILE = "error_state.json"

# --- CONFIGURACIÓN DE NOTIFICACIONES ---
# NTFY (se lee desde los secretos de GitHub)
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

# Correo (se lee desde los secretos de GitHub)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")


# --- OTRAS CONFIGURACIONES ---
ETD_FILTER_DAYS = 15
ETB_CHANGE_THRESHOLD_HOURS = 2
CAMPOS_A_MONITORIAR = [
    "ETB", "MANIFEST", "ATA", "ETD", "ATD", "SERVICE", 
    "DRY CUTOFF", "REE
