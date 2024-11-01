# Enhanced Error handling and Stats

import discord
from discord.ext import commands
import secrets
import asyncio
import logging
from datetime import datetime
from .config import Config
from .email_service import EmailService
from .utils import VerificationUtils
from .verification_storage import VerificationStorage
from .stats import VerificationStats

class VerificationError(Exception):
    """Base class for verification errors"""
    pass

class EmailInUseError(VerificationError):
    pass

class InvalidEmailError(VerificationError):
    pass

class VerificationTimeoutError(VerificationError):
    pass

class VerificationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.storage = VerificationStorage(bot)
        self.stats = VerificationStats()
        self.log_channel = None
        self._setup_error_handlers()

    def _setup_error_handlers(self):
        """Set up error handlers for various verification scenarios"""
        @self.verify_email.error
        async def verify_email_error(ctx, error):
            if isinstance(error, commands.PrivateMessageOnly):
                await ctx.send("Dieser Befehl kann nur in Direktnachrichten verwendet werden.")
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Bitte gib eine E-Mail-Adresse an.")
            else:
                await self.handle_unexpected_error(ctx, error)

        @self.confirm_email.error
        async def confirm_email_error(ctx, error):
            if isinstance(error, commands.PrivateMessageOnly):
                await ctx.send("Dieser Befehl kann nur in Direktnachrichten verwendet werden.")
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Bitte gib den Verifizierungscode an.")
            else:
                await self.handle_unexpected_error(ctx, error)

    async def handle_unexpected_error(self, ctx, error):
        """Handle unexpected errors and log them"""
        error_id = secrets.token_hex(4)
        await self.log_to_channel(VerificationUtils.create_log_embed(
            "Unexpected Error",
            f"Error ID: {error_id}",
            discord.Color.red(),
            [
                ("User", f"{ctx.author} ({ctx.author.id})", True),
                ("Command", ctx.command.name, True),
                ("Error", str(error), False)
            ]
        ))
        await ctx.send(f"Ein unerwarteter Fehler ist aufgetreten. Error ID: {error_id}")
        logger.error(f"Unexpected error {error_id}: {str(error)}", exc_info=error)

    @commands.dm_only()
    @commands.command(name="verify")
    async def verify_email(self, ctx, email: str):
        """Enhanced verify command with error handling and stats tracking"""
        try:
            # Track verification attempt
            await self.stats.log_verification_attempt(email)

            # Check if user is already verified
            if await self.storage.is_verified(ctx.author.id):
                await self.stats.log_verification_failure('already_verified')
                raise VerificationError("Du bist bereits verifiziert!")

            # Validate email format
            is_valid, message = VerificationUtils.is_valid_student_email(email)
            if not is_valid:
                await self.stats.log_verification_failure('invalid_email')
                raise InvalidEmailError(message)

            # Check if email is already in use
            is_used, existing_user = await self.storage.is_email_used(email)
            if is_used:
                await self.stats.log_verification_failure('email_in_use')
                raise EmailInUseError("Diese E-Mail-Adresse wurde bereits verwendet.")

            # Generate and send verification code
            try:
                verification_code = secrets.token_hex(3).upper()
                await EmailService.send_verification_email(email, verification_code, str(ctx.author))
            except Exception as e:
                await self.stats.log_verification_failure('email_error')
                logger.error(f"Failed to send verification email: {e}")
                raise VerificationError("Fehler beim Senden der Verifizierungs-E-Mail.")

            # Add pending verification
            self.storage.add_pending_verification(ctx.author.id, email, verification_code)

            # Set up timeout
            asyncio.create_task(self._handle_verification_timeout(ctx.author.id))

            await ctx.send("✅ Verifizierungscode wurde gesendet!\n"
                         "Bitte überprüfe deine Universitäts-E-Mail für den Verifizierungscode.\n"
                         "Benutze `>confirm <code>` um die Verifizierung abzuschließen.\n"
                         "Der Code läuft in 5 Minuten ab.")

        except VerificationError as e:
            await ctx.send(str(e))
        except Exception as e:
            await self.handle_unexpected_error(ctx, e)

    @commands.command(name="stats")
    @commands.has_permissions(administrator=True)
    async def show_stats(self, ctx, days: int = 7):
        """Command to show verification statistics"""
        try:
            stats = await self.stats.get_stats_report(days)
            
            embed = discord.Embed(
                title=f"Verification Statistics (Last {days} days)",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Add general stats
            embed.add_field(
                name="General Stats",
                value=f"Total Attempts: {stats['total_attempts']}\n"
                      f"Successful: {stats['successful_verifications']}\n"
                      f"Failed: {stats['failed_verifications']}\n"
                      f"Success Rate: {stats['success_rate']:.1f}%",
                inline=False
            )
            
            # Add failure breakdown
            embed.add_field(
                name="Failure Breakdown",
                value=f"Expired: {stats['expired_verifications']}\n"
                      f"Invalid Emails: {stats['invalid_emails']}\n"
                      f"Already Verified: {stats['already_verified_attempts']}\n"
                      f"Email Errors: {stats['email_send_errors']}\n"
                      f"Invalid Codes: {stats['invalid_codes']}",
                inline=False
            )
            
            # Add domain stats
            domain_stats = "\n".join(f"{domain}: {count}" 
                                   for domain, count in stats['domains'].items())
            embed.add_field(
                name="Domain Statistics",
                value=domain_stats or "No domain data",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self.handle_unexpected_error(ctx, e)

    async def _handle_verification_timeout(self, user_id: int):
        """Handle verification timeout with stats tracking"""
        await asyncio.sleep(Config.VERIFICATION_TIMEOUT)
        verification = self.storage.get_pending_verification(user_id)
        if verification:
            await self.stats.log_verification_failure('expired')
            await self.storage.remove_verification_timeout(user_id, expired=True)
