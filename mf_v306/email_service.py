from __future__ import annotations
import os, smtplib
from email.message import EmailMessage

def send_email(to_email, subject, html_body, attachment=None, attachment_name='report.html'):
    host=os.getenv('SMTP_HOST',''); port=int(os.getenv('SMTP_PORT','587')); user=os.getenv('SMTP_USER',''); password=os.getenv('SMTP_PASSWORD',''); sender=os.getenv('SMTP_FROM',user)
    if not host or not sender: raise RuntimeError('SMTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD and SMTP_FROM.')
    msg=EmailMessage(); msg['From']=sender; msg['To']=to_email; msg['Subject']=subject; msg.set_content('MechForge AI report attached.'); msg.add_alternative(html_body,subtype='html')
    if attachment:
        msg.add_attachment(attachment, maintype='application', subtype='octet-stream', filename=attachment_name)
    with smtplib.SMTP(host,port,timeout=20) as server:
        server.starttls()
        if user: server.login(user,password)
        server.send_message(msg)
