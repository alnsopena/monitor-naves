# config.py
import os

URL = "https://naves.dpworldcallao.com.pe/programacion/"
DATA_FILE = "etb_data.json"

# NUEVO: Plazo en días para filtrar las naves por su fecha de salida (ETD)
ETD_FILTER_DAYS = 15

# Tópico de ntfy.sh (se lee desde los secretos de GitHub)
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

# Umbral en horas para considerar un cambio de ETB como "significativo"
ETB_CHANGE_THRESHOLD_HOURS = 2

# Lista de todas las columnas que nos interesan de la tabla
CAMPOS_A_MONITORIAR = [
    "ETB", "MANIFEST", "ATA", "ETD", "ATD", "SERVICE", 
    "DRY CUTOFF", "REEFER CUTOFF"
]
