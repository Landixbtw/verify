from typing import Optional 
import discord
from discord.ext import commands
import secrets
import asyncio
import logging
import hashlib
from datetime import datetime
from .config import Config
from .email_service import EmailService
from .utils import VerificationUtils
from .verification_storage import VerificationStorage
from .stats import VerificationStats

logger = logging.getLogger('email_verification')

class VerificationError(Exception):
    """Base class for verification errors"""
    pass

class EmailInUseError(VerificationError):
    pass

class InvalidEmailError(VerificationError):
    pass

class VerificationTimeoutError(VerificationError):
    pass

class VerificationCommands:
    def __init__(self, bot):
        self.bot = bot
        self.storage = VerificationStorage(bot)
        self.stats = VerificationStats()
        self.log_channel = None

    async def get_log_channel(self):
        """Get or retrieve the logging channel"""
        if self.log_channel is None:
            for guild in self.bot.guilds:
                channel = discord.utils.get(guild.channels, name=Config.LOG_CHANNEL_NAME)
                if channel:
                    self.log_channel = channel
                    break
        return self.log_channel

    async def log_to_channel(self, embed: discord.Embed):
        """Send a log message to the designated channel"""
        channel = await self.get_log_channel()
        if channel is None:
            logger.error(f"Could not find channel named {Config.LOG_CHANNEL_NAME}")
            return

        try:
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send log message: {e}")

    async def handle_unexpected_error(self, ctx, error):
        """Handle unexpected errors and log them"""
        error_id = secrets.token_hex(4)
        await self.log_to_channel(VerificationUtils.create_log_embed(
            "Unexpected Error",
            f"Error ID: {error_id}",
            discord.Color.red(),
            [
                ("User", f"{ctx.author} ({ctx.author.id})", True),
                ("Error Type", type(error).__name__, True),
                ("Error", str(error), False)
            ]
        ))
        await ctx.send(f"Ein unerwarteter Fehler ist aufgetreten. Error ID: {error_id}")
        logger.error(f"Unexpected error {error_id}: {str(error)}", exc_info=error)

    async def verify_email(self, ctx, email: Optional[str] = None):
        """Handle the verify command"""
        try:
            if not email:
                await self.log_to_channel(VerificationUtils.create_log_embed(
                    "Verification Attempt - No Email",
                    "User tried to verify without providing email",
                    discord.Color.yellow(),
                    [("User", f"{ctx.author} ({ctx.author.id})", True)]
                ))
                return await ctx.send("Bitte gib deine E-Mail-Adresse an.\n"
                                    "Beispiel: `>verify foobar@thu.de`")

            # Track verification attempt
            await self.stats.log_verification_attempt(email)

            # Check if user is already verified
            if await self.storage.is_verified(ctx.author.id):
                await self.stats.log_verification_failure('already_verified')
                await self.log_to_channel(VerificationUtils.create_log_embed(
                    "Verification Attempt - Already Verified",
                    "User tried to verify again",
                    discord.Color.yellow(),
                    [
                        ("User", f"{ctx.author} ({ctx.author.id})", True),
                        ("Email", email, True)
                    ]
                ))
                return await ctx.send("Du bist bereits verifiziert!")

            # Validate email format
            is_valid, message = VerificationUtils.is_valid_student_email(email)
            if not is_valid:
                await self.stats.log_verification_failure('invalid_email')
                await self.log_to_channel(VerificationUtils.create_log_embed(
                    "Verification Attempt - Invalid Email",
                    message,
                    discord.Color.red(),
                    [
                        ("User", f"{ctx.author} ({ctx.author.id})", True),
                        ("Email", email, True),
                        ("Reason", message, False)
                    ]
                ))
                return await ctx.send("Ungültige E-Mail-Adresse. Bitte verwende deine THU-E-Mail-Adresse.")

            await ctx.send("Sende Verifizierungscode... Dies kann einen Moment dauern.")
            verification_code = secrets.token_hex(3).upper()
            
            try:

                # Add pending verification before sending email
                self.storage.add_pending_verification(ctx.author.id, email, verification_code)
                
                # Send verification email
                EmailService.send_verification_email(email, verification_code, str(ctx.author))
                
                # Create timeout task
                async def timeout_verification():
                    await asyncio.sleep(Config.VERIFICATION_TIMEOUT)
                    await self.storage.remove_verification_timeout(ctx.author.id, expired=True)
                
                asyncio.create_task(timeout_verification())
                
                await self.log_to_channel(VerificationUtils.create_log_embed(
                    "Verification Code Sent",
                    "Verification email sent successfully",
                    discord.Color.blue(),
                    [
                        ("User", f"{ctx.author} ({ctx.author.id})", True),
                        ("Email", email, True)
                    ]
                ))
                
                await ctx.send("✅ Verifizierungscode wurde gesendet!\n"
                             "Bitte überprüfe deine Universitäts-E-Mail für den Verifizierungscode.\n"
                             "Benutze `>confirm <code>` um die Verifizierung abzuschließen.\n"
                             "Der Code läuft in 5 Minuten ab.")
                
            except Exception as e:
                await self.stats.log_verification_failure('email_error')
                logger.error(f"Failed to send verification email: {e}")
                if ctx.author.id in self.storage.pending_verifications:
                    del self.storage.pending_verifications[ctx.author.id]
                await ctx.send("Es gab einen Fehler beim Senden der Verifizierungs-E-Mail.")
                raise

        except Exception as e:
            await self.handle_unexpected_error(ctx, e)

    async def confirm_email(self, ctx, code: str):
        """Handle the confirm command"""
        try:
            verification = self.storage.get_pending_verification(ctx.author.id)
            if not verification:
                await self.log_to_channel(VerificationUtils.create_log_embed(
                    "Confirmation Attempt - No Pending Verification",
                    "User tried to confirm without pending verification",
                    discord.Color.yellow(),
                    [("User", f"{ctx.author} ({ctx.author.id})", True)]
                ))
                return await ctx.send("Keine ausstehende Verifizierung. Bitte benutze `>verify <deine.universitaets.email>` zuerst.")

            # Check for timeout
            if await self.storage.check_verification_timeout(ctx.author.id):
                await self.storage.remove_verification_timeout(ctx.author.id, expired=True)
                return await ctx.send("Dein Verifizierungscode ist abgelaufen. Bitte benutze `>verify <email>` um einen neuen Code anzufordern.")

            # Check attempts
            if verification['attempts'] >= 3:
                await self.log_to_channel(VerificationUtils.create_log_embed(
                    "Verification Failed - Max Attempts",
                    "User exceeded maximum verification attempts",
                    discord.Color.red(),
                    [
                        ("User", f"{ctx.author} ({ctx.author.id})", True),
                        ("Email", verification['email'], True)
                    ]
                ))
                del self.storage.pending_verifications[ctx.author.id]
                return await ctx.send("Zu viele Versuche. Bitte starte erneut mit `>verify <email>`")

            # Validate code
            if code.upper() != verification['code']:
                verification['attempts'] += 1
                await self.log_to_channel(VerificationUtils.create_log_embed(
                    "Invalid Verification Code",
                    f"Attempt {verification['attempts']}/3",
                    discord.Color.orange(),
                    [
                        ("User", f"{ctx.author} ({ctx.author.id})", True),
                        ("Email", verification['email'], True),
                        ("Provided Code", code.upper(), True),
                        ("Expected Code", verification['code'], True)
                    ]
                ))
                return await ctx.send(f"Ungültiger Code. Noch {3 - verification['attempts']} Versuche übrig.")

            # Save verified user
            email_hash = hashlib.sha256(verification['email'].encode()).hexdigest()
            await self.storage.save_verified_user(ctx.author.id, email_hash)

            # Assign role
            try:
                guild = ctx.bot.get_guild(int(Config.GUILD_ID))
                if guild:
                    member = await guild.fetch_member(ctx.author.id)
                    if member:
                        verified_role = discord.utils.get(guild.roles, name="Verified")
                        if verified_role:
                            await member.add_roles(verified_role)
                            await self.log_to_channel(VerificationUtils.create_log_embed(
                                "Verification Successful",
                                "User verified and role assigned",
                                discord.Color.green(),
                                [
                                    ("User", f"{ctx.author} ({ctx.author.id})", True),
                                    ("Email", verification['email'], True)
                                ]
                            ))
                        else:
                            await self.log_to_channel(VerificationUtils.create_log_embed(
                                "Role Assignment Failed",
                                "Verified role not found",
                                discord.Color.red(),
                                [("User", f"{ctx.author} ({ctx.author.id})", True)]
                            ))
            except Exception as e:
                await self.log_to_channel(VerificationUtils.create_log_embed(
                    "Role Assignment Error",
                    str(e),
                    discord.Color.red(),
                    [
                        ("User", f"{ctx.author} ({ctx.author.id})", True),
                        ("Error", str(e), False)
                    ]
                ))

            del self.storage.pending_verifications[ctx.author.id]
            await self.stats.log_verification_success()
            await ctx.send("E-Mail erfolgreich verifiziert! Dir wurde die Verified-Rolle zugewiesen.")

        except Exception as e:
            await self.handle_unexpected_error(ctx, e)

    async def remove_verify(self, ctx, member: discord.Member):
        """Handle the remove_verify command"""
        try:
            verified_users = await self.storage.load_verified_users()
            if str(member.id) in verified_users:
                # set the user email hash to 0 but keep member id 
                await self.storage.save_verified_user(member.id, None)  # Pass member.id since method expects int
                
                verified_role = discord.utils.get(ctx.guild.roles, name="Verified")
                if verified_role and verified_role in member.roles:
                    await member.remove_roles(verified_role)
                
                await self.log_to_channel(VerificationUtils.create_log_embed(
                    "Verification Removed",
                    "Admin removed user verification",
                    discord.Color.orange(),
                    [
                        ("User", f"{member} ({member.id})", True),
                        ("Admin", f"{ctx.author} ({ctx.author.id})", True)
                    ]
                ))
                await ctx.send(f"Verifizierung von {member} wurde entfernt.")
            else:
                await ctx.send(f"{member} ist nicht verifiziert.")
        except Exception as e:
            await self.handle_unexpected_error(ctx, e)

    async def show_stats(self, ctx, days: int = 7):
        """Handle the stats command"""
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
