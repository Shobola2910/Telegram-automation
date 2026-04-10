"""
FastAPI routers — REST API for frontend dashboard
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import Optional
import logging

from database import get_db, Driver, EldSource, TelegramGroup, AlertLog
from services import telegram_client as tg
from services.monitor import run_monitor_cycle, get_recent_alerts
from services.eld_client import EldClientFactory

logger = logging.getLogger(__name__)

# ─── Pydantic schemas ────────────────────────────────────────────────────────

class DriverCreate(BaseModel):
    eld_driver_id: str
    driver_name: str
    driver_email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_chat_title: Optional[str] = None
    eld_source: str = "factor"
    company_id: Optional[str] = None

class DriverUpdate(BaseModel):
    driver_name: Optional[str] = None
    driver_email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_chat_title: Optional[str] = None
    is_active: Optional[bool] = None

class EldSourceCreate(BaseModel):
    name: str
    display_name: str
    base_url: str
    bearer_token: str
    tenant_id: Optional[str] = None
    is_active: bool = True

class TelegramAuthStep1(BaseModel):
    phone: str

class TelegramAuthStep2(BaseModel):
    phone: str
    code: str
    phone_code_hash: str
    password: Optional[str] = ""

class ManualAlertRequest(BaseModel):
    chat_id: str
    message: str

# ─── Drivers router ──────────────────────────────────────────────────────────

drivers_router = APIRouter(prefix="/api/drivers", tags=["drivers"])

@drivers_router.get("")
async def list_drivers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Driver).order_by(Driver.driver_name))
    drivers = result.scalars().all()
    return [
        {
            "id": d.id,
            "eld_driver_id": d.eld_driver_id,
            "driver_name": d.driver_name,
            "driver_email": d.driver_email,
            "telegram_chat_id": d.telegram_chat_id,
            "telegram_chat_title": d.telegram_chat_title,
            "eld_source": d.eld_source,
            "company_id": d.company_id,
            "is_active": d.is_active,
        }
        for d in drivers
    ]

@drivers_router.post("")
async def create_driver(body: DriverCreate, db: AsyncSession = Depends(get_db)):
    driver = Driver(**body.model_dump())
    db.add(driver)
    await db.commit()
    await db.refresh(driver)
    return {"id": driver.id, "message": "Driver qo'shildi"}

@drivers_router.put("/{driver_id}")
async def update_driver(driver_id: int, body: DriverUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Driver).where(Driver.id == driver_id))
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(404, "Driver topilmadi")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(driver, k, v)
    await db.commit()
    return {"message": "Yangilandi"}

@drivers_router.delete("/{driver_id}")
async def delete_driver(driver_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Driver).where(Driver.id == driver_id))
    await db.commit()
    return {"message": "O'chirildi"}

@drivers_router.post("/sync-from-eld")
async def sync_drivers_from_eld(eld_source_id: int, db: AsyncSession = Depends(get_db)):
    """Pull drivers from ELD and create/update records"""
    src_result = await db.execute(select(EldSource).where(EldSource.id == eld_source_id))
    src = src_result.scalar_one_or_none()
    if not src:
        raise HTTPException(404, "ELD source topilmadi")

    client = EldClientFactory.get_client(src.name, src.base_url, src.bearer_token, src.tenant_id)
    try:
        eld_drivers = await client.get_drivers()
    finally:
        await client.close()

    added, updated = 0, 0
    for d in eld_drivers:
        eld_id = str(d.get("id") or d.get("driver_id", ""))
        if not eld_id:
            continue
        name = (d.get("name") or
                f"{d.get('first_name','')} {d.get('last_name','')}".strip() or
                "Unknown")
        existing = await db.execute(
            select(Driver).where(Driver.eld_driver_id == eld_id,
                                  Driver.eld_source == src.name)
        )
        row = existing.scalar_one_or_none()
        if row:
            row.driver_name = name
            row.driver_email = d.get("email", row.driver_email)
            updated += 1
        else:
            db.add(Driver(
                eld_driver_id=eld_id,
                driver_name=name,
                driver_email=d.get("email"),
                eld_source=src.name,
                company_id=str(d.get("company_id", "")),
            ))
            added += 1
    await db.commit()
    return {"added": added, "updated": updated, "total": len(eld_drivers)}


# ─── ELD Sources router ──────────────────────────────────────────────────────

eld_router = APIRouter(prefix="/api/eld-sources", tags=["eld"])

@eld_router.get("")
async def list_eld_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EldSource))
    sources = result.scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "display_name": s.display_name,
            "base_url": s.base_url,
            "tenant_id": s.tenant_id,
            "is_active": s.is_active,
            "bearer_token_preview": s.bearer_token[:20] + "..." if s.bearer_token else "",
        }
        for s in sources
    ]

@eld_router.post("")
async def create_eld_source(body: EldSourceCreate, db: AsyncSession = Depends(get_db)):
    src = EldSource(**body.model_dump())
    db.add(src)
    await db.commit()
    await db.refresh(src)
    return {"id": src.id, "message": "ELD source qo'shildi"}

@eld_router.delete("/{source_id}")
async def delete_eld_source(source_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(EldSource).where(EldSource.id == source_id))
    await db.commit()
    return {"message": "O'chirildi"}


# ─── Telegram router ─────────────────────────────────────────────────────────

tg_router = APIRouter(prefix="/api/telegram", tags=["telegram"])

_pending_auth: dict[str, str] = {}  # phone -> phone_code_hash

@tg_router.get("/status")
async def telegram_status():
    authorized = await tg.is_authorized()
    session = await tg.get_session_string()
    return {
        "authorized": authorized,
        "session_saved": bool(session),
    }

@tg_router.post("/auth/send-code")
async def telegram_send_code(body: TelegramAuthStep1):
    try:
        hash_ = await tg.send_code_request(body.phone)
        _pending_auth[body.phone] = hash_
        return {"message": "SMS kod yuborildi", "phone": body.phone}
    except Exception as e:
        raise HTTPException(400, str(e))

@tg_router.post("/auth/verify")
async def telegram_verify(body: TelegramAuthStep2):
    hash_ = _pending_auth.get(body.phone) or body.phone_code_hash
    try:
        result = await tg.sign_in(body.phone, body.code, hash_, body.password or "")
        _pending_auth.pop(body.phone, None)
        return {"message": "Muvaffaqiyatli kirildi", **result}
    except Exception as e:
        raise HTTPException(400, str(e))

@tg_router.get("/groups")
async def get_telegram_groups(db: AsyncSession = Depends(get_db)):
    groups = await tg.get_all_groups()
    # Upsert to DB
    for g in groups:
        existing = await db.execute(
            select(TelegramGroup).where(TelegramGroup.chat_id == g["chat_id"])
        )
        row = existing.scalar_one_or_none()
        if row:
            row.title = g["title"]
            row.chat_type = g["chat_type"]
            row.member_count = g.get("member_count")
        else:
            db.add(TelegramGroup(
                chat_id=g["chat_id"],
                title=g["title"],
                chat_type=g["chat_type"],
                member_count=g.get("member_count"),
            ))
    await db.commit()
    return groups

@tg_router.post("/send")
async def send_manual_message(body: ManualAlertRequest):
    success = await tg.send_message(body.chat_id, body.message)
    if not success:
        raise HTTPException(500, "Yuborishda xato")
    return {"message": "Yuborildi"}


# ─── Monitor router ──────────────────────────────────────────────────────────

monitor_router = APIRouter(prefix="/api/monitor", tags=["monitor"])

@monitor_router.post("/run")
async def trigger_monitor(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_monitor_cycle)
    return {"message": "Monitor ishga tushirildi"}

@monitor_router.get("/alerts")
async def get_alerts(limit: int = 100):
    alerts = await get_recent_alerts(limit)
    return alerts

@monitor_router.get("/alerts/stats")
async def alert_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    result = await db.execute(
        select(AlertLog.alert_type, func.count(AlertLog.id).label("count"))
        .group_by(AlertLog.alert_type)
        .order_by(func.count(AlertLog.id).desc())
    )
    rows = result.all()
    return [{"alert_type": r[0], "count": r[1]} for r in rows]
