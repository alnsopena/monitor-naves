# scraper.py
# Módulo responsable de descargar y procesar los datos de la web.

import requests
import pandas as pd
import pytz
from datetime import datetime
from io import StringIO
import config
from notifier import enviar_notificacion

def get_lima_time():
    """Obtiene la hora actual en la zona horaria de Lima, Perú."""
    return datetime.now(pytz.timezone('America/Lima'))

def obtener_tabla_naves():
    """Descarga, filtra por ATD y devuelve la tabla de naves como un DataFrame."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(config.URL, headers=headers, timeout=15)
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
        enviar_notificacion("‼️🚨 Error en Script de Naves", f"No se pudo descargar la tabla de DP World. Error: {e}", tags="x")
        return None
