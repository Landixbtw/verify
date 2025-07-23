from discord.ext import commands
import discord
from cogs.email_verification.config import Config

class CustomHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title="📚 THU Discord Bot Hilfe",
            description="Hier sind alle verfügbaren Befehle:",
            color=discord.Color.blue()
        )

        for cog, commands in mapping.items():
            # Filter to get only visible commands
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                # Get cog name, if no cog use "Andere Befehle"
                cog_name = getattr(cog, "qualified_name", "Andere Befehle")
                # Add field for each category
                command_list = "\n".join(f"`{Config.PREFIX}{c.name}` - {c.brief}" for c in filtered)
                if command_list:
                    embed.add_field(
                        name=f"📌 {cog_name}",
                        value=command_list,
                        inline=False
                    )

        embed.set_footer(text=f"Nutze {Config.PREFIX}help <Befehl> für detaillierte Informationen zu einem Befehl.")
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=f"Hilfe: {command.name}",
            description=command.help or "Keine detaillierte Beschreibung verfügbar.",
            color=discord.Color.blue()
        )
        
        if command.aliases:
            embed.add_field(
                name="Aliase",
                value=", ".join(command.aliases),
                inline=False
            )
            
        embed.add_field(
            name="Verwendung",
            value=f"`{Config.PREFIX}{command.name} {command.signature}`",
            inline=False
        )
        
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=f"{cog.qualified_name} Befehle",
            description=cog.description or "Keine Beschreibung verfügbar.",
            color=discord.Color.blue()
        )
        
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(
                name=f"{Config.PREFIX}{command.name}",
                value=command.brief or "Keine kurze Beschreibung verfügbar.",
                inline=False
            )
            
        channel = self.get_destination()
        await channel.send(embed=embed)

    # This is called when a help command fails
    async def send_error_message(self, error):
        embed = discord.Embed(
            title="Fehler",
            description=error,
            color=discord.Color.red()
        )
        channel = self.get_destination()
        await channel.send(embed=embed)

# To use this custom help command, add this to your bot setup:
async def setup(bot):
    bot.help_command = CustomHelpCommand()
