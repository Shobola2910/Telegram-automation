"""
database.py — SQLite storage using aiosqlite
Tables: companies, drivers, alert_history, active_alerts
"""

import aiosqlite
import json
from datetime import datetime, timezone
from typing import Optional

DB_PATH = "eld_monitor.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usdot TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                mc_number TEXT,
                address TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eld_driver_id TEXT NOT NULL,
                eld_account TEXT NOT NULL,
                full_name TEXT NOT NULL,
                company_usdot TEXT,
                status TEXT,
                drive_remaining_h REAL DEFAULT 0,
                shift_remaining_h REAL DEFAULT 0,
                cycle_remaining_h REAL DEFAULT 0,
                break_remaining_h REAL DEFAULT 0,
                connected INTEGER DEFAULT 1,
                tg_group_name TEXT,
                last_seen TEXT,
                UNIQUE(eld_driver_id, eld_account)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS active_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id TEXT NOT NULL,
                driver_name TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_sent TEXT,
                send_count INTEGER DEFAULT 0,
                message_index INTEGER DEFAULT 0,
                UNIQUE(driver_id, alert_type)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_name TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                tg_group TEXT,
                sent_at TEXT DEFAULT (datetime('now')),
                success INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.commit()


# ── Companies ──────────────────────────────────────────────────────────────────

async def upsert_company(usdot: str, name: str, mc_number: str = "", address: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO companies (usdot, name, mc_number, address)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(usdot) DO UPDATE SET name=excluded.name,
                mc_number=excluded.mc_number, address=excluded.address
        """, (usdot, name, mc_number, address))
        await db.commit()


async def get_companies() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM companies ORDER BY name") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def delete_company(usdot: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM companies WHERE usdot = ?", (usdot,))
        await db.commit()


# ── Drivers ────────────────────────────────────────────────────────────────────

async def upsert_driver(driver):
    """Save or update driver data from ELD."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO drivers
                (eld_driver_id, eld_account, full_name, status,
                 drive_remaining_h, shift_remaining_h, cycle_remaining_h,
                 break_remaining_h, connected, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(eld_driver_id, eld_account) DO UPDATE SET
                full_name = excluded.full_name,
                status = excluded.status,
                drive_remaining_h = excluded.drive_remaining_h,
                shift_remaining_h = excluded.shift_remaining_h,
                cycle_remaining_h = excluded.cycle_remaining_h,
                break_remaining_h = excluded.break_remaining_h,
                connected = excluded.connected,
                last_seen = excluded.last_seen
        """, (
            driver.id, driver.account_name, driver.full_name, driver.status,
            driver.drive_remaining_hours, driver.shift_remaining_hours,
            driver.cycle_remaining_hours, driver.break_remaining_hours,
            1 if driver.connected else 0, now
        ))
        await db.commit()


async def get_drivers() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM drivers ORDER BY full_name"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def update_driver_tg_group(eld_driver_id: str, eld_account: str, group_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE drivers SET tg_group_name = ?
            WHERE eld_driver_id = ? AND eld_account = ?
        """, (group_name, eld_driver_id, eld_account))
        await db.commit()


# ── Active alerts ──────────────────────────────────────────────────────────────

async def get_active_alert(driver_id: str, alert_type: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM active_alerts WHERE driver_id=? AND alert_type=?",
            (driver_id, alert_type)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def upsert_active_alert(driver_id: str, driver_name: str, alert_type: str,
                               last_sent: str, send_count: int, message_index: int):
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO active_alerts
                (driver_id, driver_name, alert_type, first_seen, last_sent, send_count, message_index)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(driver_id, alert_type) DO UPDATE SET
                last_sent = excluded.last_sent,
                send_count = excluded.send_count,
                message_index = excluded.message_index
        """, (driver_id, driver_name, alert_type, now, last_sent, send_count, message_index))
        await db.commit()


async def delete_active_alert(driver_id: str, alert_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM active_alerts WHERE driver_id=? AND alert_type=?",
            (driver_id, alert_type)
        )
        await db.commit()


async def get_all_active_alerts() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM active_alerts ORDER BY first_seen DESC"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def clear_resolved_alerts(driver_id: str, current_alert_types: list[str]):
    """Remove alerts for issues that are no longer occurring."""
    if not current_alert_types:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM active_alerts WHERE driver_id=?", (driver_id,))
            await db.commit()
        return

    placeholders = ",".join(["?" for _ in current_alert_types])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"DELETE FROM active_alerts WHERE driver_id=? AND alert_type NOT IN ({placeholders})",
            [driver_id] + current_alert_types
        )
        await db.commit()


# ── Alert history ──────────────────────────────────────────────────────────────

async def log_alert(driver_name: str, alert_type: str, message: str,
                    tg_group: str = "", success: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO alert_history (driver_name, alert_type, message, tg_group, success)
            VALUES (?, ?, ?, ?, ?)
        """, (driver_name, alert_type, message, tg_group, 1 if success else 0))
        # Keep only last 500 records
        await db.execute("""
            DELETE FROM alert_history WHERE id NOT IN (
                SELECT id FROM alert_history ORDER BY id DESC LIMIT 500
            )
        """)
        await db.commit()


async def get_alert_history(limit: int = 100) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM alert_history ORDER BY id DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM drivers") as cur:
            total_drivers = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM active_alerts") as cur:
            active_alerts = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM drivers WHERE connected=1") as cur:
            connected = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM companies") as cur:
            companies = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM alert_history WHERE date(sent_at) = date('now')"
        ) as cur:
            sent_today = (await cur.fetchone())[0]
        return {
            "total_drivers": total_drivers,
            "active_alerts": active_alerts,
            "connected_drivers": connected,
            "companies": companies,
            "sent_today": sent_today,
        }
