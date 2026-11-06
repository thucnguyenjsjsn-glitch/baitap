from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

DockType = Literal["standard", "refrigerated"]
class DockExtracted(BaseModel):
    request_id: str = Field(min_length=1)
    carrier: str | None = None
    earliest_start: datetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    dock_type: DockType | None = None
    missing_fields: list[str] = Field(default_factory=list)
    @field_validator("earliest_start")
    @classmethod
    def tz_required(cls, v):
        if v is not None and (v.tzinfo is None or v.utcoffset() is None): raise ValueError("earliest_start phải có múi giờ")
        return v

class DockExtractRequest(BaseModel):
    request_id: str = Field(min_length=1)
    email: str = Field(min_length=1)

class SlotRequest(BaseModel):
    extracted: DockExtracted

class ConfirmBooking(BaseModel):
    email: str = Field(min_length=1)
    extracted: DockExtracted
    ai_extracted: DockExtracted | None = None
    dock_id: str
    start_at: datetime
    end_at: datetime
    @field_validator("start_at", "end_at")
    @classmethod
    def timezone_required(cls, v):
        if v.tzinfo is None or v.utcoffset() is None: raise ValueError("Thời gian phải có múi giờ")
        return v
    @model_validator(mode="after")
    def positive_interval(self):
        if self.end_at <= self.start_at: raise ValueError("end_at phải sau start_at")
        return self
