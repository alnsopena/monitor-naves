# main.py
import os
import json
import pandas as pd
from datetime import datetime
import config
from notifier import enviar_a_ntfy, enviar_a_correo
from scraper import obtener_tabla_naves, get_lima_time
from utils import (is_in_error_state, set_error_state, 
                   cargar_notificaciones_enviadas, guardar_notificaciones_enviadas, 
                   parse_date, cargar_rate_limit_state, guardar_rate_limit_state)

def generar_mensaje_resumen(df_zim, cambios=None):
    if cambios is None:
        cambios = {"nuevas": [], "modificadas": {}}
    lima_now = get_lima_time()
    mensaje_resumen = ""
    for _, nave in df_zim.iterrows():
        nombre_nave = nave.get('VESSEL NAME', 'N/A')
        ib_vyg = pd.Series(nave.get('I/B VYG', '')).fillna('').iloc[0]
        identificador_nave = f"{nombre_nave} {ib_vyg}".strip()
        clave_viaje = f"{nombre_nave}-{ib_vyg}"
        etb_date = parse_date(pd.Series(nave.get('ETB', '---')).fillna('---').iloc[0])
        ata_date = parse_date(pd.Series(nave.get('ATA', '---')).fillna('---').iloc[0])
        atd_date = parse_date(pd.Series(nave.get('ATD', '---')).fillna('---').iloc[0])
        status_emoji = '🗓️'
        if atd_date and atd_date < lima_now: status_emoji = '➡️'
        elif ata_date and ata_date < lima_now: status_emoji = '⚓'
        elif etb_date and (etb_date - lima_now).total_seconds() <= 0: status_emoji = '⚓'
        elif etb_date and (etb_date - lima_now).total_seconds() / 3600 <= 24: status_emoji = '⏳'
        nave_emoji = "✨" if clave_viaje in cambios.get("nuevas", []) else status_emoji
        lineas_datos = []
        campos_modificados = cambios.get("modificadas", {}).get(clave_viaje, [])
        for campo in ["Manifest", "ETB", "ETD"]:
            valor = pd.Series(nave.get(campo.upper(), '---')).fillna('---').iloc[0]
            prefijo = "✏️ " if campo.upper() in campos_modificados else "  "
            lineas_datos.append(f"{prefijo}{campo}: {valor}")
        datos_formateados = "\n".join(lineas_datos)
        mensaje_resumen += f"\n{nave_emoji} **{identificador_nave}**\n{datos_formateados}\n"
    return mensaje_resumen.strip()

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
        cambios_info = {"nuevas": [], "modificadas": {}}
        for _, nave in df_zim.iterrows():
            clave_viaje = f"{nave['VESSEL NAME']}-{nave['I/B VYG']}"
            datos_nuevos[clave_viaje] = {campo: pd.Series(nave.get(campo, '---')).fillna('---').iloc[0] for campo in config.CAMPOS_A_MONITORIAR}
            if clave_viaje not in datos_viejos:
                cambios_info["nuevas"].append(clave_viaje)
            else:
                campos_modificados_nave = [campo for campo in config.CAMPOS_A_MONITORIAR if datos_nuevos[clave_viaje].get(campo) != datos_viejos[clave_viaje].get(campo)]
                if campos_modificados_nave:
                    cambios_info["modificadas"][clave_viaje] = campos_modificados_nave
        
        hubo_cambios = bool(cambios_info["nuevas"] or cambios_info["modificadas"])

        if hubo_cambios:
            print("Cambios detectados. Verificando reglas de notificación...")
            lima_now = get_lima_time()
            titulo = "📰 resumen ZIM Actualizado por Cambios"
            mensaje_resumen = generar_mensaje_resumen(df_zim, cambios_info)
            enviar_a_ntfy(titulo, mensaje_resumen, tags="newspaper")

            rate_limit_state = cargar_rate_limit_state()
            today_str = lima_now.strftime('%Y-%m-%d')
            if rate_limit_state.get("today_date") != today_str:
                rate_limit_state = {"change_emails_sent_today": 0, "last_change_email_timestamp": None, "today_date": today_str}
            
            if rate_limit_state["change_emails_sent_today"] >= 6:
                print("Límite de 6 correos por cambio alcanzado. Correo omitido.")
            else:
                can_send = True
                if rate_limit_state["last_change_email_timestamp"]:
                    last_sent_time = datetime.fromisoformat(rate_limit_state["last_change_email_timestamp"])
                    hours_since_last = (lima_now - last_sent_time).total_seconds() / 3600
                    if hours_since_last < 1:
                        print(f"Menos de 1 hora desde el último correo ({hours_since_last:.2f}h). Correo omitido.")
                        can_send = False
                if can_send:
                    enviar_a_correo(titulo, mensaje_resumen)
                    # --- MODIFICACIÓN CLAVE ---
                    # La memoria de datos SÓLO se actualiza si el correo fue enviado.
                    with open(config.DATA_FILE, 'w') as f:
                        json.dump(datos_nuevos, f, indent=4)
                    print("Memoria de datos actualizada.")
                    
                    rate_limit_state["change_emails_sent_today"] += 1
                    rate_limit_state["last_change_email_timestamp"] = lima_now.isoformat()
            
            guardar_rate_limit_state(rate_limit_state)
        else:
            print("Revisión completada. No se detectaron cambios.")
            # Si no hubo cambios, nos aseguramos de que la memoria esté sincronizada.
            with open(config.DATA_FILE, 'w') as f:
                json.dump(datos_nuevos, f, indent=4)
        
        if is_in_error_state():
            set_error_state(False)
            enviar_a_ntfy("✅ Sistema Recuperado", "El script ha vuelto a funcionar correctamente.", tags="white_check_mark")
            
    except Exception as e:
        print(f"Error al procesar la revisión de cambios: {e}")
        if not is_in_error_state():
            enviar_a_ntfy("‼️🚨 Error en Script de Naves", f"El script ha comenzado a fallar. Error: {e}", tags="x")
            set_error_state(True)

def enviar_resumen_diario():
    # Esta función no cambia
    print("Generando resumen diario y alertas de plazos...")
    # ... (código se mantiene igual)

# El resto del archivo main.py se mantiene igual
