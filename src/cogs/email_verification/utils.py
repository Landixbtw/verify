import discord
from datetime import datetime 
import re 
from .config import Config

class VerificationUtils:
    @staticmethod
    def create_log_embed(title: str, description: str, color: discord.Color, fields: list) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        return embed

    @staticmethod
    def is_valid_student_email(email: str) -> tuple[bool, str]:
        if not email.endswith(Config.ALLOWED_DOMAIN):
            return False, "Email must be a THU email address"

        if re.match(Config.STUDENT_PATTERN, email):
            return True, "Valid email"

        if re.match(Config.PROF_PATTERN, email):
            return False, "Valid staff email"

        return False, "E-Mail-Format ungültig"
