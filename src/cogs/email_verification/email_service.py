import smtplib
from email.mime.text import MIMEText
from .config import Config

class EmailService:
    @staticmethod
    def send_verification_email(email: str, code: str, username: str) -> None:
        msg = MIMEText(
            "(english below)"
            f"Hallo {username},\n\n"
            f"Dein Verifizierungscode lautet: {code}\n\n"
            f"Bitte gib diesen Code mit dem Befehl {Config.PREFIX}confirm <code> ein.\n"
            "Der Code läuft in 5 Minuten ab.\n\n"
            "Mit freundlichen Grüßen,\nDein Verifikations-Bot"
            "\n"
            "\n"
            "\n"
            f"Hello {username},\n\n"
            f"Your Verifikation Code is {code}\n\n"
            f"Please enter your code with the command {Config.PREFIX}confirm <code>.\n"
            "This code expires in 5minutes.\n\n"
            "Kind regards, your verification bot"

        )
        
        msg['Subject'] = 'Discord Verifikationscode'
        msg['From'] = Config.SENDER_EMAIL
        msg['To'] = email
        
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SENDER_EMAIL, Config.EMAIL_PASSWORD)
            server.send_message(msg)
