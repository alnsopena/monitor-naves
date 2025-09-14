# main.py
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import pytz

import config
from notifier import enviar_notificacion
# Se quita la importación circular, scraper ya no importa desde main
from scraper import obtener_tabla_naves, get_lima_time

# --- NUEVAS FUNCIONES DE ESTADO DE ERROR ---
def is_in_error_state():
    """Comprueba si el script está actualmente en estado de error."""
    try:
        with open(config.ERROR_STATE_FILE, 'r') as f:
            state = json.load(f)
            return state.get("in_error_state", False)
    except (FileNotFoundError, json.JSONDecodeError):
        return False

def set_error_state(status: bool):
    """Establece el estado de error del script."""
    with open(config.ERROR_STATE_FILE, 'w') as f:
        json.dump({"in_error_state": status}, f)
# --- FIN DE FUNCIONES DE ESTADO DE ERROR ---

def parse_date(date_str):
    if not date_str or date_str == '---': return None
    try:
        lima_tz = pytz.timezone('America/Lima')
        dt = datetime.strptime(date_str, '%d-%m-%Y %H:%M:%S')
        return lima_tz.localize(dt)
    except (ValueError, TypeError): return None

def generar_y_enviar_resumen(df_zim, titulo):
    # ... (Esta función no cambia)
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
    enviar_notificacion(titulo, mensaje_resumen.strip(), tags="newspaper")
    print("Resumen enviado.")

def revisar_cambios():
    print("Iniciando revisión de cambios...")
    try:
        # ... (La lógica interna de esta función no cambia)
        with open(config.DATA_FILE, 'r') as f: datos_viejos = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): datos_viejos = {}
        df = obtener_tabla_naves()
        if df is None: return
        df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
        print(f"Se encontraron {len(df_zim)} naves de ZIM activas.")
        if df_zim.empty:
            with open(config.DATA_FILE, 'w') as f: json.dump({}, f)
        else:
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
        
        # MODIFICADO: Lógica de recuperación
        if is_in_error_state():
            set_error_state(False)
            enviar_notificacion("✅ Sistema Recuperado", "El script ha vuelto a funcionar correctamente.", tags="white_check_mark")
            
    except Exception as e:
        print(f"Error al procesar la revisión de cambios: {e}")
        # MODIFICADO: Usa la nueva lógica de notificación de errores
        if not is_in_error_state():
            enviar_notificacion("‼️🚨 Error en Script de Naves", f"El script ha comenzado a fallar. Error: {e}", tags="x")
            set_error_state(True)

