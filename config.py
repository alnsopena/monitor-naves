# config.py
# Archivo central para todas las configuraciones del proyecto.

# URL del sitio a monitorear
URL = "https://naves.dpworldcallao.com.pe/programacion/"

# Archivo para guardar el estado de las naves
DATA_FILE = "etb_data.json"

# Tópico de ntfy.sh (lo moveremos a secretos de GitHub en el siguiente paso)
NTFY_TOPIC = "cambios-naves-zim-9w3z5z"

# Umbral en horas para considerar un cambio de ETB como "significativo"
ETB_CHANGE_THRESHOLD_HOURS = 2

# Lista de todas las columnas que nos interesan de la tabla
CAMPOS_A_MONITORIAR = [
    "ETB", "MANIFEST", "ATA", "ETD", "ATD", "SERVICE", 
    "DRY CUTOFF", "REEFER CUTOFF"
]
