# config.py
import os

URL = "https://naves.dpworldcallao.com.pe/programacion/"
DATA_FILE = "etb_data.json"

# Archivo para registrar las notificaciones de plazo ya enviadas
SENT_NOTIFICATIONS_FILE = "sent_notifications.json"

ETD_FILTER_DAYS = 15
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
ETB_CHANGE_THRESHOLD_HOURS = 2
CAMPOS_A_MONITORIAR = [
    "ETB", "MANIFEST", "ATA", "ETD", "ATD", "SERVICE", 
    "DRY CUTOFF", "REEFER CUTOFF"
]
