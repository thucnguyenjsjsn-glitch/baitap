from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.dependencies import get_db
from app.expense_schemas import ExtractRequest,CheckRequest,ReviewRequest,ExpenseExtracted
from app.expense_models import Expense
from app.expense_ai_service import extract as ai_extract
from app.expense_service import check,validate
router=APIRouter(tags=['Bài 03 - Expenses'])

def existing(db):
    return [ExpenseExtracted.model_validate(x.confirmed_json) for x in db.scalars(select(Expense)).all()]

@router.post('/expenses/extract')
def extract(payload:ExtractRequest):
    return {'extracted':ai_extract(payload).model_dump(mode='json')}

@router.post('/expenses/check')
def check_expense(payload:CheckRequest,db:Session=Depends(get_db)):
    return check(payload.extracted,existing(db))

@router.post('/expenses/review',status_code=201)
def review(payload:ReviewRequest,db:Session=Depends(get_db)):
    validate(payload.extracted)
    if payload.ai_extracted and payload.ai_extracted.submission_id!=payload.extracted.submission_id:raise HTTPException(422,'AI submission_id khác bản sửa')
    try:
        db.execute(text('SELECT pg_advisory_xact_lock(20261102, 3)'))
        if db.get(Expense,payload.extracted.submission_id):raise HTTPException(409,'submission_id đã tồn tại')
        result=check(payload.extracted,existing(db))
        if result['status']=='needs_review' and payload.decision!='needs_review':raise HTTPException(422,'Thiếu khóa tra cứu, cần needs_review')
        if result['status']!='duplicate_candidate' and payload.decision=='confirm_suspicion':raise HTTPException(422,'Không có ứng viên trùng để xác nhận')
        db.add(Expense(submission_id=payload.extracted.submission_id,original_text=payload.original_text,ai_json=(payload.ai_extracted or payload.extracted).model_dump(mode='json'),confirmed_json=payload.extracted.model_dump(mode='json'),check_result=result,decision=payload.decision,note=payload.note,reviewed_at=datetime.now(timezone.utc)))
        db.commit()
    except IntegrityError as exc:
        db.rollback();raise HTTPException(409,'submission_id trùng') from exc
    return {'submission_id':payload.extracted.submission_id,'decision':payload.decision,'check':result}