def enviar_resumen_diario():
    print("Generando resumen diario y alertas de plazos...")
    try:
        # ... (La lógica interna de esta función no cambia)
        df = obtener_tabla_naves()
        if df is None: return
        df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
        print(f"Se encontraron {len(df_zim)} naves para el resumen.")
        notificaciones_enviadas = cargar_notificaciones_enviadas()
        lima_hoy_str = get_lima_time().strftime('%Y-%m-%d')
        claves_a_borrar = [k for k, v in notificaciones_enviadas.items() if (datetime.strptime(lima_hoy_str, '%Y-%m-%d') - datetime.strptime(v, '%Y-%m-%d')).days > 30]
        for k in claves_a_borrar: del notificaciones_enviadas[k]
        if not df_zim.empty:
            lima_now = get_lima_time()
            for _, nave in df_zim.iterrows():
                nombre_nave = nave.get('VESSEL NAME', 'N/A')
                ib_vyg = pd.Series(nave.get('I/B VYG', '')).fillna('').iloc[0]
                identificador_nave = f"{nombre_nave} {ib_vyg}".strip()
                clave_viaje = f"{nombre_nave}-{ib_vyg}"
                etb_date = parse_date(pd.Series(nave.get('ETB', '---')).fillna('---').iloc[0])
                atd_date = parse_date(pd.Series(nave.get('ATD', '---')).fillna('---').iloc[0])
                dry_cutoff_str = pd.Series(nave.get('DRY CUTOFF', '---')).fillna('---').iloc[0]
                reefer_cutoff_str = pd.Series(nave.get('REEFER CUTOFF', '---')).fillna('---').iloc[0]
                service = pd.Series(nave.get('SERVICE', '---')).fillna('---').iloc[0]
                if etb_date:
                    diff_to_etb_hours = (etb_date - lima_now).total_seconds() / 3600
                    llave_myc = f"{clave_viaje}-MYC"
                    if 227.75 <= diff_to_etb_hours < 228 and llave_myc not in notificaciones_enviadas:
                        enviar_notificacion(f"⚠️📝 Recordatorio MYC: {identificador_nave}", f"Faltan 9.5 días para el ETB.\nEs momento de crear la nave en el sistema MYC.", tags="bell")
                        notificaciones_enviadas[llave_myc] = lima_hoy_str
                    llave_aduana = f"{clave_viaje}-ADUANA"
                    if 47.75 <= diff_to_etb_hours < 48 and llave_aduana not in notificaciones_enviadas:
                        if service == 'ZCX NB':
                            enviar_notificacion(f"⚠️📝 Alerta Aduanas (USA/Canadá): {identificador_nave}", "Faltan 48h para el ETB...", tags="customs")
                            notificaciones_enviadas[llave_aduana] = lima_hoy_str
                        elif service == 'ZAT':
                            enviar_notificacion(f"⚠️📝 Alerta Aduanas (China): {identificador_nave}", "Faltan 48h para el ETB...", tags="customs")
                            notificaciones_enviadas[llave_aduana] = lima_hoy_str
                cutoff_date = min(filter(None, [parse_date(dry_cutoff_str), parse_date(reefer_cutoff_str)])) if any([dry_cutoff_str != '---', reefer_cutoff_str != '---']) else None
                if cutoff_date:
                    diff_to_cutoff = (cutoff_date - lima_now).total_seconds() / 3600
                    llave_cutoff = f"{clave_viaje}-CUTOFF"
                    if 23.75 <= diff_to_cutoff < 24 and llave_cutoff not in notificaciones_enviadas:
                        enviar_notificacion(f"‼️🚨 Alerta de Cierre Documentario (24H): {identificador_nave}", "Faltan 24h para el Cut-Off...", tags="bangbang")
                        notificaciones_enviadas[llave_cutoff] = lima_hoy_str
                if atd_date:
                    diff_from_atd = (lima_now - atd_date).total_seconds() / 3600
                    llave_zarpe6h = f"{clave_viaje}-ZARPE6H"
                    llave_zarpe24h = f"{clave_viaje}-ZARPE24H"
                    if 6 <= diff_from_atd < 6.25 and llave_zarpe6h not in notificaciones_enviadas:
                        enviar_notificacion(f"⚠️📝 Recordatorio Post-Zarpe (6H): {identificador_nave}", "Han pasado 6h desde el zarpe real (ATD)...", tags="email")
                        notificaciones_enviadas[llave_zarpe6h] = lima_hoy_str
                    if 24 <= diff_from_atd < 24.25 and llave_zarpe24h not in notificaciones_enviadas:
                        enviar_notificacion(f"⚠️📝 Recordatorio Post-Zarpe (24H): {identificador_nave}", "Han pasado 24h desde el zarpe real (ATD)...", tags="page_facing_up")
                        notificaciones_enviadas[llave_zarpe24h] = lima_hoy_str
        
        if not df_zim.empty:
            generar_y_enviar_resumen(df_zim, "📰 resumen Diario de Naves ZIM")
        else:
            enviar_notificacion("📰 resumen Diario de Naves ZIM", "No hay naves de ZIM activas en la programación de hoy.", tags="newspaper")
        guardar_notificaciones_enviadas(notificaciones_enviadas)
        
        # MODIFICADO: Lógica de recuperación
        if is_in_error_state():
            set_error_state(False)
            enviar_notificacion("✅ Sistema Recuperado", "El script ha vuelto a funcionar correctamente.", tags="white_check_mark")

    except Exception as e:
        print(f"Error al enviar el resumen diario: {e}")
        # MODIFICADO: Usa la nueva lógica de notificación de errores
        if not is_in_error_state():
            enviar_notificacion("‼️🚨 Error en Resumen Diario", f"Falló con el error: {e}", tags="x")
            set_error_state(True)

# --- Bloque de ejecución principal (sin cambios) ---
if __name__ == "__main__":
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
