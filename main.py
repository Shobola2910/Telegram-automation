"""
ELD Monitor — Main Application
FastAPI + Telethon + APScheduler
"""
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from config import get_settings
from database import init_db, AsyncSessionLocal, EldSource
from services import telegram_client as tg
from services.monitor import run_monitor_cycle
from routers.api import drivers_router, eld_router, tg_router, monitor_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()
scheduler = AsyncIOScheduler()


async def seed_default_eld_source():
    """Seed Factor ELD as default source if not exists"""
    if not settings.eld_bearer_token:
        return
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(EldSource).where(EldSource.name == "factor"))
        if existing.scalar_one_or_none():
            return
        src = EldSource(
            name="factor",
            display_name="Factor ELD",
            base_url=settings.eld_base_url,
            bearer_token=settings.eld_bearer_token,
            tenant_id=settings.eld_tenant_id,
            is_active=True,
        )
        db.add(src)
        await db.commit()
        logger.info("✅ Factor ELD source seeded from .env")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 ELD Monitor starting...")

    # 1. Init DB
    await init_db()
    logger.info("✅ Database ready")

    # 2. Seed default ELD source
    await seed_default_eld_source()

    # 3. Init Telegram
    try:
        await tg.init_telegram(
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
            session_string=settings.telegram_session_string,
        )
        authorized = await tg.is_authorized()
        if authorized:
            logger.info("✅ Telegram authorized")
        else:
            logger.warning("⚠️  Telegram NOT authorized — use /api/telegram/auth/send-code")
    except Exception as e:
        logger.error(f"Telegram init error: {e}")

    # 4. Start scheduler
    scheduler.add_job(
        run_monitor_cycle,
        "interval",
        seconds=settings.poll_interval_seconds,
        id="eld_monitor",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info(f"⏱  Scheduler running (every {settings.poll_interval_seconds}s)")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    await tg.disconnect()
    logger.info("👋 ELD Monitor stopped")


app = FastAPI(
    title="ELD Monitor",
    description="Algo Group — Real-time ELD monitoring & Telegram alerts",
    version="2.0.0",
    lifespan=lifespan,
)

# API routes
app.include_router(drivers_router)
app.include_router(eld_router)
app.include_router(tg_router)
app.include_router(monitor_router)

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse("frontend/index.html")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "telegram": await tg.is_authorized(),
        "scheduler": scheduler.running,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=True)
