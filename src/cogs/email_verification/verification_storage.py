import discord
import json
import aiofiles
import hashlib
import logging
from datetime import datetime
from .utils import VerificationUtils
from .config import Config

logger = logging.getLogger('email_verification')

class VerificationStorage:
    def __init__(self, bot):
        self.bot = bot
        self.verified_users_file = "verified_users.json"
        self.pending_verifications = {}

    async def load_verified_users(self) -> dict:
        try:
            async with aiofiles.open(self.verified_users_file, 'r') as f:
                content = await f.read()
                return json.loads(content) if content else {}
        except FileNotFoundError:
            return {}

    async def save_verified_user(self, user_id: int, email_hash: str) -> None:
        verified_users = await self.load_verified_users()
        verified_users[str(user_id)] = email_hash
        
        async with aiofiles.open(self.verified_users_file, 'w') as f:
            await f.write(json.dumps(verified_users))

    async def is_verified(self, user_id: int) -> bool:
        verified_users = await self.load_verified_users()
        return str(user_id) in verified_users

    async def is_email_used(self, email: str) -> tuple[bool, str]:
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        verified_users = await self.load_verified_users()
        
        for user_id, stored_hash in verified_users.items():
            if stored_hash == email_hash:
                return True, user_id
        return False, ""

    async def remove_verification_timeout(self, user_id: int, expired: bool = False):
        """Remove a pending verification and handle timeout notifications"""
        if user_id in self.pending_verifications:
            verification = self.pending_verifications[user_id]
            del self.pending_verifications[user_id]
            
            if expired:
                try:
                    user = await self.bot.fetch_user(user_id)
                    if user:
                        await user.send("Dein Verifizierungscode ist abgelaufen. Bitte benutze `>verify <email>` um einen neuen Code anzufordern.")
                        
                        # Create and send log embed
                        log_embed = VerificationUtils.create_log_embed(
                            "Verification Expired",
                            "Verification code expired after 5 minutes",
                            discord.Color.orange(),
                            [
                                ("User", f"{user} ({user.id})", True),
                                ("Email", verification['email'], True)
                            ]
                        )
                        await self.log_to_channel(log_embed)
                        
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

    def get_pending_verification(self, user_id: int) -> dict:
        """Get a pending verification if it exists"""
        return self.pending_verifications.get(user_id)

    def increment_verification_attempts(self, user_id: int) -> int:
        """Increment the number of verification attempts and return the new count"""
        if user_id in self.pending_verifications:
            self.pending_verifications[user_id]['attempts'] += 1
            return self.pending_verifications[user_id]['attempts']
        return 0

    async def check_verification_timeout(self, user_id: int) -> bool:
        """Check if a verification has timed out"""
        verification = self.get_pending_verification(user_id)
        if verification:
            time_elapsed = (datetime.now() - verification['created_at']).total_seconds()
            return time_elapsed > Config.VERIFICATION_TIMEOUT
        return True

