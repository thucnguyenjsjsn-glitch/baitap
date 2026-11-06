from fastapi import HTTPException
from app.config import settings
from app.schemas import ExtractedTicket, ExtractRequest

def extract_ticket(payload: ExtractRequest) -> ExtractedTicket:
    if settings.ai_mode == "mock":
        message = payload.message.lower()
        if any(x in message for x in ("hai lần", "2 lần", "trừ tiền", "thanh toán")):
            intent, severity = "billing", "high"
        elif any(x in message for x in ("lỗi", "không truy cập", "không đăng nhập")):
            intent, severity = "technical", "medium"
        else:
            intent, severity = "other", "low"
        return ExtractedTicket(ticket_id=payload.ticket_id, intent=intent,
            severity=severity, product=None, summary=payload.message[:200],
            needs_human_review=(intent == "other"))
    if settings.ai_mode != "openai":
        raise HTTPException(503, "AI_MODE phải là mock hoặc openai")
    if not settings.openai_api_key:
        raise HTTPException(503, "Chưa cấu hình OPENAI_API_KEY")
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0)
    structured = llm.with_structured_output(ExtractedTicket, method="json_schema")
    try:
        result = structured.invoke([
            ("system", "Trích xuất ticket từ tin nhắn. Giữ nguyên ticket_id được cấp. "
             "Không tính deadline. Không bịa thông tin. product=null nếu không rõ. "
             "Tin mơ hồ: intent=other và needs_human_review=true. "
             "Chỉ chọn intent và severity trong schema."),
            ("human", f"ticket_id hệ thống: {payload.ticket_id}\nTin nhắn: {payload.message}")
        ])
    except Exception as exc:
        raise HTTPException(502, "Không trích xuất được dữ liệu từ AI; vui lòng thử lại") from exc
    if result.ticket_id != payload.ticket_id:
        raise HTTPException(422, "AI trả ticket_id khác mã hệ thống cấp")
    return result
