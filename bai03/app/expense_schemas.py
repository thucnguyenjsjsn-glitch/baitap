from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class ExpenseExtracted(BaseModel):
    submission_id: str
    vendor: str | None = None
    invoice_number: str | None = None
    transaction_date: date | None = None
    amount_minor: int | None = None
    currency: str | None = None
    receipt_id: str | None = None
    missing_fields: list[str] = Field(default_factory=list)

class ExtractRequest(BaseModel):
    submission_id: str
    text: str = Field(min_length=1)

class CheckRequest(BaseModel):
    extracted: ExpenseExtracted

class ReviewRequest(BaseModel):
    original_text: str = Field(min_length=1)
    extracted: ExpenseExtracted
    ai_extracted: ExpenseExtracted | None = None
    decision: Literal['confirm_suspicion','dismiss_suspicion','needs_review']
    note: str | None = None
