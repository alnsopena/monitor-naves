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
                                detalle_cambio = f"Cambio significativo de {diferencia_horas:.1f}h en ETB: de '{valor_viejo}' a '{valor_nuevo}'"
                                cambios_detectados.append(detalle_cambio)
                            else:
                                print(f"Cambio menor de ETB para {nombre_nave} ignorado.")
                        else:
                            cambios_detectados.append(f"Campo 'ETB' cambió de '{valor_viejo}' a '{valor_nuevo}'")
                    else:
                        cambios_detectados.append(f"Campo '{campo}' cambió de '{valor_viejo}' a '{valor_nuevo}'")

            if cambios_detectados:
                if es_alerta_mayor:
                    titulo = f"‼️🚨 Múltiples Cambios (MAYOR): {nombre_nave}"
                    tags = "rotating_light"
                else:
                    titulo = f"⚠️📝 Múltiples Cambios: {nombre_nave}"
                    tags = "warning"
                
                mensaje = "Se detectaron los siguientes cambios:\n- " + "\n- ".join(cambios_detectados)
                enviar_notificacion(titulo, mensaje, tags)

    with open(config.DATA_FILE, 'w') as f:
        json.dump(datos_nuevos, f, indent=4)
    print("Revisión de cambios completada.")


def enviar_resumen_diario():
    """Envía un resumen diario enriquecido y las alertas de plazos."""
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
        # Extracción de datos para el resumen y alertas
        nombre_nave = nave.get('VESSEL NAME', 'N/A')
        etb_str = pd.Series(nave.get('ETB', '---')).fillna('---').iloc[0]
        etd_str = pd.Series(nave.get('ETD', '---')).fillna('---').iloc[0]
        ata_str = pd.Series(nave.get('ATA', '---')).fillna('---').iloc[0]
        atd_str = pd.Series(nave.get('ATD', '---')).fillna('---').iloc[0]
        dry_cutoff_str = pd.Series(nave.get('DRY CUTOFF', '---')).fillna('---').iloc[0]
        reefer_cutoff_str = pd.Series(nave.get('REEFER CUTOFF', '---')).fillna('---').iloc[0]
        service = pd.Series(nave.get('SERVICE', '---')).fillna('---').iloc[0]

        etb_date = parse_date(etb_str)
        ata_date = parse_date(ata_str)
        atd_date = parse_date(atd_str)

        # Lógica de Alertas de Plazos (sin cambios)
        if etb_date and (etb_date.date() - lima_now.date()).days == 8:
            enviar_notificacion(f"⚠️📝 Recordatorio MYC: {nombre_nave}", f"Faltan exactamente 8 días para el ETB.\nEs momento de crearla en el sistema MYC.", tags="bell")
        if etb_date:
            diff_to_etb = (etb_date - lima_now).total_seconds() / 3600
            if 47 <= diff_to_etb < 48:
                if service == 'ZCX NB':
                    enviar_notificacion(f"⚠️📝 Alerta Aduanas (USA/Canadá): {nombre_nave}", "Faltan 48h para el ETB. Realizar transmisión para Aduana Americana y Canadiense.", tags="customs")
                elif service == 'ZAT':
                    enviar_notificacion(f"⚠️📝 Alerta Aduanas (China): {nombre_nave}", "Faltan 48h para el ETB. Realizar transmisión para Aduana China.", tags="customs")
        cutoff_date = min(filter(None, [parse_date(dry_cutoff_str), parse_date(reefer_cutoff_str)])) if any([dry_cutoff_str != '---', reefer_cutoff_str != '---']) else None
        if cutoff_date:
            diff_to_cutoff = (cutoff_date - lima_now).total_seconds() / 3600
            if 23 <= diff_to_cutoff < 24:
                enviar_notificacion(f"‼️🚨 Alerta de Cierre Documentario (24H): {nombre_nave}", "Faltan 24h para el Cut-Off. Asegúrate de procesar la matriz/correctores.", tags="bangbang")
        if atd_date:
            diff_from_atd = (lima_now - atd_date).total_seconds() / 3600
            if 6 <= diff_from_atd < 6.25:
                enviar_notificacion(f"⚠️📝 Recordatorio Post-Zarpe (6H): {nombre_nave}", "Han pasado 6h desde el zarpe real (ATD). Recordar enviar aviso a clientes.", tags="email")
            if 24 <= diff_from_atd < 24.25:
                enviar_notificacion(f"⚠️📝 Recordatorio Post-Zarpe (24H): {nombre_nave}", "Han pasado 24h desde el zarpe real (ATD). Recordar cerrar BLs y dar conformidad.", tags="page_facing_up")
        
        # MEJORA 4: Lógica para el Resumen Enriquecido con Emojis de Estado
        status_emoji = '🗓️' # Estado por defecto: Programado
        if atd_date and atd_date < lima_now:
            status_emoji = '➡️' # Zarpado
        elif ata_date and ata_date < lima_now:
            status_emoji = '⚓' # En Puerto
        elif etb_date and (etb_date - lima_now).total_seconds() <= 0:
            status_emoji = '⚓' # En Puerto (Pasó la hora de ETB)
        elif etb_date and (etb_date - lima_now).total_seconds() / 3600 <= 24:
            status_emoji = '⏳' # Próximo a Arribar
        
        mensaje_resumen += f"\n{status_emoji} **{nombre_nave}**\n  ETB: {etb_str}\n  ETD: {etd_str}\n"

    enviar_notificacion("📰 resumen Diario de Naves ZIM", mensaje_resumen.strip(), tags="newspaper")
    print("Resumen diario y alertas de plazos enviados.")


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
