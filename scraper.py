# scraper.py
import requests
import pandas as pd
import pytz
from datetime import datetime, timedelta
from io import StringIO
import config
from notifier import enviar_a_ntfy
from utils import is_in_error_state, set_error_state

def get_lima_time():
    """Obtiene la hora actual en la zona horaria de Lima, Perú."""
    return datetime.now(pytz.timezone('America/Lima'))

def obtener_tabla_naves():
    """Descarga, filtra por ATD y ETD, y devuelve la tabla de naves."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(config.URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        all_tables = pd.read_html(StringIO(response.text), attrs={'id': 'tabla-naves'})
        df = all_tables[0]
        lima_now = get_lima_time()
        print(f"Naves encontradas en la web: {len(df)}.")

        df['ATD_datetime'] = pd.to_datetime(df['ATD'], format='%d-%m-%Y %H:%M:%S', errors='coerce')
        df['ATD_datetime'] = df['ATD_datetime'].apply(lambda x: x.tz_localize('America/Lima', ambiguous='NaT') if pd.notnull(x) else x)
        df_filtrado = df[df['ATD_datetime'].isnull() | (df['ATD_datetime'] > lima_now)].copy()
        print(f"Naves después de filtro ATD (zarpe): {len(df_filtrado)}.")

        cutoff_date = lima_now.date() + timedelta(days=config.ETD_FILTER_DAYS)
        df_filtrado['ETD_date'] = pd.to_datetime(df_filtrado['ETD'], format='%d-%m-%Y %H:%M:%S', errors='coerce').dt.date
        
        df_final = df_filtrado[
            (df_filtrado['ETD_date'].isnull()) | 
            (df_filtrado['ETD_date'] <= cutoff_date)
        ].copy()
        print(f"Naves después de filtro ETD ({config.ETD_FILTER_DAYS} días): {len(df_final)}.")

        df_final.drop(columns=['ATD_datetime', 'ETD_date'], inplace=True, errors='ignore')
        return df_final

    except Exception as e:
        print(f"Error al obtener la tabla de la web: {e}")
        if not is_in_error_state():
            enviar_a_ntfy("‼️🚨 Error en Script de Naves", f"El script ha comenzado a fallar al obtener datos de DP World. Error: {e}", tags="x")
            set_error_state(True)
        return None
