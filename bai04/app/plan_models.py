from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, JSON, Text, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class PlanRecord(Base):
    __tablename__ = 'plans'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    ai_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    confirmed_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
