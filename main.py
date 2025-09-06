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

def generar_y_enviar_resumen(df_zim, titulo):
    """Construye y envía el mensaje de resumen enriquecido."""
    lima_now = get_lima_time()
    mensaje_resumen = ""
    for _, nave in df_zim.iterrows():
        nombre_nave = nave.get('VESSEL NAME', 'N/A')
        ib_vyg = pd.Series(nave.get('I/B VYG', '')).fillna('').iloc[0]
        identificador_nave = f"{nombre_nave} {ib_vyg}".strip()

        etb_str = pd.Series(nave.get('ETB', '---')).fillna('---').iloc[0]
        etd_str = pd.Series(nave.get('ETD', '---')).fillna('---').iloc[0]
        ata_str = pd.Series(nave.get('ATA', '---')).fillna('---').iloc[0]
        atd_str = pd.Series(nave.get('ATD', '---')).fillna('---').iloc[0]
        # MODIFICADO: Se extrae el MANIFEST
        manifest_str = pd.Series(nave.get('MANIFEST', '---')).fillna('---').iloc[0]

        etb_date = parse_date(etb_str)
        ata_date = parse_date(ata_str)
        atd_date = parse_date(atd_str)

        status_emoji = '🗓️'
        if atd_date and atd_date < lima_now: status_emoji = '➡️'
        elif ata_date and ata_date < lima_now: status_emoji = '⚓'
        elif etb_date and (etb_date - lima_now).total_seconds() <= 0: status_emoji = '⚓'
        elif etb_date and (etb_date - lima_now).total_seconds() / 3600 <= 24: status_emoji = '⏳'
        
        # MODIFICADO: Se añade el MANIFEST al mensaje del resumen
        mensaje_resumen += f"\n{status_emoji} **{identificador_nave}**\n  Manifest: {manifest_str}\n  ETB: {etb_str}\n  ETD: {etd_str}\n"

    enviar_notificacion(titulo, mensaje_resumen.strip(), tags="newspaper")
    print("Resumen enviado.")

def revisar_cambios():
    """Compara los datos actuales con los viejos y si hay cambios, envía un resumen completo."""
    print("Iniciando revisión de cambios...")
    try:
        with open(config.DATA_FILE, 'r') as f:
            datos_viejos = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        datos_viejos = {}
        
    df = obtener_tabla_naves()
    if df is None: return

    df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
    print(f"Se encontraron {len(df_zim)} naves de ZIM activas.")

    if df_zim.empty:
        with open(config.DATA_FILE, 'w') as f:
            json.dump({}, f)
        return

    hubo_cambios = False
    datos_nuevos = {}
    claves_nuevas = set()

    for _, nave in df_zim.iterrows():
        nombre_nave = nave['VESSEL NAME']
        ib_vyg = nave['I/B VYG']
        clave_viaje = f"{nombre_nave}-{ib_vyg}"
        claves_nuevas.add(clave_viaje)
        
        datos_nuevos[clave_viaje] = {campo: pd.Series(nave.get(campo, '---')).fillna('---').iloc[0] for campo in config.CAMPOS_A_MONITORIAR}
        
        if clave_viaje not in datos_viejos or datos_nuevos[clave_viaje] != datos_viejos[clave_viaje]:
            hubo_cambios = True

    # Comprobar si alguna nave fue eliminada
    if set(datos_viejos.keys()) != claves_nuevas:
        hubo_cambios = True

    with open(config.DATA_FILE, 'w') as f:
        json.dump(datos_nuevos, f, indent=4)
    
    if hubo_cambios:
        print("Cambios detectados. Enviando resumen actualizado...")
        generar_y_enviar_resumen(df_zim, "📰 resumen ZIM Actualizado por Cambios")
    else:
        print("Revisión completada. No se detectaron cambios.")

