from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas import ExtractRequest, ConfirmRequest
from app.ai_service import extract_ticket
from app.ticket_service import deadline, top_k, reason
from app import ticket_repository as repo

router = APIRouter(prefix="/tickets", tags=["tickets"])
def present(item):
    return {**item, "reason": reason(item)}

@router.post("/extract")
def extract(payload: ExtractRequest):
    result = extract_ticket(payload)
    if result.ticket_id != payload.ticket_id:
        raise HTTPException(422, "AI trả sai ticket_id")
    return {"extracted": result.model_dump(), "deadline_at": deadline(payload.received_at, result.severity)}

@router.post("/confirm", status_code=201)
def confirm(payload: ConfirmRequest, db: Session = Depends(get_db)):
    if payload.ticket_id != payload.extracted.ticket_id:
        raise HTTPException(422, "ticket_id của AI khác mã hệ thống cấp")
    if payload.ai_extracted is not None and payload.ai_extracted.ticket_id != payload.ticket_id:
        raise HTTPException(422, "ai_extracted có ticket_id không khớp")
    due = deadline(payload.received_at, payload.extracted.severity)
    if not repo.add_ticket(db, payload, payload.extracted, payload.ai_extracted or payload.extracted):
        raise HTTPException(409, "ticket_id đã tồn tại")
    return {"ticket_id": payload.ticket_id, "deadline_at": due, "status": "queued"}

@router.get("/queue")
def queue(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    return [present(item) for item in top_k(repo.list_queue(db), limit)]

@router.post("/next")
def next_ticket(db: Session = Depends(get_db)):
    item = repo.pop_next(db)
    return present(item) if item else {"message": "Hàng đợi trống"}
