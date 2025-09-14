# config.py
import os

URL = "https://naves.dpworldcallao.com.pe/programacion/"
DATA_FILE = "etb_data.json"
SENT_NOTIFICATIONS_FILE = "sent_notifications.json"

# NUEVO: Archivo para guardar si el script está en estado de error
ERROR_STATE_FILE = "error_state.json"

ETD_FILTER_DAYS = 15
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
ETB_CHANGE_THRESHOLD_HOURS = 2
CAMPOS_A_MONITORIAR = [
    "ETB", "MANIFEST", "ATA", "ETD", "ATD", "SERVICE", 
    "DRY CUTOFF", "REEFER CUTOFF"
]
