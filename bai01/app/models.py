from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint("severity IN ('low','medium','high','critical')", name="ck_ticket_severity"),
        Index("ix_ticket_status_deadline", "status", "deadline_at"),
    )
    ticket_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    original_message: Mapped[str] = mapped_column(Text, nullable=False)
    ai_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confirmed_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    intent: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str] = mapped_column(String(200), nullable=False)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'queued'"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
