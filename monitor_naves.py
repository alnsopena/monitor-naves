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
            if datos_viejos:
                enviar_notificacion("Todas las naves ZIM han sido removidas", "Ya no hay naves ZIM activas en la programación.", tags="wastebasket")
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

        naves_desaparecidas = set(datos_viejos.keys()) - set(datos_nuevos.keys())
        for clave_viaje in naves_desaparecidas:
            nombre_nave_desaparecida = clave_viaje.split('-')[0]
            titulo = f"🗑️ Nave Removida: {nombre_nave_desaparecida}"
            mensaje = f"La nave {nombre_
