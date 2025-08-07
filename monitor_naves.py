import requests
import pandas as pd
import json
from io import StringIO
from datetime import datetime

# --- CONFIGURACIÓN ---
# La URL de la página de DP World Callao
URL = "https://naves.dpworldcallao.com.pe/programacion/"

# Tu tema de ntfy.sh. Ya está configurado.
NTFY_TOPIC = "cambios-naves-zim-9w3x5z"

# Archivo para guardar los datos y detectar cambios
DATA_FILE = "etb_data.json"

# --- FUNCIONES AUXILIARES ---

def cargar_datos_viejos():
    """Carga los datos de ETB guardados en la última ejecución."""
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Si el archivo no existe o está vacío, devuelve un diccionario vacío.
        return {}

def guardar_datos_nuevos(data):
    """Guarda los datos actuales para la próxima comparación."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def enviar_notificacion(titulo, mensaje):
    """Envía una notificación push a tu celular vía ntfy.sh."""
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mensaje.encode('utf-8'),
            headers={"Title": titulo.encode('utf-8')}
        )
        print(f"Notificación enviada: {titulo}")
    except Exception as e:
        print(f"Error al enviar notificación: {e}")

# --- LÓGICA PRINCIPAL (VERSIÓN CORREGIDA Y DEFINITIVA) ---

def main():
    print("Iniciando revisión de naves ZIM...")
    datos_viejos = cargar_datos_viejos()
    datos_nuevos = {}

    try:
        # Encabezado para simular un navegador y evitar el error 403
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Usamos requests para obtener el HTML con el encabezado
        response = requests.get(URL, headers=headers)
        response.raise_for_status()  # Esto verificará si hubo errores en la solicitud

        # MODIFICACIÓN FINAL: Apuntamos directamente a la tabla usando su ID correcto "tabla-naves".
        # Esto soluciona el error "No tables found".
        all_tables = pd.read_html(StringIO(response.text), attrs={'id': 'tabla-naves'})
        df = all_tables[0]

        # Filtramos para obtener solo las filas de la línea "ZIM"
        df_zim = df[df['LINE'].str.strip() == 'ZIM'].copy()
        print(f"Se encontraron {len(df_zim)} naves de ZIM.")

        if df_zim.empty:
            print("No se encontraron naves de ZIM en la tabla.")
            guardar_datos_nuevos({})
            return

        for index, nave in df_zim.iterrows():
            if 'VESSEL NAME' not in nave or 'I/B VYG' not in nave or 'ETB' not in nave:
                print(f"Advertencia: La fila {index} no tiene las columnas esperadas. Saltando.")
                continue

            nombre_nave = nave['VESSEL NAME']
            ib_vyg = nave['I/B VYG']
            etb_actual = nave['ETB']
            
            clave_viaje = f"{nombre_nave}-{ib_vyg}"
            
            datos_nuevos[clave_viaje] = etb_actual

            etb_viejo = datos_viejos.get(clave_viaje)

            if etb_viejo is None:
                titulo = f"🚢 Nueva Nave ZIM: {nombre_nave}"
                mensaje = f"Se añadió la nave {nombre_nave} ({ib_vyg}) con ETB: {etb_actual}."
                enviar_notificacion(titulo, mensaje)
            elif etb_viejo != etb_actual:
                titulo = f"⚠️ ALERTA: Cambio de ETB para {nombre_nave}"
                mensaje = f"Nave: {nombre_nave} ({ib_vyg})\nETB Anterior: {etb_viejo}\nETB Nuevo: {etb_actual}"
                enviar_notificacion(titulo, mensaje)

    except requests.exceptions.HTTPError as http_err:
        print(f"Error de HTTP: {http_err}")
        enviar_notificacion("‼️ Error en Script de Naves", f"El script falló con un error de HTTP: {http_err}")
        return
    except Exception as e:
        print(f"Error al procesar la página: {e}")
        enviar_notificacion("‼️ Error en Script de Naves", f"El script falló con el error: {e}")
        return

    guardar_datos_nuevos(datos_nuevos)
    print("Revisión completada.")

if __name__ == "__main__":
    main()