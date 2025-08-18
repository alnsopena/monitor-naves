import requests
import pandas as pd
import json
import os
from io import StringIO
from datetime import datetime
import pytz

# --- CONFIGURACIÓN ---
URL = "https://naves.dpworldcallao.com.pe/programacion/"
NTFY_TOPIC = "cambios-naves-zim-9w3x5z"
DATA_FILE = "etb_data.json"
ETB_CHANGE_THRESHOLD_HOURS = 2
CAMPOS_A_MONITOREAR = ["ETB", "MANIFEST", "ATA", "ETD", "ATD"]

# --- FUNCIONES AUXILIARES ---

def cargar_datos_viejos():
    """Carga los datos guardados en la última ejecución."""
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_datos_nuevos(data):
    """Guarda los datos actuales para la próxima comparación."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def enviar_notificacion(titulo, mensaje, tags="shipping_container"):
    """Envía una notificación push a tu celular vía ntfy.sh."""
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mensaje.encode('utf-8'),
            headers={
                "Title": titulo.encode('utf-8'),
                "Tags": tags
            }
        )
        print(f"Notificación enviada: {titulo}")
    except Exception as e:
        print(f"Error al enviar notificación: {e}")

def get_lima_time():
    """Obtiene la hora actual en la zona horaria de Lima, Perú."""
    lima_tz = pytz.timezone('America/Lima')
    return datetime.now(lima_tz)

# --- LÓGICA PRINCIPAL ---

def revisar_cambios():
    """Compara los datos actuales con los viejos y notifica si hay cambios."""
    print("Iniciando revisión de cambios en naves ZIM...")
    datos_viejos = cargar_datos_viejos()
    datos_nuevos = {}
    
    try:
        df = obtener_tabla_naves()
        if df is None: return

        df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
        print(f"Se encontraron {len(df_zim)} naves de ZIM activas.")

        if df_zim.empty:
            guardar_datos_nuevos({})
            # Se elimina la notificación de "todas las naves removidas"
            return

        for index, nave in df_zim.iterrows():
            nombre_nave = nave['VESSEL NAME']
            ib_vyg = nave['I/B VYG']
            clave_viaje = f"{nombre_nave}-{ib_vyg}"
            
            datos_nuevos[clave_viaje] = {campo: pd.Series(nave.get(campo, '---')).fillna('---').iloc[0] for campo in CAMPOS_A_MONITOREAR}
            
            if clave_viaje not in datos_viejos:
                titulo = f"🚢 Nueva Nave ZIM: {nombre_nave}"
                mensaje = f"Se añadió la nave {nombre_nave} ({ib_vyg}) a la programación."
                enviar_notificacion(titulo, mensaje, tags="heavy_plus_sign")
            else:
                for campo in CAMPOS_A_MONITOREAR:
                    valor_nuevo = datos_nuevos[clave_viaje].get(campo, '---')
                    valor_viejo = datos_viejos[clave_viaje].get(campo, '---')
                    
                    if valor_nuevo != valor_viejo:
                        mensaje_base = f"Campo '{campo}' ha cambiado.\nAnterior: {valor_viejo}\nNuevo: {valor_nuevo}"
                        titulo = f"⚠️ Alerta de Cambio: {nombre_nave}"

                        if campo == "ETB":
                            try:
                                formato_fecha = '%d-%m-%Y %H:%M:%S'
                                fecha_vieja = datetime.strptime(valor_viejo, formato_fecha)
                                fecha_nueva = datetime.strptime(valor_nuevo, formato_fecha)
                                diferencia_horas = abs((fecha_nueva - fecha_vieja).total_seconds() / 3600)
                                
                                if diferencia_horas > ETB_CHANGE_THRESHOLD_HOURS:
                                    titulo = f"‼️ ALERTA MAYOR: {nombre_nave}"
                                    mensaje = f"Cambio significativo de {diferencia_horas:.1f} horas en ETB.\nAnterior: {valor_viejo}\nNuevo: {valor_nuevo}"
                                    enviar_notificacion(titulo, mensaje, tags="rotating_light")
                                else:
                                    print(f"Cambio menor de ETB para {nombre_nave} ignorado ({diferencia_horas:.1f} horas).")
                            except ValueError:
                                enviar_notificacion(titulo, mensaje_base, tags="warning")
                        else:
                            enviar_notificacion(titulo, mensaje_base, tags="warning")

        # --- SECCIÓN ELIMINADA ---
        # Ya no se comprueba si una nave desapareció de la lista.
        
        guardar_datos_nuevos(datos_nuevos)
        print("Revisión de cambios completada.")

    except Exception as e:
        print(f"Error al procesar la revisión de cambios: {e}")
        enviar_notificacion("‼️ Error en Script de Naves", f"El script falló con el error: {e}", tags="x")

def enviar_resumen_diario():
    print("Generando resumen diario y alertas de 8 días...")
    try:
        df = obtener_tabla_naves()
        if df is None: return

        df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
        print(f"Se encontraron {len(df_zim)} naves para el resumen.")

        if df_zim.empty:
            enviar_notificacion("Resumen Diario de Naves", "No hay naves de ZIM activas en la programación de hoy.", tags="date")
            return

        lima_hoy = get_lima_time().date()
        formato_fecha = '%d-%m-%Y %H:%M:%S'
        mensaje_resumen = ""

        for index, nave in df_zim.iterrows():
            nombre_nave = nave.get('VESSEL NAME', 'N/A')
            etb_str = pd.Series(nave.get('ETB', '---')).fillna('---').iloc[0]
            etd_str = pd.Series(nave.get('ETD', '---')).fillna('---').iloc[0]
            
            try:
                if etb_str != '---':
                    etb_date = datetime.strptime(etb_str, formato_fecha).date()
                    diferencia_dias = (etb_date - lima_hoy).days
                    
                    if diferencia_dias == 8:
                        titulo_alerta = f"🔔 Recordatorio MYC: {nombre_nave}"
                        mensaje_alerta = f"Faltan exactamente 8 días para el ETB de la nave {nombre_nave}.\nEs momento de crearla en el sistema MYC."
                        enviar_notificacion(titulo_alerta, mensaje_alerta, tags="bell")
            except ValueError:
                print(f"No se pudo procesar la fecha ETB '{etb_str}' para la nave {nombre_nave}.")
            
            mensaje_resumen += f"\n- {nombre_nave}:\n  ETB: {etb_str}\n  ETD: {etd_str}\n"

        titulo_resumen = "Resumen Diario de Naves ZIM"
        enviar_notificacion(titulo_resumen, mensaje_resumen.strip(), tags="newspaper")
        print("Resumen diario enviado.")
    except Exception as e:
        print(f"Error al enviar el resumen diario: {e}")
        enviar_notificacion("‼️ Error en Resumen Diario", f"Falló con el error: {e}", tags="x")

def obtener_tabla_naves():
    """Descarga, filtra por ATD y devuelve la tabla de naves como un DataFrame."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        all_tables = pd.read_html(StringIO(response.text), attrs={'id': 'tabla-naves'})
        df = all_tables[0]

        print("Filtrando naves que ya han zarpado...")
        lima_time_now = get_lima_time()
        
        df['ATD_datetime'] = pd.to_datetime(df['ATD'], format='%d-%m-%Y %H:%M:%S', errors='coerce')
        df['ATD_datetime'] = df['ATD_datetime'].apply(lambda x: x.tz_localize('America/Lima', ambiguous='NaT') if pd.notnull(x) else x)

        df_filtrado = df[df['ATD_datetime'].isnull() | (df['ATD_datetime'] > lima_time_now)].copy()
        
        df_filtrado.drop(columns=['ATD_datetime'], inplace=True)
        print(f"Naves en total: {len(df)}. Naves activas (sin ATD pasado): {len(df_filtrado)}.")
        return df_filtrado
    except Exception as e:
        print(f"Error al obtener la tabla de la web: {e}")
        enviar_notificacion("‼️ Error en Script de Naves", f"No se pudo descargar la tabla de DP World. Error: {e}", tags="x")
        return None

if __name__ == "__main__":
    job_type = os.getenv('JOB_TYPE', 'REGULAR_CHECK')
    if job_type == 'DAILY_SUMMARY':
        enviar_resumen_diario()
    else:
        revisar_cambios()
