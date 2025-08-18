# notifier.py
# Módulo responsable de enviar notificaciones.

import requests
import config

def enviar_notificacion(titulo, mensaje, tags="shipping_container"):
    """Envía una notificación push a tu celular vía ntfy.sh."""
    try:
        requests.post(
            f"https://ntfy.sh/{config.NTFY_TOPIC}",
            data=mensaje.encode('utf-8'),
            headers={
                "Title": titulo.encode('utf-8'),
                "Tags": tags
            }
        )
        print(f"Notificación enviada: {titulo}")
    except Exception as e:
        print(f"Error al enviar notificación: {e}")
