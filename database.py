from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, JSON
from datetime import datetime
from typing import Optional
import json

import os
_data_dir = "/data" if os.path.exists("/data") else "."
DATABASE_URL = f"sqlite+aiosqlite:///{_data_dir}/eld_monitor.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Driver(Base):
    """Maps ELD driver to Telegram group chat"""
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    eld_driver_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    driver_name: Mapped[str] = mapped_column(String(200))
    driver_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telegram_chat_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    eld_source: Mapped[str] = mapped_column(String(50), default="factor")  # factor, leader, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    company_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertLog(Base):
    """Logs all sent alerts to prevent spam"""
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_id: Mapped[str] = mapped_column(String(100), index=True)
    alert_type: Mapped[str] = mapped_column(String(100))  # e.g. "cycle_low", "disconnect"
    alert_key: Mapped[str] = mapped_column(String(200))   # unique key for dedup
    message_sent: Mapped[str] = mapped_column(Text)
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    eld_source: Mapped[str] = mapped_column(String(50), default="factor")
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON


class TelegramGroup(Base):
    """All Telegram groups the user is a member of"""
    __tablename__ = "telegram_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    chat_type: Mapped[str] = mapped_column(String(50))  # group, supergroup, channel
    member_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_synced: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppSettings(Base):
    """Key-value settings store"""
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EldSource(Base):
    """Registered ELD sources (Factor, Leader, etc.)"""
    __tablename__ = "eld_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(500))
    bearer_token: Mapped[str] = mapped_column(Text)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
