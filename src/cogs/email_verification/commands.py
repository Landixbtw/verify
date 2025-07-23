from typing import Optional 
import discord
from discord.ext import commands
import secrets
import asyncio
import logging
from datetime import datetime
from .config import Config
from .email_service import EmailService
from .utils import VerificationUtils

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
        self.pending_verifications = {}

    async def handle_unexpected_error(self, ctx, error):
        """Handle unexpected errors and log them"""
        error_id = secrets.token_hex(4)
        await VerificationUtils.log_to_channel(
            self.bot,
            VerificationUtils.create_log_embed(
                "Unexpected Error",
                f"Error ID: {error_id}",
                discord.Color.red(),
                [
                    ("User", f"{ctx.author} ({ctx.author.id})", True),
                    ("Error Type", type(error).__name__, True),
                    ("Error", str(error), False)
                ]
            )
        )
        await ctx.send(f"Ein unerwarteter Fehler ist aufgetreten. Error ID: {error_id}")
        logger.error(f"Unexpected error {error_id}: {str(error)}", exc_info=error)

    async def verify_email(self, ctx, email: Optional[str] = None):
        """Handle the verify command"""
        try:
            if not email:
                await VerificationUtils.log_to_channel(
                    self.bot,
                    VerificationUtils.create_log_embed(
                        "Verification Attempt - No Email",
                        "User tried to verify without providing email",
                        discord.Color.yellow(),
                        [("User", f"{ctx.author} ({ctx.author.id})", True)]
                    )
                )
                return await ctx.send(f"Bitte gebe deine @thu.de E-Mail-Adresse an.\n")

            # Check if user already has Verified role
            guild = ctx.bot.get_guild(Config.GUILD_ID)
            if guild:
                member = await guild.fetch_member(ctx.author.id)
                if member:
                    verified_role = discord.utils.get(guild.roles, name="Verified")
                    if verified_role and verified_role in member.roles:
                        await VerificationUtils.log_to_channel(
                            self.bot,
                            VerificationUtils.create_log_embed(
                                "Verification Attempt - Already Verified",
                                "User already has Verified role",
                                discord.Color.yellow(),
                                [
                                    ("User", f"{ctx.author} ({ctx.author.id})", True),
                                    ("Email", email, True)
                                ]
                            )
                        )
                        return await ctx.send("Du bist bereits verifiziert!")

            try:
                is_valid, message = VerificationUtils.is_valid_student_email(email)
                if not is_valid:
                    await VerificationUtils.log_to_channel(
                        self.bot,
                        VerificationUtils.create_log_embed(
                            "Verification Attempt - Invalid Email",
                            message,
                            discord.Color.red(),
                            [
                                ("User", f"{ctx.author} ({ctx.author.id})", True),
                                ("Email", email, True),
                                ("Reason", message, False)
                            ]
                        )
                    )
                    return await ctx.send("Ungültige E-Mail-Adresse. Bitte verwende deine THU-E-Mail-Adresse.")
            except Exception as e:
                logger.error(f"Failed to validate email: {e}")
                return await ctx.send("Es gab einen Fehler bei der E-Mail-Validierung.")

            await ctx.send("Sende Verifizierungscode... Dies kann einen Moment dauern.")
            verification_code = secrets.token_hex(3).upper()
            
            try:
                # Store pending verification in memory only
                self.pending_verifications[ctx.author.id] = {
                    'email': email,
                    'code': verification_code,
                    'attempts': 0,
                    'timestamp': datetime.utcnow()
                }
                
                EmailService.send_verification_email(email, verification_code, str(ctx.author))
                
                async def timeout_verification():
                    try:
                        await asyncio.sleep(Config.VERIFICATION_TIMEOUT)
                        if ctx.author.id in self.pending_verifications:
                            del self.pending_verifications[ctx.author.id]
                            await VerificationUtils.log_to_channel(
                                self.bot,
                                VerificationUtils.create_log_embed(
                                    "Verification Timeout",
                                    "Verification code expired",
                                    discord.Color.yellow(),
                                    [
                                        ("User", f"{ctx.author} ({ctx.author.id})", True),
                                        ("Email", email, True)
                                    ]
                                )
                            )
                    except Exception as e:
                        logger.error(f"Error in timeout task: {e}")
                
                asyncio.create_task(timeout_verification())
                
                await VerificationUtils.log_to_channel(
                    self.bot,
                    VerificationUtils.create_log_embed(
                        "Verification Code Sent",
                        "Verification email sent successfully",
                        discord.Color.blue(),
                        [
                            ("User", f"{ctx.author} ({ctx.author.id})", True),
                            ("Email", email, True)
                        ]
                    )
                )
                
                await ctx.send("✅ Verifizierungscode wurde gesendet!\n"
                             "Bitte überprüfe deine Universitäts-E-Mail für den Verifizierungscode.\n"
                             f"Benutze `{Config.PREFIX}confirm <code>` um die Verifizierung abzuschließen.\n"
                             "Der Code läuft in 5 Minuten ab.")
                
            except Exception as e:
                logger.error(f"Failed to send verification email: {e}")
                if ctx.author.id in self.pending_verifications:
                    try:
                        del self.pending_verifications[ctx.author.id]
                    except Exception as cleanup_error:
                        logger.error(f"Failed to clean up pending verification: {cleanup_error}")
                await ctx.send("Es gab einen Fehler beim Senden der Verifizierungs-E-Mail.")
                return

        except Exception as e:
            logger.error(f"Unexpected error in verify_email: {e}")
            await self.handle_unexpected_error(ctx, e)



    async def confirm_email(self, ctx, code: Optional[str] = None):
        """Handle the confirm command"""
        try:
            if code is None: # user gave no code 
                return await ctx.send(f"Bitte gib den Verifizierungscode an.\n"
                    f"Beispiel: `{Config.PREFIX}confirm 12345`")
            else:
                verification = self.pending_verifications.get(ctx.author.id)
                if not verification:
                    await VerificationUtils.log_to_channel(
                        self.bot,
                        VerificationUtils.create_log_embed(
                            "Confirmation Attempt - No Pending Verification",
                            "User tried to confirm without pending verification",
                            discord.Color.yellow(),
                            [("User", f"{ctx.author} ({ctx.author.id})", True)]
                        )
                    )
                    return await ctx.send(f"Keine ausstehende Verifizierung. Bitte benutze `{Config.PREFIX}verify <email>` zuerst.")

                # Check if verification has timed out
                time_elapsed = (datetime.utcnow() - verification['timestamp']).total_seconds()
                if time_elapsed > Config.VERIFICATION_TIMEOUT:
                    del self.pending_verifications[ctx.author.id]
                    return await ctx.send(f"Dein Verifizierungscode ist abgelaufen. Bitte benutze `{Config.PREFIX}verify <email>` um einen neuen Code anzufordern.")

                if verification['attempts'] >= 3:
                    await VerificationUtils.log_to_channel(
                        self.bot,
                        VerificationUtils.create_log_embed(
                            "Verification Failed - Max Attempts",
                            "User exceeded maximum verification attempts",
                            discord.Color.red(),
                            [
                                ("User", f"{ctx.author} ({ctx.author.id})", True),
                                ("Email", verification['email'], True)
                            ]
                        )
                    )
                    del self.pending_verifications[ctx.author.id]
                    return await ctx.send(f"Zu viele Versuche. Bitte starte erneut mit `{Config.PREFIX}verify <email>`")

                if code.upper() != verification['code']:
                    verification['attempts'] += 1
                    await VerificationUtils.log_to_channel(
                        self.bot,
                        VerificationUtils.create_log_embed(
                            "Invalid Verification Code",
                            f"Attempt {verification['attempts']}/3",
                            discord.Color.orange(),
                            [
                                ("User", f"{ctx.author} ({ctx.author.id})", True),
                                ("Email", verification['email'], True),
                                ("Provided Code", code.upper(), True),
                                ("Expected Code", verification['code'], True)
                            ]
                        )
                    )
                    return await ctx.send(f"Ungültiger Code. Noch {3 - verification['attempts']} Versuche übrig.")



            # Verification successful - just assign role
            try:
                guild = ctx.bot.get_guild(Config.GUILD_ID)
                if guild:
                    member = await guild.fetch_member(ctx.author.id)
                    if member:
                        verified_role = discord.utils.get(guild.roles, name="Verified")
                        if verified_role:
                            await member.add_roles(verified_role)
                            await VerificationUtils.log_to_channel(
                                self.bot,
                                VerificationUtils.create_log_embed(
                                    "Verification Successful",
                                    "User verified and role assigned",
                                    discord.Color.green(),
                                    [
                                        ("User", f"{ctx.author} ({ctx.author.id})", True),
                                        ("Email", verification['email'], True)
                                    ]
                                )
                            )
                        else:
                            await VerificationUtils.log_to_channel(
                                self.bot,
                                VerificationUtils.create_log_embed(
                                    "Role Assignment Failed",
                                    "Verified role not found",
                                    discord.Color.red(),
                                    [("User", f"{ctx.author} ({ctx.author.id})", True)]
                                )
                            )
            except Exception as e:
                await VerificationUtils.log_to_channel(
                    self.bot,
                    VerificationUtils.create_log_embed(
                        "Role Assignment Error",
                        str(e),
                        discord.Color.red(),
                        [
                            ("User", f"{ctx.author} ({ctx.author.id})", True),
                            ("Error", str(e), False)
                        ]
                    )
                )

            del self.pending_verifications[ctx.author.id]
            await ctx.send("E-Mail erfolgreich verifiziert! Dir wurde die Verified-Rolle zugewiesen.")

        except Exception as e:
            await self.handle_unexpected_error(ctx, e)

    async def remove_verify(self, ctx, member: discord.Member):
        """Handle the remove_verify command"""
        try:
            verified_role = discord.utils.get(ctx.guild.roles, name="Verified")
            if verified_role and verified_role in member.roles:
                await member.remove_roles(verified_role)
                
                await VerificationUtils.log_to_channel(
                    self.bot,
                    VerificationUtils.create_log_embed(
                        "Verification Removed",
                        "Admin removed user verification",
                        discord.Color.orange(),
                        [
                            ("User", f"{member} ({member.id})", True),
                            ("Admin", f"{ctx.author} ({ctx.author.id})", True)
                        ]
                    )
                )
                await ctx.send(f"Verifizierung von {member} wurde entfernt.")
            else:
                await ctx.send(f"{member} ist nicht verifiziert.")
        except Exception as e:
            await self.handle_unexpected_error(ctx, e)
