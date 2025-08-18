# main.py
import os
import json
import pandas as pd
from datetime import datetime

import config
from notifier import enviar_notificacion
from scraper import obtener_tabla_naves, get_lima_time

# (La función parse_date y revisar_cambios no cambian, por brevedad no se muestran aquí,
# pero deben permanecer en tu archivo. El código completo está abajo.)

# ... (código de las funciones revisar_cambios, etc. se mantiene igual) ...

if __name__ == "__main__":
    now = get_lima_time()
    is_summary_time = False

    # Condición para el resumen de la mañana (6:00 - 6:14 AM)
    if now.hour == 6 and 0 <= now.minute < 15:
        is_summary_time = True

    # Condición para el resumen de la tarde (5:30 - 5:44 PM)
    if now.hour == 17 and 30 <= now.minute < 45:
        is_summary_time = True

    # Si es una ejecución manual, siempre hará una revisión de cambios
    # La variable GITHUB_EVENT_NAME nos la da GitHub Actions
    if os.getenv('GITHUB_EVENT_NAME') == 'workflow_dispatch':
        is_summary_time = False
        print("Ejecución manual detectada. Forzando revisión de cambios.")

    if is_summary_time:
        print(f"Hora de resumen detectada ({now.strftime('%H:%M')}). Ejecutando resumen diario.")
        # Aquí iría la llamada a la función enviar_resumen_diario()
        # Nota: La lógica completa está en el bloque de código final.
    else:
        print(f"Hora normal ({now.strftime('%H:%M')}). Ejecutando revisión de cambios.")
        revisar_cambios()
