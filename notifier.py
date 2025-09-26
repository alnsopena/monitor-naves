# notifier.py
import requests
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

def enviar_a_ntfy(titulo, mensaje, tags=""):
    """Envía una notificación específicamente a ntfy.sh."""
    if not config.NTFY_TOPIC:
        print("Advertencia: NTFY_TOPIC no configurado.")
        return
    try:
        requests.post(
            f"https://ntfy.sh/{config.NTFY_TOPIC}",
            data=mensaje.encode('utf-8'),
            headers={"Title": titulo.encode('utf-8'), "Tags": tags}
        )
        print(f"Notificación enviada a ntfy.")
    except Exception as e:
        print(f"ERROR al enviar por ntfy: {e}")

def enviar_a_correo(titulo, mensaje):
    """Envía una notificación específicamente por correo electrónico."""
    if not config.EMAIL_ADDRESS or not config.EMAIL_APP_PASSWORD:
        print("Advertencia: Credenciales de correo no configuradas.")
        return
    try:
        email_msg = MIMEMultipart()
        email_msg["From"] = f"Monitor de Naves <{config.EMAIL_ADDRESS}>"
        email_msg["To"] = config.EMAIL_ADDRESS
        email_msg["Subject"] = titulo
        
        mensaje_simple = mensaje.replace('**', '').replace('➡️', '->').replace('⚓', '(En Puerto)').replace('⏳', '(Próximo)').replace('🗓️', '(Programado)')
        
        cuerpo_html = f'<html><body><pre style="font-family: monospace; font-size: 14px;">{mensaje_simple}</pre></body></html>'
        email_msg.attach(MIMEText(cuerpo_html, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT, context=context) as server:
            server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
            server.sendmail(config.EMAIL_ADDRESS, config.EMAIL_ADDRESS, email_msg.as_string())
            print(f"Notificación enviada por correo a {config.EMAIL_ADDRESS}")
    except Exception as e:
        print(f"ERROR al enviar por correo: {e}")
