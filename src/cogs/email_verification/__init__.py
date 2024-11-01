from .cog import EmailVerification

async def setup(bot):
    await bot.add_cog(EmailVerification(bot))
