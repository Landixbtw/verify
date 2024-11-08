import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from help import setup as help_setup

if not os.path.exists("./Logs"):
    os.makedirs("./Logs")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("./Logs/bot.log", encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('bot')

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=">",
            intents=discord.Intents.all(),
            help_command=None
        )
        self.logger = logger

    async def setup_hook(self):
        self.logger.info("Loading cogs...")
        
        # Load email verification cog first
        try:
            await self.load_extension("cogs.email_verification")
            self.logger.info(f"Loaded email verification cog with commands: {[cmd.name for cmd in self.commands]}")
        except Exception as e:
            self.logger.error(f"Failed to load email verification cog: {e}", exc_info=True)

        # Load other cogs
        for file in os.listdir("./cogs"):
            if file.endswith(".py") and not file.startswith("__"):
                try:
                    name = file[:-3]
                    if name != "verify":  # Skip if it's not the email verification cog
                        await self.load_extension(f"cogs.{name}")
                        self.logger.info(f"Loaded cog: {name}")
                except Exception as e:
                    self.logger.error(f"Failed to load cog {file}: {e}", exc_info=True)

    async def on_ready(self):
        self.logger.info(f"{self.user.name} is ready")
        try:
            synced = await self.tree.sync()
            self.logger.info(f"Synced {len(synced)} commands")
        except Exception as e:
            self.logger.error(f"Failed to sync commands: {e}", exc_info=True)

        # Log all available commands
        self.logger.info("Available commands:")
        for cmd in self.commands:
            self.logger.info(f"- {cmd.name}: {cmd.help}")

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{self.command_prefix}help"
            )
        )

def main():
    # Load environment variables
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f".env file exists: {os.path.exists('.env')}")
    load_dotenv(verbose=True)
    
    # Get token
    token = str(os.getenv("TOKEN"))
    if not token or not token.strip():
        raise ValueError("No valid token found in environment variables")

    try:
        # Initialize and run bot
        bot = Bot()
        help_setup(bot)
        bot.run(token)
    except discord.errors.LoginFailure as e:
        logger.error(f"Failed to login: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main()
