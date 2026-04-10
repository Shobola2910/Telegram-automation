"""
get_session.py — Bir martalik script.
Telegram ga local login qilib session string olish uchun.
Keyin bu stringni Render.com → Environment Variables → TELEGRAM_SESSION_STRING ga qo'ying.

Ishlatish:
    python get_session.py
"""
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID   = 35507477
API_HASH = "201ab47b2a808cc66c3ef61529dba649"
PHONE    = "+998775013234"

async def main():
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start(phone=PHONE)
    session = client.session.save()
    print("\n" + "="*60)
    print("✅ Session string (Render ga qo'ying):")
    print("="*60)
    print(session)
    print("="*60 + "\n")
    print("Render.com → eld-monitor → Environment → TELEGRAM_SESSION_STRING")
    await client.disconnect()

asyncio.run(main())
