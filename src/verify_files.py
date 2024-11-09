import os
import logging

def test_verification_setup():
    # Check directory structure
    required_files = [
        'cogs/email_verification/__init__.py',
        'cogs/email_verification/cog.py',
        'cogs/email_verification/commands.py',
        'cogs/email_verification/config.py',
        'cogs/email_verification/email_service.py',
        'cogs/email_verification/verification_storage.py',
        'cogs/email_verification/utils.py',
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print("Missing files:")
        for file in missing_files:
            print(f"- {file}")
        return False

    # Check environment variables
    required_env = [
        'TOKEN',
        'SMTP_SERVER',
        'SMTP_PORT',
        'SENDER_EMAIL',
        'EMAIL_PASSWORD',
        'GUILD_ID',
        'LOG_CHANNEL_NAME',

        'DB_USER',
        'DB_PASSWORD',
        'DB_HOST',
        'DB_PORT',
        'DB_NAME',
    ]

    missing_env = []
    for env in required_env:
        if not os.getenv(env):
            missing_env.append(env)

    if missing_env:
        print("Missing environment variables:")
        for env in missing_env:
            print(f"- {env}")
        return False

    print("Verification setup check passed!")
    return True

if __name__ == "__main__":
    test_verification_setup()
