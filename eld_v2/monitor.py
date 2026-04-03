"""
monitor.py — ELD monitoring loop
Polls every POLL_INTERVAL seconds, checks violations, sends Telegram alerts.
Alert state is persisted in SQLite so restarts don't reset the 30-min window.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

import database as db
from eld_client import ELDDriver
from messages import get_message_at_index

logger = logging.getLogger(__name__)

SETTINGS = {
    "poll_interval":           int(os.getenv("POLL_INTERVAL", "60")),
    "alert_repeat_minutes":    int(os.getenv("ALERT_REPEAT_MINUTES", "30")),
    "hos_shift_warning_hours": float(os.getenv("HOS_SHIFT_WARNING_HOURS", "2")),
    "hos_drive_warning_hours": float(os.getenv("HOS_DRIVE_WARNING_HOURS", "2")),
    "hos_break_warning_hours": float(os.getenv("HOS_BREAK_WARNING_HOURS", "2")),
    "hos_cycle_warning_hours": float(os.getenv("HOS_CYCLE_WARNING_HOURS", "30")),
    "on_duty_stuck_hours":     float(os.getenv("ON_DUTY_STUCK_HOURS", "2")),
    "profile_stale_days":      int(os.getenv("PROFILE_STALE_DAYS", "3")),
}

# Last poll time (for dashboard)
last_poll_time: str = "Never"


def _fmt_time(hours: float) -> str:
    m = int(hours * 60)
    h, rem = divmod(m, 60)
    return f"{h}h {rem}m" if h and rem else (f"{h}h" if h else f"{rem}m")


def _fmt_dur(minutes: float) -> str:
    h, m = divmod(int(minutes), 60)
    return f"{h}h {m}m" if h else f"{m} min"


def check_violations(driver: ELDDriver) -> list[tuple[str, dict]]:
    """Returns list of (alert_type, message_kwargs) for all current issues."""
    issues = []
    name = driver.full_name
    s = SETTINGS

    # Overtime
    if driver.drive_violation or driver.drive_remaining_hours < 0:
        issues.append(("violation_overtime", {"name": name}))

    # No PTI
    if not driver.has_pti and driver.status in ("driving", "on_duty", "D", "ON"):
        issues.append(("violation_no_pti", {"name": name}))

    is_active = driver.status not in ("off_duty", "sleeper_berth", "OFF", "SB")

    if is_active:
        if 0 < driver.shift_remaining_hours < s["hos_shift_warning_hours"]:
            issues.append(("hos_shift_low", {"name": name, "time": _fmt_time(driver.shift_remaining_hours)}))
        if 0 < driver.drive_remaining_hours < s["hos_drive_warning_hours"]:
            issues.append(("hos_drive_low", {"name": name, "time": _fmt_time(driver.drive_remaining_hours)}))
        if 0 < driver.break_remaining_hours < s["hos_break_warning_hours"]:
            issues.append(("hos_break_low", {"name": name, "time": _fmt_time(driver.break_remaining_hours)}))

    if 0 < driver.cycle_remaining_hours < s["hos_cycle_warning_hours"]:
        issues.append(("hos_cycle_low", {"name": name, "time": _fmt_time(driver.cycle_remaining_hours)}))

    if not driver.connected:
        issues.append(("driver_disconnect", {"name": name}))

    if driver.status in ("on_duty", "ON", "on_duty_not_driving"):
        dur = driver.status_duration_minutes()
        if dur and dur > s["on_duty_stuck_hours"] * 60:
            issues.append(("status_stuck_on_duty", {"name": name, "duration": _fmt_dur(dur)}))

    if driver.last_profile_update:
        try:
            if isinstance(driver.last_profile_update, str):
                last = datetime.fromisoformat(driver.last_profile_update.replace("Z", "+00:00"))
            else:
                from datetime import timezone as tz
                last = datetime.fromtimestamp(driver.last_profile_update, tz=timezone.utc)
            days = (datetime.now(timezone.utc) - last).days
            if days >= s["profile_stale_days"]:
                issues.append(("profile_stale", {"name": name, "days": str(days)}))
        except Exception:
            pass

    if not driver.logs_certified:
        issues.append(("certification_missing", {
            "name": name,
            "days": str(getattr(driver, "uncertified_days", 1))
        }))

    return issues


async def _should_send(driver_id: str, alert_type: str, repeat_minutes: int) -> bool:
    row = await db.get_active_alert(driver_id, alert_type)
    if not row:
        return True
    if not row["last_sent"]:
        return True
    last = datetime.fromisoformat(row["last_sent"])
    elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 60
    return elapsed >= repeat_minutes


async def process_driver(driver: ELDDriver, telegram_manager):
    """Check one driver and fire alerts as needed."""
    await db.upsert_driver(driver)

    violations = check_violations(driver)
    current_types = [v[0] for v in violations]
    await db.clear_resolved_alerts(driver.id, current_types)

    for alert_type, kwargs in violations:
        if not await _should_send(driver.id, alert_type, SETTINGS["alert_repeat_minutes"]):
            continue

        # Get current send count to pick message variant
        row = await db.get_active_alert(driver.id, alert_type)
        send_count = (row["send_count"] if row else 0) + 1
        msg_index = send_count % 15  # cycles through 15 variants

        try:
            message = get_message_at_index(alert_type, msg_index, **kwargs)
            success, group = await telegram_manager.send_alert(driver.full_name, message)
            now = datetime.now(timezone.utc).isoformat()

            await db.upsert_active_alert(
                driver.id, driver.full_name, alert_type,
                now, send_count, msg_index
            )
            await db.log_alert(driver.full_name, alert_type, message, group, success)

            if success:
                logger.info(f"✓ Alert: {driver.full_name} | {alert_type} | variant #{msg_index}")
            else:
                logger.warning(f"✗ No group: {driver.full_name} | {alert_type}")

        except Exception as e:
            logger.error(f"Error processing {driver.full_name}/{alert_type}: {e}")


async def run_monitor(eld_clients: list, telegram_manager):
    """Main monitoring loop. Runs forever."""
    global last_poll_time
    poll_interval = SETTINGS["poll_interval"]
    logger.info(f"Monitor started — poll every {poll_interval}s, "
                f"alert repeat every {SETTINGS['alert_repeat_minutes']}min")

    while True:
        try:
            all_drivers = []
            for client in eld_clients:
                try:
                    drivers = await client.get_all_driver_data()
                    all_drivers.extend(drivers)
                except Exception as e:
                    logger.error(f"Failed to fetch from {client.account_name}: {e}")

            for driver in all_drivers:
                await process_driver(driver, telegram_manager)

            last_poll_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            logger.info(f"Poll done — {len(all_drivers)} drivers checked")

        except Exception as e:
            logger.error(f"Monitor loop error: {e}", exc_info=True)

        await asyncio.sleep(poll_interval)
