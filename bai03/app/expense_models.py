from datetime import datetime
from sqlalchemy import String,Text,DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base
class Expense(Base):
    __tablename__='expenses'
    submission_id:Mapped[str]=mapped_column(String(60),primary_key=True)
    original_text:Mapped[str]=mapped_column(Text,nullable=False)
    ai_json:Mapped[dict]=mapped_column(JSONB,nullable=False)
    confirmed_json:Mapped[dict]=mapped_column(JSONB,nullable=False)
    check_result:Mapped[dict]=mapped_column(JSONB,nullable=False)
    decision:Mapped[str]=mapped_column(String(40),nullable=False)
    note:Mapped[str|None]=mapped_column(Text)
    reviewed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
