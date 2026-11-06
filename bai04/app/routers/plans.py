from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.plan_schemas import ExtractRequest, ValidateRequest, OrderRequest
from app.plan_ai_service import extract as ai_extract
from app.plan_service import validate_plan, order_plan
from app.plan_models import PlanRecord

router = APIRouter(tags=['Bài 04 - Plans'])

@router.post('/plans/extract')
def extract(payload: ExtractRequest, request: Request):
    return {'extracted': ai_extract(payload.text, request.app.state.settings).model_dump(mode='json')}

@router.post('/plans/validate')
def validate(payload: ValidateRequest):
    return validate_plan(payload.extracted)

@router.post('/plans/order')
def order(payload: OrderRequest, db: Session = Depends(get_db)):
    result = order_plan(payload.extracted)
    if payload.save:
        record = PlanRecord(original_text=payload.original_text,
            ai_json=(payload.ai_extracted or payload.extracted).model_dump(mode='json'),
            confirmed_json=payload.extracted.model_dump(mode='json'),
            result_json=result, status=result['status'])
        db.add(record)
        db.commit()
        db.refresh(record)
        return {'plan_id':record.id, **result}
    return result
