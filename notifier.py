# notifier.py
# Módulo responsable de enviar notificaciones por AMBOS canales: ntfy y correo.

import requests
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

def _enviar_por_ntfy(titulo, mensaje, tags=""):
    """Función interna para enviar notificación vía ntfy.sh."""
    if not config.NTFY_TOPIC:
        print("Advertencia: NTFY_TOPIC no está configurado. Saltando envío a ntfy.")
        return
    
    requests.post(
        f"https://ntfy.sh/{config.NTFY_TOPIC}",
        data=mensaje.encode('utf-8'),
        headers={
            "Title": titulo.encode('utf-8'),
            "Tags": tags
        }
    )
    print(f"Notificación enviada a ntfy (Tópico: {config.NTFY_TOPIC})")

def _enviar_por_correo(titulo, mensaje):
    """Función interna para enviar notificación vía correo electrónico."""
    if not config.EMAIL_ADDRESS or not config.EMAIL_APP_PASSWORD:
        print("Advertencia: Credenciales de correo no configuradas. Saltando envío de correo.")
        return

    email_msg = MIMEMultipart()
    email_msg["From"] = config.EMAIL_ADDRESS
    email_msg["To"] = config.EMAIL_ADDRESS
    email_msg["Subject"] = titulo
    
    mensaje_simple = mensaje.replace('**', '').replace('➡️', '->').replace('⚓', '(En Puerto)').replace('⏳', '(Próximo)').replace('🗓️', '(Programado)')
    
    cuerpo_html = f"""
    <html>
    <body>
        <p><b>{titulo}</b></p>
        <pre style="font-family: monospace; font-size: 14px;">{mensaje_simple}</pre>
    </body>
    </html>
    """
    email_msg.attach(MIMEText(cuerpo_html, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT, context=context) as server:
        server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
        server.sendmail(config.EMAIL_ADDRESS, config.EMAIL_ADDRESS, email_msg.as_string())
        print(f"Notificación enviada por correo a {config.EMAIL_ADDRESS}")

def enviar_notificacion(titulo, mensaje, tags=""):
    """
    Función principal que envía una notificación a TODOS los canales configurados.
    """
    # Envío a ntfy
    try:
        _enviar_por_ntfy(titulo, mensaje, tags)
    except Exception as e:
        print(f"ERROR al enviar por ntfy: {e}")

    # Envío a Correo
    try:
        _enviar_por_correo(titulo, mensaje)
    except Exception as e:
        print(f"ERROR al enviar por correo: {e}")
