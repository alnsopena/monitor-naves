# main.py
import os
import json
import pandas as pd
from datetime import datetime
import config
from notifier import enviar_a_ntfy, enviar_a_correo
from scraper import obtener_tabla_naves, get_lima_time
from utils import is_in_error_state, set_error_state, cargar_notificaciones_enviadas, guardar_notificaciones_enviadas, parse_date

def generar_y_enviar_resumen(df_zim, titulo, cambios=None):
    """Construye y envía el mensaje de resumen, resaltando cambios si se proveen."""
    if cambios is None:
        cambios = {"nuevas": [], "modificadas": {}}

    lima_now = get_lima_time()
    mensaje_resumen = ""
    for _, nave in df_zim.iterrows():
        nombre_nave = nave.get('VESSEL NAME', 'N/A')
        ib_vyg = pd.Series(nave.get('I/B VYG', '')).fillna('').iloc[0]
        identificador_nave = f"{nombre_nave} {ib_vyg}".strip()
        clave_viaje = f"{nombre_nave}-{ib_vyg}"

        # Determinar el estado general de la nave
        etb_date = parse_date(pd.Series(nave.get('ETB', '---')).fillna('---').iloc[0])
        ata_date = parse_date(pd.Series(nave.get('ATA', '---')).fillna('---').iloc[0])
        atd_date = parse_date(pd.Series(nave.get('ATD', '---')).fillna('---').iloc[0])
        status_emoji = '🗓️'
        if atd_date and atd_date < lima_now: status_emoji = '➡️'
        elif ata_date and ata_date < lima_now: status_emoji = '⚓'
        elif etb_date and (etb_date - lima_now).total_seconds() <= 0: status_emoji = '⚓'
        elif etb_date and (etb_date - lima_now).total_seconds() / 3600 <= 24: status_emoji = '⏳'
        
        # Determinar si la nave es nueva para resaltarla
        nave_emoji = "✨" if clave_viaje in cambios.get("nuevas", []) else status_emoji
        
        # Construir las líneas de datos, resaltando los campos modificados
        lineas_datos = []
        campos_modificados = cambios.get("modificadas", {}).get(clave_viaje, [])
        
        for campo in ["Manifest", "ETB", "ETD"]:
            valor = pd.Series(nave.get(campo.upper(), '---')).fillna('---').iloc[0]
            prefijo = "✏️ " if campo.upper() in campos_modificados else "  "
            lineas_datos.append(f"{prefijo}{campo}: {valor}")
        
        datos_formateados = "\n".join(lineas_datos)
        mensaje_resumen += f"\n{nave_emoji} **{identificador_nave}**\n{datos_formateados}\n"

    enviar_a_ntfy(titulo, mensaje_resumen, tags="newspaper")
    enviar_a_correo(titulo, mensaje_resumen)
    print("Resumen enviado a todos los canales.")

def revisar_cambios():
    print("Iniciando revisión de cambios...")
    try:
        try:
            with open(config.DATA_FILE, 'r') as f:
                datos_viejos = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            datos_viejos = {}
        
        df = obtener_tabla_naves()
        if df is None: return
        df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()

        datos_nuevos = {}
        # MODIFICADO: Estructura para registrar cambios detallados
        cambios_info = {"nuevas": [], "modificadas": {}}

        for _, nave in df_zim.iterrows():
            clave_viaje = f"{nave['VESSEL NAME']}-{nave['I/B VYG']}"
            datos_nuevos[clave_viaje] = {campo: pd.Series(nave.get(campo, '---')).fillna('---').iloc[0] for campo in config.CAMPOS_A_MONITORIAR}
            
            if clave_viaje not in datos_viejos:
                cambios_info["nuevas"].append(clave_viaje)
            else:
                campos_modificados_nave = []
                for campo in config.CAMPOS_A_MONITORIAR:
                    if datos_nuevos[clave_viaje].get(campo) != datos_viejos[clave_viaje].get(campo):
                        campos_modificados_nave.append(campo)
                if campos_modificados_nave:
                    cambios_info["modificadas"][clave_viaje] = campos_modificados_nave

        if set(datos_viejos.keys()) != set(datos_nuevos.keys()):
             # Si las naves han sido añadidas o eliminadas, lo consideramos un cambio
            if not cambios_info["nuevas"] and not cambios_info["modificadas"]:
                 # Caso especial: solo se eliminaron naves
                 cambios_info["eliminadas"] = True


        with open(config.DATA_FILE, 'w') as f: json.dump(datos_nuevos, f, indent=4)

        if cambios_info.get("nuevas") or cambios_info.get("modificadas") or cambios_info.get("eliminadas"):
            print("Cambios detectados. Enviando resumen actualizado con resaltados...")
            generar_y_enviar_resumen(df_zim, "📰 resumen ZIM Actualizado por Cambios", cambios=cambios_info)
        else:
            print("Revisión completada. No se detectaron cambios.")
        
        if is_in_error_state():
            set_error_state(False)
            enviar_a_ntfy("✅ Sistema Recuperado", "El script ha vuelto a funcionar correctamente.", tags="white_check_mark")
            
    except Exception as e:
        print(f"Error al procesar la revisión de cambios: {e}")
        if not is_in_error_state():
            enviar_a_ntfy("‼️🚨 Error en Script de Naves", f"El script ha comenzado a fallar. Error: {e}", tags="x")
            set_error_state(True)

