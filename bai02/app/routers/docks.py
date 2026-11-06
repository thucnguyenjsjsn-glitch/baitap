from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.dependencies import get_db
from app.dock_schemas import DockExtractRequest, SlotRequest, ConfirmBooking
from app.dock_ai_service import extract_dock_request
from app.dock_models import Dock, Booking
from app.dock_service import suggest, validate_request

router=APIRouter(tags=["Bài 02 - Dock Scheduling"])

@router.post("/requests/extract")
def extract(payload:DockExtractRequest):
    result=extract_dock_request(payload)
    if result.request_id!=payload.request_id: raise HTTPException(422,"AI trả sai request_id")
    return {"extracted":result.model_dump(mode="json")}

@router.post("/slots/suggest")
def slots(payload:SlotRequest,db:Session=Depends(get_db)):
    docks=db.scalars(select(Dock).order_by(Dock.dock_id)).all()
    bookings=db.scalars(select(Booking)).all()
    return suggest(payload.extracted,docks,bookings)

@router.post("/bookings/confirm",status_code=201)
def confirm(payload:ConfirmBooking,db:Session=Depends(get_db)):
    r=validate_request(payload.extracted)
    if payload.ai_extracted is not None and payload.ai_extracted.request_id!=r.request_id: raise HTTPException(422,"ai_extracted sai request_id")
    if payload.start_at < r.earliest_start: raise HTTPException(422,"Giờ đặt trước earliest_start")
    if payload.end_at-payload.start_at!=timedelta(minutes=r.duration_minutes): raise HTTPException(422,"Thời lượng không khớp")
    if payload.start_at.date()!=r.earliest_start.date() or payload.end_at.date()!=r.earliest_start.date(): raise HTTPException(422,"Không tự chuyển sang ngày hôm sau")
    if payload.start_at.timetz().replace(tzinfo=None)<datetime.min.replace(hour=8).time() or payload.end_at.timetz().replace(tzinfo=None)>datetime.min.replace(hour=18).time(): raise HTTPException(422,"Ngoài giờ 08:00–18:00")
    try:
        # Serialize booking confirmations, including concurrent requests across workers.
        db.execute(text("SELECT pg_advisory_xact_lock(20261031, 2)"))
        if db.get(Booking,r.request_id): raise HTTPException(409,"request_id đã tồn tại")
        dock=db.get(Dock,payload.dock_id)
        if dock is None or dock.dock_type!=r.dock_type: raise HTTPException(422,"Cửa kho không tồn tại hoặc sai loại")
        conflict=db.scalar(select(Booking.request_id).where(Booking.dock_id==payload.dock_id,Booking.start_at<payload.end_at,Booking.end_at>payload.start_at).limit(1))
        if conflict: raise HTTPException(409,"Cửa kho đã được đặt trong khoảng giờ này")
        db.add(Booking(request_id=r.request_id,dock_id=payload.dock_id,start_at=payload.start_at,end_at=payload.end_at,carrier=r.carrier,duration_minutes=r.duration_minutes,original_email=payload.email,ai_json=(payload.ai_extracted or r).model_dump(mode="json"),confirmed_json=r.model_dump(mode="json"),confirmed_at=datetime.now(timezone.utc)))
        db.commit()
    except IntegrityError as exc:
        db.rollback();raise HTTPException(409,"request_id trùng hoặc dữ liệu không hợp lệ") from exc
    return {"status":"confirmed","request_id":r.request_id,"dock_id":payload.dock_id,"start_at":payload.start_at,"end_at":payload.end_at}

@router.get("/docks/schedule")
def schedule(db:Session=Depends(get_db)):
    docks=db.scalars(select(Dock).order_by(Dock.dock_id)).all()
    bookings=db.scalars(select(Booking).order_by(Booking.start_at)).all()
    return [{"dock_id":d.dock_id,"dock_type":d.dock_type,"bookings":[{"request_id":b.request_id,"start_at":b.start_at,"end_at":b.end_at} for b in bookings if b.dock_id==d.dock_id]} for d in docks]
