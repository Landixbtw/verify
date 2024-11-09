import discord
import mariadb
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from .utils import VerificationUtils
from .config import Config
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger('email_verification')

class VerificationStorage:
    def __init__(self, bot):
        self.bot = bot
        self.pending_verifications = {}

        # Load database credentials
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = int(os.getenv("DB_PORT"))
        db_name = os.getenv("DB_NAME")

        # MariaDB connection setup
        try:
            self.conn = mariadb.connect(
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port,
                database=db_name
            )
            self.cursor = self.conn.cursor()
            logger.info("Connected to MariaDB database.")
        except mariadb.Error as e:
            logger.error(f"Error connecting to MariaDB: {e}")
            raise e

    def __del__(self):
        """Cleanup database connections"""
        try:
            if hasattr(self, 'cursor'):
                self.cursor.close()
            if hasattr(self, 'conn'):
                self.conn.close()
            logger.info("Closed database connections.")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

    async def load_verified_users(self) -> dict:
        """Load verified users from the database"""
        verified_users = {}
        try:
            self.cursor.execute("SELECT user_id, email_hash FROM verified_users")
            for user_id, email_hash in self.cursor.fetchall():
                verified_users[str(user_id)] = email_hash
        except mariadb.Error as e:
            logger.error(f"Error loading verified users: {e}")
        return verified_users

    async def save_verified_user(self, user_id: int, email_hash: str) -> None:
        """Save a verified user to the database"""
        try:
            self.cursor.execute(
                "REPLACE INTO verified_users (user_id, email_hash) VALUES (?, ?)",
                (user_id, email_hash)
            )
            self.conn.commit()
        except mariadb.Error as e:
            logger.error(f"Error saving verified user: {e}")

    async def is_verified(self, user_id: int) -> bool:
        """Check if a user is verified in the database"""
        try:
            self.cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM verified_users WHERE user_id=?)",
                (user_id,)
            )
            return self.cursor.fetchone()[0] == 1
        except mariadb.Error as e:
            logger.error(f"Error checking verification status: {e}")
            return False

    async def is_email_used(self, email: str) -> tuple[bool, str]:
        """Check if an email is already used in the database"""
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        try:
            self.cursor.execute(
                "SELECT user_id FROM verified_users WHERE email_hash=?",
                (email_hash,)
            )
            result = self.cursor.fetchone()
            if result:
                return True, str(result[0])
        except mariadb.Error as e:
            logger.error(f"Error checking if email is used: {e}")
        return False, ""

    async def remove_verification_timeout(self, user_id: int, expired: bool = False) -> None:
        """Remove a pending verification and handle timeout notifications"""
        if user_id in self.pending_verifications:
            verification = self.pending_verifications.pop(user_id)
            
            if expired:
                try:
                    user = await self.bot.fetch_user(user_id)
                    if user:
                        await user.send(f"Dein Verifizierungscode ist abgelaufen. Bitte benutze `{Config.PREFIX}verify <email>` um einen neuen Code anzufordern.")
                        
                        log_embed = VerificationUtils.create_log_embed(
                            "Verification Expired",
                            "Verification code expired after 5 minutes",
                            discord.Color.orange(),
                            [
                                ("User", f"{user} ({user.id})", True),
                                ("Email", verification['email'], True)
                            ]
                        )
                        await VerificationUtils.log_to_channel(self.bot, log_embed)
                except Exception as e:
                    logger.error(f"Failed to notify user of expired verification: {e}")

    def add_pending_verification(self, user_id: int, email: str, code: str) -> None:
        """Add a new pending verification"""
        self.pending_verifications[user_id] = {
            'email': email,
            'code': code,
            'attempts': 0,
            'created_at': datetime.now()
        }

    def get_pending_verification(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a pending verification if it exists"""
        return self.pending_verifications.get(user_id)

    async def check_verification_timeout(self, user_id: int) -> bool:
        """Check if a verification has timed out"""
        verification = self.get_pending_verification(user_id)
        if verification:
            time_elapsed = (datetime.now() - verification['created_at']).total_seconds()
            return time_elapsed > Config.VERIFICATION_TIMEOUT
        return True
