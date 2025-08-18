# main.py
# Script principal que orquesta el proceso de monitoreo.

import os
import json
import pandas as pd
from datetime import datetime

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
            for campo in config.CAMPOS_A_MONITORIAR:
                valor_nuevo = datos_nuevos[clave_viaje].get(campo)
                valor_viejo = datos_viejos[clave_viaje].get(campo)
                
                if valor_nuevo != valor_viejo:
                    # Lógica de notificación de cambios (simplificada por ahora, la mejoraremos después)
                    titulo = f"⚠️📝 Alerta de Cambio: {nombre_nave}"
                    mensaje = f"Campo '{campo}' ha cambiado.\nAnterior: {valor_viejo}\nNuevo: {valor_nuevo}"
                    enviar_notificacion(titulo, mensaje, tags="warning")

    with open(config.DATA_FILE, 'w') as f:
        json.dump(datos_nuevos, f, indent=4)
    print("Revisión de cambios completada.")


def enviar_resumen_diario():
    """Envía un resumen diario y las alertas de plazos."""
    print("Generando resumen diario y alertas...")
    df = obtener_tabla_naves()
    if df is None: return
    
    df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
    print(f"Se encontraron {len(df_zim)} naves para el resumen.")

    if df_zim.empty:
        enviar_notificacion("📰 resumen Diario de Naves ZIM", "No hay naves de ZIM activas en la programación de hoy.", tags="newspaper")
        return
        
    # (Aquí añadiremos la lógica de las alertas de plazos en el futuro)
    
    mensaje_resumen = ""
    for _, nave in df_zim.iterrows():
        nombre_nave = nave.get('VESSEL NAME', 'N/A')
        etb_str = pd.Series(nave.get('ETB', '---')).fillna('---').iloc[0]
        etd_str = pd.Series(nave.get('ETD', '---')).fillna('---').iloc[0]
        mensaje_resumen += f"\n- {nombre_nave}:\n  ETB: {etb_str}\n  ETD: {etd_str}\n"

    enviar_notificacion("📰 resumen Diario de Naves ZIM", mensaje_resumen.strip(), tags="newspaper")
    print("Resumen diario enviado.")


if __name__ == "__main__":
    # La lógica para decidir qué hacer se simplificará en el próximo paso
    # cuando optimicemos el archivo .yml
    job_type = os.getenv('JOB_TYPE', 'REGULAR_CHECK')

    if job_type == 'DAILY_SUMMARY':
        enviar_resumen_diario()
    else:
        revisar_cambios()
