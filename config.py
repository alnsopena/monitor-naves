# config.py
import os

URL = "https://naves.dpworldcallao.com.pe/programacion/"
DATA_FILE = "etb_data.json"
ETB_CHANGE_THRESHOLD_HOURS = 2
CAMPOS_A_MONITORIAR = [
    "ETB", "MANIFEST", "ATA", "ETD", "ATD", "SERVICE", 
    "DRY CUTOFF", "REEFER CUTOFF"
]

# AHORA SE LEE DESDE LOS SECRETS DE GITHUB DE FORMA SEGURA
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
