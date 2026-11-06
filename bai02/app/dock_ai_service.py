import re
from datetime import datetime
from fastapi import HTTPException
from app.config import settings
from app.dock_schemas import DockExtracted, DockExtractRequest

def extract_dock_request(payload: DockExtractRequest):
    if settings.ai_mode=="mock":
        email=payload.email
        duration=re.search(r"(\d+)\s*(?:phút|minutes)",email,re.I)
        hours=re.search(r"(\d+)\s*(?:giờ|hours)",email,re.I)
        date=re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2}|Z)",email)
        start=datetime.fromisoformat(date.group(0).replace("Z","+00:00")) if date else None
        mins=int(duration.group(1)) if duration else (int(hours.group(1))*60 if hours else None)
        kind="refrigerated" if any(k in email.lower() for k in ("cửa lạnh","refrigerated","kho lạnh")) else ("standard" if any(k in email.lower() for k in ("cửa thường","standard")) else None)
        result=DockExtracted(request_id=payload.request_id,earliest_start=start,duration_minutes=mins,dock_type=kind)
        result.missing_fields=[k for k in ("carrier","earliest_start","duration_minutes","dock_type") if getattr(result,k) is None]
        return result
    if settings.ai_mode!="openai": raise HTTPException(503,"AI_MODE không hợp lệ")
    if not settings.openai_api_key: raise HTTPException(503,"Chưa cấu hình OPENAI_API_KEY")
    from langchain_openai import ChatOpenAI
    model=ChatOpenAI(model=settings.openai_model,api_key=settings.openai_api_key,temperature=0).with_structured_output(DockExtracted,method="json_schema")
    try:
        result=model.invoke([("system","Trích xuất yêu cầu nhận xe. Giữ nguyên request_id do hệ thống cấp. Không tự đoán trường chưa biết, để null và liệt kê trong missing_fields. earliest_start phải có múi giờ. Chỉ dùng dock_type standard hoặc refrigerated. Không tự tìm giờ trống."),("human",f"request_id: {payload.request_id}\nEmail: {payload.email}")])
    except Exception as exc: raise HTTPException(502,"OpenAI không trích xuất được dữ liệu") from exc
    if result.request_id!=payload.request_id: raise HTTPException(422,"AI trả sai request_id")
    return result
