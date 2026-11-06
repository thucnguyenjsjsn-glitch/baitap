from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

class ExtractedTicket(BaseModel):
    ticket_id: str = Field(min_length=1)
    intent: Literal["billing", "technical", "account", "other"]
    severity: Literal["low", "medium", "high", "critical"]
    product: str | None = None
    summary: str = Field(min_length=1, max_length=200)
    needs_human_review: bool

class ExtractRequest(BaseModel):
    ticket_id: str = Field(min_length=1)
    received_at: datetime
    message: str = Field(min_length=1)
    @field_validator("received_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("received_at phải có múi giờ")
        return value

class ConfirmRequest(ExtractRequest):
    extracted: ExtractedTicket
    ai_extracted: ExtractedTicket | None = None

class TicketView(BaseModel):
    ticket_id: str
    received_at: datetime
    deadline_at: datetime
    intent: str
    severity: str
    product: str | None
    summary: str
    needs_human_review: bool
    reason: str