def enviar_resumen_diario():
    # (Esta función no cambia, pero se incluye completa para evitar errores)
    print("Generando resumen diario y alertas de plazos...")
    try:
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
                atd_date = parse_date(pd.Series(nave.get('ATD', '---')).fillna('---').iloc[0])
                dry_cutoff_str = pd.Series(nave.get('DRY CUTOFF', '---')).fillna('---').iloc[0]
                reefer_cutoff_str = pd.Series(nave.get('REEFER CUTOFF', '---')).fillna('---').iloc[0]
                service = pd.Series(nave.get('SERVICE', '---')).fillna('---').iloc[0]

                if etb_date:
                    diff_to_etb_hours = (etb_date - lima_now).total_seconds() / 3600
                    llave_myc = f"{clave_viaje}-MYC"
                    if 227.75 <= diff_to_etb_hours < 228 and llave_myc not in notificaciones_enviadas:
                        enviar_a_ntfy(f"⚠️📝 Recordatorio MYC: {identificador_nave}", f"Faltan 9.5 días para el ETB.\nEs momento de crear la nave en el sistema MYC.", tags="bell")
                        notificaciones_enviadas[llave_myc] = lima_hoy_str
                    llave_aduana = f"{clave_viaje}-ADUANA"
                    if 47.75 <= diff_to_etb_hours < 48 and llave_aduana not in notificaciones_enviadas:
                        if service == 'ZCX NB':
                            enviar_a_ntfy(f"⚠️📝 Alerta Aduanas (USA/Canadá): {identificador_nave}", "Faltan 48h para el ETB...", tags="customs")
                            notificaciones_enviadas[llave_aduana] = lima_hoy_str
                        elif service == 'ZAT':
                            enviar_a_ntfy(f"⚠️📝 Alerta Aduanas (China): {identificador_nave}", "Faltan 48h para el ETB...", tags="customs")
                            notificaciones_enviadas[llave_aduana] = lima_hoy_str
                
                cutoff_date = min(filter(None, [parse_date(dry_cutoff_str), parse_date(reefer_cutoff_str)])) if any([dry_cutoff_str != '---', reefer_cutoff_str != '---']) else None
                if cutoff_date:
                    diff_to_cutoff = (cutoff_date - lima_now).total_seconds() / 3600
                    llave_cutoff = f"{clave_viaje}-CUTOFF"
                    if 23.75 <= diff_to_cutoff < 24 and llave_cutoff not in notificaciones_enviadas:
                        enviar_a_ntfy(f"‼️🚨 Alerta de Cierre Documentario (24H): {identificador_nave}", "Faltan 24h para el Cut-Off...", tags="bangbang")
                        notificaciones_enviadas[llave_cutoff] = lima_hoy_str
                
                if atd_date:
                    diff_from_atd = (lima_now - atd_date).total_seconds() / 3600
                    llave_zarpe6h = f"{clave_viaje}-ZARPE6H"
                    llave_zarpe24h = f"{clave_viaje}-ZARPE24H"
                    if 6 <= diff_from_atd < 6.25 and llave_zarpe6h not in notificaciones_enviadas:
                        enviar_a_ntfy(f"⚠️📝 Recordatorio Post-Zarpe (6H): {identificador_nave}", "Han pasado 6h desde el zarpe real (ATD)...", tags="email")
                        notificaciones_enviadas[llave_zarpe6h] = lima_hoy_str
                    if 24 <= diff_from_atd < 24.25 and llave_zarpe24h not in notificaciones_enviadas:
                        enviar_a_ntfy(f"⚠️📝 Recordatorio Post-Zarpe (24H): {identificador_nave}", "Han pasado 24h desde el zarpe real (ATD)...", tags="page_facing_up")
                        notificaciones_enviadas[llave_zarpe24h] = lima_hoy_str
        
        if not df_zim.empty:
            # El resumen diario se envía SIN resaltados
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
            
    except Exception as e:
        print(f"Error al enviar el resumen diario: {e}")
        if not is_in_error_state():
            enviar_a_ntfy("‼️🚨 Error en Resumen Diario", f"Falló con el error: {e}", tags="x")
            set_error_state(True)

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
