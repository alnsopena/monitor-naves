# main.py
# Script principal que orquesta el proceso de monitoreo.

import os
import json
import pandas as pd
from datetime import datetime
import pytz

import config
from notifier import enviar_notificacion
from scraper import obtener_tabla_naves, get_lima_time

def parse_date(date_str):
    """Convierte un string de fecha a un objeto datetime con zona horaria."""
    if not date_str or date_str == '---':
        return None
    try:
        lima_tz = pytz.timezone('America/Lima')
        dt = datetime.strptime(date_str, '%d-%m-%Y %H:%M:%S')
        return lima_tz.localize(dt)
    except (ValueError, TypeError):
        return None

def revisar_cambios():
    """Compara los datos actuales con los viejos y notifica si hay cambios."""
    print("Iniciando revisión de cambios...")
    try:
        with open(config.DATA_FILE, 'r') as f:
            datos_viejos = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        datos_viejos = {}
        
    datos_nuevos = {}
    df = obtener_tabla_naves()
    if df is None: return

    df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
    print(f"Se encontraron {len(df_zim)} naves de ZIM activas.")

    if df_zim.empty:
        with open(config.DATA_FILE, 'w') as f:
            json.dump({}, f)
        return

    for _, nave in df_zim.iterrows():
        nombre_nave = nave['VESSEL NAME']
        ib_vyg = nave['I/B VYG']
        clave_viaje = f"{nombre_nave}-{ib_vyg}"
        
        datos_nuevos[clave_viaje] = {campo: pd.Series(nave.get(campo, '---')).fillna('---').iloc[0] for campo in config.CAMPOS_A_MONITORIAR}
        
        if clave_viaje not in datos_viejos:
            titulo = f"🚢➡️ Nueva Nave ZIM: {nombre_nave}"
            mensaje = f"Se añadió la nave {nombre_nave} ({ib_vyg}) a la programación."
            enviar_notificacion(titulo, mensaje, tags="ship")
        else:
            # MEJORA 4: Lógica para agrupar notificaciones de cambio
            cambios_detectados = []
            es_alerta_mayor = False

            for campo in config.CAMPOS_A_MONITORIAR:
                valor_nuevo = datos_nuevos[clave_viaje].get(campo)
                valor_viejo = datos_viejos[clave_viaje].get(campo)
                
                if valor_nuevo != valor_viejo:
                    if campo == "ETB":
                        fecha_vieja = parse_date(valor_viejo)
                        fecha_nueva = parse_date(valor_nuevo)
                        if fecha_vieja and fecha_nueva:
                            diferencia_horas = abs((fecha_nueva - fecha_vieja).total_seconds() / 3600)
                            if diferencia_horas > config.ETB_CHANGE_THRESHOLD_HOURS:
                                es_alerta_mayor = True
                                detalle_cambio = f"Cambio significativo de {diferencia_horas:.1f}h