def enviar_resumen_diario():
    """Envía un resumen diario y las alertas de plazos."""
    print("Generando resumen diario y alertas de plazos...")
    df = obtener_tabla_naves()
    if df is None: return
    
    df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
    print(f"Se encontraron {len(df_zim)} naves para el resumen.")

    if not df_zim.empty:
        lima_now = get_lima_time()
        for _, nave in df_zim.iterrows():
            nombre_nave = nave.get('VESSEL NAME', 'N/A')
            ib_vyg = pd.Series(nave.get('I/B VYG', '')).fillna('').iloc[0]
            identificador_nave = f"{nombre_nave} {ib_vyg}".strip()
            etb_str = pd.Series(nave.get('ETB', '---')).fillna('---').iloc[0]
            dry_cutoff_str = pd.Series(nave.get('DRY CUTOFF', '---')).fillna('---').iloc[0]
            reefer_cutoff_str = pd.Series(nave.get('REEFER CUTOFF', '---')).fillna('---').iloc[0]
            service = pd.Series(nave.get('SERVICE', '---')).fillna('---').iloc[0]
            atd_str = pd.Series(nave.get('ATD', '---')).fillna('---').iloc[0]
            etb_date = parse_date(etb_str)
            atd_date = parse_date(atd_str)

            if etb_date:
                diff_to_etb_hours = (etb_date - lima_now).total_seconds() / 3600
                if 227.75 <= diff_to_etb_hours < 228:
                    enviar_notificacion(f"⚠️📝 Recordatorio MYC: {identificador_nave}", f"Faltan 9.5 días para el ETB.\nEs momento de crearla en el sistema MYC.", tags="bell")
                if 47.75 <= diff_to_etb_hours < 48:
                    if service == 'ZCX NB':
                        enviar_notificacion(f"⚠️📝 Alerta Aduanas (USA/Canadá): {identificador_nave}", "Faltan 48h para el ETB. Realizar transmisión para Aduana Americana y Canadiense.", tags="customs")
                    elif service == 'ZAT':
                        enviar_notificacion(f"⚠️📝 Alerta Aduanas (China): {identificador_nave}", "Faltan 48h para el ETB. Realizar transmisión para Aduana China.", tags="customs")
            
            cutoff_date = min(filter(None, [parse_date(dry_cutoff_str), parse_date(reefer_cutoff_str)])) if any([dry_cutoff_str != '---', reefer_cutoff_str != '---']) else None
            if cutoff_date:
                diff_to_cutoff = (cutoff_date - lima_now).total_seconds() / 3600
                if 23.75 <= diff_to_cutoff < 24:
                    enviar_notificacion(f"‼️🚨 Alerta de Cierre Documentario (24H): {identificador_nave}", "Faltan 24h para el Cut-Off. Asegúrate de procesar la matriz/correctores.", tags="bangbang")

            if atd_date:
                diff_from_atd = (lima_now - atd_date).total_seconds() / 3600
                if 6 <= diff_from_atd < 6.25:
                    enviar_notificacion(f"⚠️📝 Recordatorio Post-Zarpe (6H): {identificador_nave}", "Han pasado 6h desde el zarpe real (ATD). Recordar enviar aviso a clientes.", tags="email")
                if 24 <= diff_from_atd < 24.25:
                    enviar_notificacion(f"⚠️📝 Recordatorio Post-Zarpe (24H): {identificador_nave}", "Han pasado 24h desde el zarpe real (ATD). Recordar cerrar BLs y dar conformidad.", tags="page_facing_up")

    if not df_zim.empty:
        generar_y_enviar_resumen(df_zim, "📰 resumen Diario de Naves ZIM")
    else:
        enviar_notificacion("📰 resumen Diario de Naves ZIM", "No hay naves de ZIM activas en la programación de hoy.", tags="newspaper")

if __name__ == "__main__":
    now = get_lima_time()
    is_summary_time = False
    if now.hour == 6 and 0 <= now.minute < 15: is_summary_time = True
    if now.hour == 17 and 30 <= now.minute < 45: is_summary_time = True
    if os.getenv('GITHUB_EVENT_NAME') == 'workflow_dispatch':
        is_summary_time = False
        print("Ejecución manual detectada. Forzando revisión de cambios.")
    
    if is_summary_time:
        print(f"Hora de resumen detectada ({now.strftime('%H:%M')}). Ejecutando resumen diario.")
        enviar_resumen_diario()
    else:
        print(f"Hora normal ({now.strftime('%H:%M')}). Ejecutando revisión de cambios.")
        revisar_cambios()
