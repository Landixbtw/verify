from discord.ext import commands
import discord
from typing import Optional
from .commands import VerificationCommands
from .config import Config

class EmailVerification(commands.Cog, name="Email Verification"):
    """Email verification commands"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.cmd_handler = VerificationCommands(bot)

    @commands.command(name="verify", brief="Verifiziere dich mit deiner @thu.de Email-Adresse")
    @commands.dm_only()
    async def verify_email(self, ctx, email: Optional[str] = None):
        """Start email verification process"""
        await self.cmd_handler.verify_email(ctx, email)

    @commands.command(name="confirm", brief="Bestätige Verifizierung mit Code aus Email")
    @commands.dm_only()
    async def confirm_email(self, ctx, code: Optional[str] = None):
        """Confirm your email with the verification code"""
        await self.cmd_handler.confirm_email(ctx, code)

    @commands.command(name="remove_verify")
    @commands.has_permissions(administrator=True)
    async def remove_verify(self, ctx, member: discord.Member):
        """Remove verification from a user (Admin only)"""
        await self.cmd_handler.remove_verify(ctx, member)

    @remove_verify.error
    async def remove_verify_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'member':
                await ctx.send("Bitte gib einen Benutzer an!\nBeispiel: `{Config.PREFIX}remove_verify @User`")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("Dieser Benutzer wurde nicht gefunden!")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("Du benötigst Administrator-Rechte um diesen Befehl auszuführen!")

    @commands.command(name="verify_debug")
    @commands.has_permissions(administrator=True)
    async def debug_verify(self, ctx):
        """Debug command to show verification system status"""
        embed = discord.Embed(
            title="Verification System Debug",
            color=discord.Color.blue()
        )
        
        # List available commands
        commands = [c.name for c in self.get_commands()]
        embed.add_field(
            name="Available Commands",
            value="\n".join(commands) or "No commands found",
            inline=False
        )
        
        # Show cog status
        embed.add_field(
            name="Cog Status",
            value=f"Loaded: {self.bot.get_cog('Email Verification') is not None}\n"
                  f"Command Count: {len(self.get_commands())}\n"
                  f"Bot Command Count: {len(self.bot.commands)}",
            inline=False
        )
        
        await ctx.send(embed=embed)
