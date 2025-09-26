# main.py
import os
import json
import pandas as pd
from datetime import datetime
import pytz

import config
# MODIFICADO: Importa las dos funciones específicas
from notifier import enviar_a_ntfy, enviar_a_correo
from scraper import obtener_tabla_naves
from utils import is_in_error_state, set_error_state, cargar_notificaciones_enviadas, guardar_notificaciones_enviadas, parse_date

def generar_y_enviar_resumen(df_zim, titulo):
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
        manifest_str = pd.Series(nave.get('MANIFEST', '---')).fillna('---').iloc[0]
        etb_date = parse_date(etb_str)
        ata_date = parse_date(ata_str)
        atd_date = parse_date(atd_str)
        status_emoji = '🗓️'
        if atd_date and atd_date < lima_now: status_emoji = '➡️'
        elif ata_date and ata_date < lima_now: status_emoji = '⚓'
        elif etb_date and (etb_date - lima_now).total_seconds() <= 0: status_emoji = '⚓'
        elif etb_date and (etb_date - lima_now).total_seconds() / 3600 <= 24: status_emoji = '⏳'
        mensaje_resumen += f"\n{status_emoji} **{identificador_nave}**\n  Manifest: {manifest_str}\n  ETB: {etb_str}\n  ETD: {etd_str}\n"

    # MODIFICADO: Envía el resumen a ambos canales
    enviar_a_ntfy(titulo, mensaje_resumen, tags="newspaper")
    enviar_a_correo(titulo, mensaje_resumen)
    print("Resumen enviado a todos los canales.")

def revisar_cambios():
    print("Iniciando revisión de cambios...")
    try:
        with open(config.DATA_FILE, 'r') as f: datos_viejos = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): datos_viejos = {}
        df = obtener_tabla_naves()
        if df is None: return
        df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
        if df_zim.empty:
            with open(config.DATA_FILE, 'w') as f: json.dump({}, f)
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
        if set(datos_viejos.keys()) != claves_nuevas: hubo_cambios = True
        with open(config.DATA_FILE, 'w') as f: json.dump(datos_nuevos, f, indent=4)
        if hubo_cambios:
            print("Cambios detectados. Enviando resumen actualizado...")
            generar_y_enviar_resumen(df_zim, "📰 resumen ZIM Actualizado por Cambios")
        else:
            print("Revisión completada. No se detectaron cambios.")
        if is_in_error_state():
            set_error_state(False)
            # MODIFICADO: Envía recuperación solo a ntfy
            enviar_a_ntfy("✅ Sistema Recuperado", "El script ha vuelto a funcionar correctamente.", tags="white_check_mark")
    except Exception as e:
        print(f"Error al procesar la revisión de cambios: {e}")
        if not is_in_error_state():
            # MODIFICADO: Envía errores solo a ntfy
            enviar_a_ntfy("‼️🚨 Error en Script de Naves", f"El script ha comenzado a fallar. Error: {e}", tags="x")
            set_error_state(True)

def enviar_resumen_diario():
    print("Generando resumen diario y alertas de plazos...")
    df = obtener_tabla_naves()
    if df is None: return
    df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
    notificaciones_enviadas = cargar_notificaciones_enviadas()
    lima_hoy_str = get_lima_time().strftime('%Y-%m-%d')
    claves_a_borrar = [k for k, v in notificaciones_enviadas.items() if (datetime.strptime(lima_hoy_str, '%Y-%m-%d') - datetime.strptime(v, '%Y-%m-%d')).days > 30]
    for k in claves_a_borrar: del notificaciones_enviadas[k]
    if not df_zim.empty:
        lima_now = get_lima_time()
        for _, nave in df_zim.iterrows():
            identificador_nave = f"{nave.get('VESSEL NAME', 'N/A')} {pd.Series(nave.get('I/B VYG', '')).fillna('').iloc[0]}".strip()
            clave_viaje = f"{nave.get('VESSEL NAME')}-{nave.get('I/B VYG')}"
            etb_date = parse_date(pd.Series(nave.get('ETB', '---')).fillna('---').iloc[0])
            if etb_date:
                diff_to_etb_hours = (etb_date - lima_now).total_seconds() / 3600
                llave_myc = f"{clave_viaje}-MYC"
                if 227.75 <= diff_to_etb_hours < 228 and llave_myc not in notificaciones_enviadas:
                    # MODIFICADO: Alertas de plazo solo a ntfy
                    enviar_a_ntfy(f"⚠️📝 Recordatorio MYC: {identificador_nave}", f"Faltan 9.5 días para el ETB.\nEs momento de crear la nave en el sistema MYC.", tags="bell")
                    notificaciones_enviadas[llave_myc] = lima_hoy_str
                # ... (y así para las demás alertas de plazo)
    if not df_zim.empty:
        generar_y_enviar_resumen(df_zim, "📰 resumen Diario de Naves ZIM")
    else:
        titulo_vacio = "📰 resumen Diario de Naves ZIM"
        mensaje_vacio = "No hay naves de ZIM activas en la programación de hoy."
        enviar_a_ntfy(titulo_vacio, mensaje_vacio, tags="newspaper")
        enviar_a_correo(titulo_vacio, mensaje_vacio)
    guardar_notificaciones_enviadas(notificaciones_enviadas)
    if is_in_error_state():
        set_error_state(False)
        enviar_a_ntfy("✅ Sistema Recuperado", "El script ha vuelto a funcionar correctamente.", tags="white_check_mark")

if __name__ == "__main__":
    # (El resto del archivo no cambia)
    now = get_lima_time()
    is_summary_time = False
    if now.hour == 6 and 0 <= now.minute < 15: is_summary_time = True
    if now.hour == 17 and 30 <= now.minute < 45: is_summary_time = True
    if os.getenv('GITHUB_EVENT_NAME') == 'workflow_dispatch':
        is_summary_time = False
        print("Ejecución manual detectada. Forzando revisión de cambios.")
    
    if is_summary_time:
        print("Hora de resumen detectada. Ejecutando resumen diario.")
        enviar_resumen_diario()
    else:
        print("Hora normal. Ejecutando revisión de cambios.")
        revisar_cambios()
