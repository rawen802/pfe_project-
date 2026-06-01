import smtplib
from email.message import EmailMessage


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

APP_EMAIL = "netautoai@gmail.com"
APP_EMAIL_PASSWORD = "sgxc qdkg ahls guce"


def send_app_email(receiver_email: str, subject: str, body: str) -> bool:
    try:
        msg = EmailMessage()
        msg["From"] = APP_EMAIL
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(APP_EMAIL, APP_EMAIL_PASSWORD)
            server.send_message(msg)

        print("Email envoyé vers :", receiver_email)
        return True

    except Exception as e:
        print("Erreur email:", e)
        return False