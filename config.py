# config.py
import os

URL = "https://naves.dpworldcallao.com.pe/programacion/"
DATA_FILE = "etb_data.json"
SENT_NOTIFICATIONS_FILE = "sent_notifications.json"
ERROR_STATE_FILE = "error_state.json"

ETD_FILTER_DAYS = 15
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
ETB_CHANGE_THRESHOLD_HOURS = 2

# CORREGIDO: Lista de campos en una sola línea para evitar errores de copiado.
CAMPOS_A_MONITORIAR = ["ETB", "MANIFEST", "ATA", "ETD", "ATD", "SERVICE", "DRY CUTOFF", "REEFER CUTOFF"]
