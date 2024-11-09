
import discord
from datetime import datetime 
import re 
import logging
from .config import Config

logger = logging.getLogger('email_verification')

class VerificationUtils:
    _log_channel = None

    @staticmethod
    async def get_log_channel(bot) -> discord.TextChannel:
        """Get or retrieve the logging channel"""
        if VerificationUtils._log_channel is None:
            for guild in bot.guilds:
                channel = discord.utils.get(guild.channels, name=Config.LOG_CHANNEL_NAME)
                if channel:
                    VerificationUtils._log_channel = channel
                    break
        return VerificationUtils._log_channel

    @staticmethod
    async def log_to_channel(bot, embed: discord.Embed) -> None:
        """Send a log message to the designated channel"""
        channel = await VerificationUtils.get_log_channel(bot)
        if channel is None:
            logger.error(f"Could not find channel named {Config.LOG_CHANNEL_NAME}")
            return
        try:
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send log message: {e}")

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

