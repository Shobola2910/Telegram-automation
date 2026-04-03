"""
main.py — FastAPI server + ELD monitor background task

Serves dashboard at / and API at /api/
"""

import asyncio
import logging
import os
import sys

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

import database as db
from eld_client import create_eld_client
from telegram_bot import TelegramUserbot, TelebotManager
from monitor import run_monitor, SETTINGS, last_poll_time
from fmcsa import lookup_by_usdot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("eld_monitor.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# ── ELD account configs ────────────────────────────────────────────────────────
ELD_CONFIGS = []

if os.getenv("FACTOR_ELD_TOKEN"):
    ELD_CONFIGS.append({
        "id": "factor", "name": "Factor ELD", "type": "factor",
        "token": os.getenv("FACTOR_ELD_TOKEN"),
        "base_url": os.getenv("FACTOR_ELD_URL", "https://api.factorhq.com"),
        "enabled": True,
    })

if os.getenv("LEADER_ELD_TOKEN"):
    ELD_CONFIGS.append({
        "id": "leader", "name": "Leader ELD", "type": "leader",
        "token": os.getenv("LEADER_ELD_TOKEN"),
        "base_url": os.getenv("LEADER_ELD_URL", "https://api.leadereld.com"),
        "enabled": True,
    })

TG_CONFIGS = []
if os.getenv("TG_SESSION_STRING") or os.getenv("TG_PHONE"):
    TG_CONFIGS.append({
        "name": "Main Account",
        "api_id": int(os.getenv("TG_API_ID", "35507477")),
        "api_hash": os.getenv("TG_API_HASH", "201ab47b2a808cc66c3ef61529dba649"),
        "phone": os.getenv("TG_PHONE", ""),
        "session_string": os.getenv("TG_SESSION_STRING", ""),
    })

# Global state
eld_clients = []
tg_manager = TelebotManager()
monitor_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    # Initialize DB
    await db.init_db()
    logger.info("Database initialized")

    # Initialize ELD clients
    for cfg in ELD_CONFIGS:
        try:
            client = create_eld_client(cfg)
            eld_clients.append(client)
            logger.info(f"ELD client ready: {cfg['name']}")
        except Exception as e:
            logger.error(f"ELD client failed ({cfg['name']}): {e}")

    # Initialize Telegram
    for tg in TG_CONFIGS:
        session_str = tg.get("session_string", "")
        if not session_str:
            logger.warning(f"No session string for {tg['name']} — Telegram disabled")
            continue
        try:
            bot = TelegramUserbot(
                api_id=tg["api_id"],
                api_hash=tg["api_hash"],
                session_string=session_str,
                name=tg["name"],
            )
            await bot.start()
            tg_manager.add(bot)
        except Exception as e:
            logger.error(f"Telegram failed ({tg.get('name')}): {e}")

    # Start monitor loop
    if eld_clients:
        global monitor_task
        monitor_task = asyncio.create_task(run_monitor(eld_clients, tg_manager))
        logger.info("Monitor task started")
    else:
        logger.warning("No ELD clients — monitor not started. Add ELD tokens to env vars.")

    yield

    # Shutdown
    if monitor_task:
        monitor_task.cancel()
    await tg_manager.stop_all()
    for client in eld_clients:
        await client.close()
    logger.info("Shutdown complete")


app = FastAPI(lifespan=lifespan, title="ELD Monitor")


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with open("static/dashboard.html", encoding="utf-8") as f:
        return f.read()


# ── Stats ──────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats():
    stats = await db.get_stats()
    stats["last_poll"] = last_poll_time
    stats["eld_accounts"] = len(eld_clients)
    stats["tg_accounts"] = len(tg_manager.accounts)
    return stats


# ── Drivers ───────────────────────────────────────────────────────────────────

@app.get("/api/drivers")
async def get_drivers():
    return await db.get_drivers()


# ── Active alerts ──────────────────────────────────────────────────────────────

@app.get("/api/active-alerts")
async def get_active_alerts():
    return await db.get_all_active_alerts()


# ── History ────────────────────────────────────────────────────────────────────

@app.get("/api/history")
async def get_history(limit: int = 100):
    return await db.get_alert_history(limit)


# ── Companies ──────────────────────────────────────────────────────────────────

@app.get("/api/companies")
async def get_companies():
    return await db.get_companies()


class CompanyIn(BaseModel):
    usdot: str
    name: str
    mc_number: str = ""
    address: str = ""


@app.post("/api/companies")
async def add_company(body: CompanyIn):
    await db.upsert_company(body.usdot, body.name, body.mc_number, body.address)
    return {"ok": True}


@app.delete("/api/companies/{usdot}")
async def remove_company(usdot: str):
    await db.delete_company(usdot)
    return {"ok": True}


# ── FMCSA lookup ──────────────────────────────────────────────────────────────

@app.get("/api/fmcsa/{usdot}")
async def fmcsa_lookup(usdot: str):
    result = await lookup_by_usdot(usdot)
    if not result:
        raise HTTPException(404, "Carrier not found")
    return result


# ── Settings ───────────────────────────────────────────────────────────────────

@app.get("/api/settings")
async def get_settings():
    return SETTINGS


# ── ELD / Telegram accounts info ──────────────────────────────────────────────

@app.get("/api/eld-accounts")
async def get_eld_accounts():
    return [
        {
            "name": cfg["name"],
            "type": cfg["type"],
            "base_url": cfg.get("base_url", ""),
            "enabled": cfg.get("enabled", True),
        }
        for cfg in ELD_CONFIGS
    ]


@app.get("/api/tg-accounts")
async def get_tg_accounts():
    return [
        {
            "name": acc.name,
            "phone": TG_CONFIGS[i]["phone"] if i < len(TG_CONFIGS) else "—",
            "connected": True,
        }
        for i, acc in enumerate(tg_manager.accounts)
    ]


@app.get("/api/tg-groups")
async def get_tg_groups():
    return await tg_manager.get_all_groups()


# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
