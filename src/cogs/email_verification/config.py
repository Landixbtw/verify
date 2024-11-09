import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PREFIX = ">"
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SENDER_EMAIL = os.getenv('SENDER_EMAIL')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    LOG_CHANNEL_NAME = os.getenv('LOG_CHANNEL_NAME', 'bot-logs')
    ALLOWED_DOMAIN = "@thu.de"
    STUDENT_PATTERN = r'^[a-z]+\d{2}@thu\.de$'
    PROF_PATTERN = r'^[a-zA-Z]+\.[a-zA-Z]+@thu\.de$'
    VERIFICATION_TIMEOUT = 300
    GUILD_ID = os.getenv('GUILD_ID')
 
