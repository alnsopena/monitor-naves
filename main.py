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
            for campo in config.CAMPOS_A_MONITORIAR:
                valor_nuevo = datos_nuevos[clave_viaje].get(campo)
                valor_viejo = datos_viejos[clave_viaje].get(campo)
                
                if valor_nuevo != valor_viejo:
                    mensaje_base = f"Campo '{campo}' ha cambiado.\nAnterior: {valor_viejo}\nNuevo: {valor_nuevo}"
                    if campo == "ETB":
                        fecha_vieja = parse_date(valor_viejo)
                        fecha_nueva = parse_date(valor_nuevo)
                        if fecha_vieja and fecha_nueva:
                            diferencia_horas = abs((fecha_nueva - fecha_vieja).total_seconds() / 3600)
                            if diferencia_horas > config.ETB_CHANGE_THRESHOLD_HOURS:
                                titulo = f"‼️🚨 ALERTA MAYOR: {nombre_nave}"
                                mensaje = f"Cambio significativo de {diferencia_horas:.1f} horas en ETB.\nAnterior: {valor_viejo}\nNuevo: {valor_nuevo}"
                                enviar_notificacion(titulo, mensaje, tags="rotating_light")
                            else:
                                print(f"Cambio menor de ETB para {nombre_nave} ignorado ({diferencia_horas:.1f} horas).")
                        else:
                            titulo = f"⚠️📝 Alerta de Cambio: {nombre_nave}"
                            enviar_notificacion(titulo, mensaje_base, tags="warning")
                    else:
                        titulo = f"⚠️📝 Alerta de Cambio: {nombre_nave}"
                        enviar_notificacion(titulo, mensaje_base, tags="warning")

    with open(config.DATA_FILE, 'w') as f:
        json.dump(datos_nuevos, f, indent=4)
    print("Revisión de cambios completada.")


def enviar_resumen_diario():
    """Envía un resumen diario y las alertas de plazos."""
    print("Generando resumen diario y alertas de plazos...")
    df = obtener_tabla_naves()
    if df is None: return
    
    df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
    print(f"Se encontraron {len(df_zim)} naves para el resumen.")

    if df_zim.empty:
        enviar_notificacion("📰 resumen Diario de Naves ZIM", "No hay naves de ZIM activas en la programación de hoy.", tags="newspaper")
        return
    
    lima_now = get_lima_time()
    mensaje_resumen = ""

    for _, nave in df_zim.iterrows():
        nombre_nave = nave.get('VESSEL NAME', 'N/A')
        etb_str = pd.Series(nave.get('ETB', '---')).fillna('---').iloc[0]
        etd_str = pd.Series(nave.get('ETD', '---')).fillna('---').iloc[0]
        atd_str = pd.Series(nave.get('ATD', '---')).fillna('---').iloc[0]
        dry_cutoff_str = pd.Series(nave.get('DRY CUTOFF', '---')).fillna('---').iloc[0]
        reefer_cutoff_str = pd.Series(nave.get('REEFER CUTOFF', '---')).fillna('---').iloc[0]
        service = pd.Series(nave.get('SERVICE', '---')).fillna('---').iloc[0]

        etb_date = parse_date(etb_str)
        atd_date = parse_date(atd_str)

        if etb_date and (etb_date.date() - lima_now.date()).days == 8:
            enviar_notificacion(f"⚠️📝 Recordatorio MYC: {nombre_nave}", f"Faltan exactamente 8 días para el ETB de la nave {nombre_nave}.\nEs momento de crearla en el sistema MYC.", tags="bell")

        if etb_date:
            diff_to_etb = (etb_date - lima_now).total_seconds() / 3600
            if 47 <= diff_to_etb < 48:
                if service == 'ZCX NB':
                    enviar_notificacion(f"⚠️📝 Alerta Aduanas (USA/Canadá): {nombre_nave}", "Faltan 48 horas para el ETB. Realizar transmisión anticipada para Aduana Americana y Canadiense.", tags="customs")
                elif service == 'ZAT':
                    enviar_notificacion(f"⚠️📝 Alerta Aduanas (China): {nombre_nave}", "Faltan 48 horas para el ETB. Realizar transmisión anticipada para Aduana China.", tags="customs")
        
        cutoff_date = min(filter(None, [parse_date(dry_cutoff_str), parse_date(reefer_cutoff_str)])) if any([dry_cutoff_str != '---', reefer_cutoff_str != '---']) else None
        if cutoff_date:
            diff_to_cutoff = (cutoff_date - lima_now).total_seconds() / 3600
            if 23 <= diff_to_cutoff < 24:
                enviar_notificacion(f"‼️🚨 Alerta de Cierre Documentario (24H): {nombre_nave}", "Faltan 24 horas para el Cut-Off. Asegúrate de procesar la matriz/correctores para evitar penalidades.", tags="bangbang")

        if atd_date:
            diff_from_atd = (lima_now - atd_date).total_seconds() / 3600
            if 6 <= diff_from_atd < 6.25:
                enviar_notificacion(f"⚠️📝 Recordatorio Post-Zarpe (6H): {nombre_nave}", "Han pasado 6 horas desde el zarpe real (ATD). Recordar enviar aviso de zarpe a los clientes.", tags="email")
            if 24 <= diff_from_atd < 24.25:
                enviar_notificacion(f"⚠️📝 Recordatorio Post-Zarpe (24H): {nombre_nave}", "Han pasado 24 horas desde el zarpe real (ATD). Recordar cerrar BLs y dar conformidad de contenedores.", tags="page_facing_up")
        
        mensaje_resumen += f"\n- {nombre_nave}:\n  ETB: {etb_str}\n  ETD: {etd_str}\n"

    enviar_notificacion("📰 resumen Diario de Naves ZIM", mensaje_resumen.strip(), tags="newspaper")
    print("Resumen diario y alertas de plazos enviados.")

if __name__ == "__main__":
    now = get_lima_time()
    is_summary_time = False

    # Condición para el resumen de la mañana (6:00 - 6:14 AM, hora de Lima)
    if now.hour == 6 and 0 <= now.minute < 15:
        is_summary_time = True

    # Condición para el resumen de la tarde (5:30 - 5:44 PM, hora de Lima)
    if now.hour == 17 and 30 <= now.minute < 45:
        is_summary_time = True
    
    # GITHUB_EVENT_NAME es una variable que GitHub Actions nos da automáticamente
    if os.getenv('GITHUB_EVENT_NAME') == 'workflow_dispatch':
        is_summary_time = False
        print("Ejecución manual detectada. Forzando revisión de cambios.")

    if is_summary_time:
        print(f"Hora de resumen detectada ({now.strftime('%H:%M')}). Ejecutando resumen diario.")
        enviar_resumen_diario()
    else:
        print(f"Hora normal ({now.strftime('%H:%M')}). Ejecutando revisión de cambios.")
        revisar_cambios()
