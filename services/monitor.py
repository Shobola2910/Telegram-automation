"""
Monitor Engine — polls ELD APIs, checks thresholds, sends Telegram alerts.
Runs on a configurable interval via APScheduler.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, Driver, AlertLog, EldSource
from services.eld_client import EldClientFactory, HosData
from services import telegram_client as tg
from services import alert_messages as msgs

logger = logging.getLogger(__name__)

# ─── Thresholds ───────────────────────────────────────────────────────────────
CYCLE_WARN_HOURS    = 20.0
DRIVE_WARN_HOURS    = 2.0
SHIFT_WARN_HOURS    = 2.0
BREAK_WARN_HOURS    = 2.0
# How long before re-alerting same condition (minutes)
ALERT_COOLDOWN_MIN  = 90


# ─── Alert deduplication ──────────────────────────────────────────────────────

async def _should_send(db: AsyncSession, driver_id: str, alert_type: str,
                        cooldown_min: int = ALERT_COOLDOWN_MIN) -> bool:
    """Returns True if enough time has passed since the last same alert"""
    cutoff = datetime.utcnow() - timedelta(minutes=cooldown_min)
    result = await db.execute(
        select(AlertLog).where(
            and_(
                AlertLog.driver_id == driver_id,
                AlertLog.alert_type == alert_type,
                AlertLog.sent_at >= cutoff,
            )
        ).limit(1)
    )
    return result.scalar_one_or_none() is None


async def _log_alert(db: AsyncSession, driver_id: str, alert_type: str,
                      message: str, chat_id: Optional[str], eld_source: str,
                      extra: Optional[dict] = None):
    log = AlertLog(
        driver_id=driver_id,
        alert_type=alert_type,
        alert_key=f"{driver_id}:{alert_type}",
        message_sent=message,
        telegram_chat_id=chat_id,
        eld_source=eld_source,
        extra_data=json.dumps(extra) if extra else None,
    )
    db.add(log)
    await db.commit()


# ─── Per-driver check ─────────────────────────────────────────────────────────

async def check_driver(hos: HosData, db: AsyncSession):
    """Evaluate one driver's HOS and send alerts as needed"""

    # Find the driver record (for telegram group mapping)
    result = await db.execute(
        select(Driver).where(
            and_(Driver.eld_driver_id == hos.driver_id,
                 Driver.eld_source == hos.eld_source)
        )
    )
    driver_record = result.scalar_one_or_none()
    chat_id = driver_record.telegram_chat_id if driver_record else None

    async def alert(alert_type: str, message: str, extra: Optional[dict] = None):
        if not await _should_send(db, hos.driver_id, alert_type):
            logger.debug(f"Skipping {alert_type} for {hos.driver_name} — cooldown")
            return
        if chat_id:
            success = await tg.send_message(chat_id, message)
            if success:
                await _log_alert(db, hos.driver_id, alert_type, message,
                                  chat_id, hos.eld_source, extra)
                logger.info(f"✅ Alert [{alert_type}] → {hos.driver_name} → {chat_id}")
        else:
            logger.warning(f"⚠️ No Telegram group for {hos.driver_name} ({hos.driver_id})")
            # Still log even without telegram
            await _log_alert(db, hos.driver_id, alert_type, message,
                              None, hos.eld_source, extra)

    # ── 1. ELD Disconnect ─────────────────────────────────────────────────────
    if not hos.is_connected:
        await alert("disconnect", msgs.get_disconnect_msg(hos.driver_name),
                    {"status": "disconnected"})
        return  # If disconnected, no point checking time values

    # ── 2. Document incomplete ────────────────────────────────────────────────
    if hos.document_incomplete:
        await alert("document_incomplete",
                    msgs.get_document_incomplete_msg(hos.driver_name))

    # ── 3. Profile form issue ─────────────────────────────────────────────────
    if not hos.profile_form_ok and hos.profile_issues:
        await alert("profile_form",
                    msgs.get_profile_form_msg(hos.driver_name, hos.profile_issues))

    # ── 4. Cycle < 20 hours ───────────────────────────────────────────────────
    if 0 < hos.cycle_remaining < CYCLE_WARN_HOURS:
        await alert("cycle_low",
                    msgs.get_cycle_low_msg(hos.driver_name, hos.cycle_remaining),
                    {"cycle_remaining": hos.cycle_remaining})

    # ── 5. Drive < 2 hours ────────────────────────────────────────────────────
    if 0 < hos.drive_remaining < DRIVE_WARN_HOURS:
        await alert("drive_low",
                    msgs.get_drive_low_msg(hos.driver_name, hos.drive_remaining),
                    {"drive_remaining": hos.drive_remaining})

    # ── 6. Shift < 2 hours ───────────────────────────────────────────────────
    if 0 < hos.shift_remaining < SHIFT_WARN_HOURS:
        await alert("shift_low",
                    msgs.get_shift_low_msg(hos.driver_name, hos.shift_remaining),
                    {"shift_remaining": hos.shift_remaining})

    # ── 7. Break < 2 hours ───────────────────────────────────────────────────
    if 0 < hos.break_remaining < BREAK_WARN_HOURS:
        await alert("break_low",
                    msgs.get_break_low_msg(hos.driver_name, hos.break_remaining),
                    {"break_remaining": hos.break_remaining})

    # ── 8. On Break notification ─────────────────────────────────────────────
    if hos.status == "SB" and hos.current_duration_min > 0:
        await alert("on_break",
                    msgs.get_on_break_msg(hos.driver_name, hos.current_duration_min),
                    {"duration_min": hos.current_duration_min})


# ─── Main polling loop ────────────────────────────────────────────────────────

async def run_monitor_cycle():
    """Called by scheduler every N minutes"""
    logger.info(f"🔄 Monitor cycle started at {datetime.utcnow().isoformat()}")

    async with AsyncSessionLocal() as db:
        # Load all active ELD sources
        sources_result = await db.execute(
            select(EldSource).where(EldSource.is_active == True)
        )
        sources = sources_result.scalars().all()

    if not sources:
        logger.warning("No active ELD sources configured. Skipping.")
        return

    for source in sources:
        logger.info(f"📡 Polling ELD source: {source.display_name}")
        client = EldClientFactory.get_client(
            source_name=source.name,
            base_url=source.base_url,
            bearer_token=source.bearer_token,
            tenant_id=source.tenant_id,
        )
        try:
            all_hos = await client.get_all_drivers_hos()
            logger.info(f"  → Got {len(all_hos)} drivers from {source.display_name}")

            async with AsyncSessionLocal() as db:
                for hos in all_hos:
                    try:
                        await check_driver(hos, db)
                    except Exception as e:
                        logger.error(f"check_driver error for {hos.driver_name}: {e}")
        except Exception as e:
            logger.error(f"ELD source {source.name} poll error: {e}")
        finally:
            await client.close()

    logger.info("✅ Monitor cycle complete")


async def get_recent_alerts(limit: int = 100) -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AlertLog).order_by(AlertLog.sent_at.desc()).limit(limit)
        )
        logs = result.scalars().all()
        return [
            {
                "id": l.id,
                "driver_id": l.driver_id,
                "alert_type": l.alert_type,
                "message": l.message_sent,
                "chat_id": l.telegram_chat_id,
                "eld_source": l.eld_source,
                "sent_at": l.sent_at.isoformat(),
            }
            for l in logs
        ]
