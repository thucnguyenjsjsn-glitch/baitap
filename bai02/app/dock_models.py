from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Dock(Base):
    __tablename__="docks"
    dock_id: Mapped[str] = mapped_column(String(30),primary_key=True)
    dock_type: Mapped[str] = mapped_column(String(30),nullable=False)

class Booking(Base):
    __tablename__="dock_bookings"
    __table_args__=(CheckConstraint("end_at > start_at",name="ck_booking_positive"),Index("ix_booking_dock_start","dock_id","start_at"))
    request_id: Mapped[str] = mapped_column(String(50),primary_key=True)
    dock_id: Mapped[str] = mapped_column(ForeignKey("docks.dock_id"),nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)
    carrier: Mapped[str|None] = mapped_column(String(255))
    duration_minutes: Mapped[int] = mapped_column(Integer,nullable=False)
    original_email: Mapped[str] = mapped_column(Text,nullable=False)
    ai_json: Mapped[dict] = mapped_column(JSONB,nullable=False)
    confirmed_json: Mapped[dict] = mapped_column(JSONB,nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)
