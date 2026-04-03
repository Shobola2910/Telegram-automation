"""
generate_session.py
───────────────────
Run this ONCE on your local computer to generate a Telegram session string.
Then copy the output string into Railway environment variable: TG_SESSION_STRING

Usage:
    pip install telethon
    python generate_session.py
"""

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID   = 35507477
API_HASH = "201ab47b2a808cc66c3ef61529dba649"
PHONE    = "+998775013234"


async def main():
    print("=" * 55)
    print("  Telegram Session Generator")
    print("=" * 55)
    print(f"  Phone: {PHONE}")
    print("  A verification code will be sent to your Telegram app.")
    print("=" * 55)

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start(phone=PHONE)

    session_string = client.session.save()
    me = await client.get_me()

    print("\n✅ Logged in as:", me.first_name, f"(@{me.username})")
    print("\n" + "=" * 55)
    print("  YOUR SESSION STRING (copy everything between the lines):")
    print("=" * 55)
    print(session_string)
    print("=" * 55)
    print("\n→ Paste this as TG_SESSION_STRING in Railway environment variables.")
    print("→ Keep it secret — it gives full access to your Telegram account.\n")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
