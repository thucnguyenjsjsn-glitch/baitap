from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import Ticket
from app.ticket_service import deadline

def as_dict(t: Ticket) -> dict:
    return {name: getattr(t, name) for name in (
        "ticket_id", "received_at", "deadline_at", "intent", "severity", "product",
        "summary", "needs_human_review")}

def add_ticket(db: Session, payload, extracted, ai_extracted) -> bool:
    ticket = Ticket(ticket_id=payload.ticket_id, received_at=payload.received_at,
        original_message=payload.message, ai_json=ai_extracted.model_dump(),
        confirmed_json=extracted.model_dump(), deadline_at=deadline(payload.received_at, extracted.severity),
        intent=extracted.intent, severity=extracted.severity, product=extracted.product,
        summary=extracted.summary, needs_human_review=extracted.needs_human_review, status="queued")
    db.add(ticket)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Only duplicate primary keys should become 409; other DB errors must surface.
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "23505":
            return False
        raise
    return True

def list_queue(db: Session) -> list[dict]:
    return [as_dict(t) for t in db.scalars(select(Ticket).where(Ticket.status == "queued")).all()]

def pop_next(db: Session) -> dict | None:
    # PostgreSQL locks the selected row to avoid double-processing across workers.
    from sqlalchemy import case
    rank = case((Ticket.severity == "critical", 4), (Ticket.severity == "high", 3),
        (Ticket.severity == "medium", 2), else_=1)
    ticket = db.scalar(select(Ticket).where(Ticket.status == "queued")
        .order_by(Ticket.deadline_at.asc(), rank.desc(), Ticket.received_at.asc(), Ticket.ticket_id.asc())
        .limit(1).with_for_update(skip_locked=True))
    if ticket is None:
        db.rollback()
        return None
    result = as_dict(ticket)
    ticket.status = "processing"
    ticket.processed_at = datetime.now(timezone.utc)
    db.commit()
    return result
