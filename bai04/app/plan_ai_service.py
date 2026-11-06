import json
from fastapi import HTTPException
from app.plan_schemas import PlanExtracted
from app.config import Settings

DEMO_PLAN = {
  'tasks': [
    {'id':'A','title':'Chốt yêu cầu API','owner':'Product'},
    {'id':'B','title':'Duyệt thiết kế UI','owner':'Design'},
    {'id':'C','title':'Tích hợp frontend','owner':'Engineering'},
    {'id':'D','title':'Kiểm thử end-to-end','owner':'QA'}],
  'dependencies': [
    {'before':'A','after':'C','evidence':'Sau khi chốt API mới tích hợp frontend'},
    {'before':'B','after':'C','evidence':'Duyệt UI trước khi tích hợp'},
    {'before':'C','after':'D','evidence':'Kiểm thử sau khi tích hợp'}]
}

def extract(text: str, settings: Settings) -> PlanExtracted:
    if settings.ai_mode == 'mock':
        # Dữ liệu mẫu cố định; nếu nhập JSON đúng schema thì dùng JSON đó.
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = DEMO_PLAN
        try: return PlanExtracted.model_validate(parsed)
        except Exception as exc: raise HTTPException(422,'JSON mẫu không đúng schema') from exc
    if settings.ai_mode != 'openai': raise HTTPException(503,'AI_MODE phải là mock hoặc openai')
    if not settings.openai_api_key: raise HTTPException(503,'Thiếu OPENAI_API_KEY')
    from langchain_openai import ChatOpenAI
    model = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0).with_structured_output(PlanExtracted,method='json_schema')
    try:
        return model.invoke([
            ('system','Đọc biên bản họp, trích xuất tasks và dependencies theo schema. ID công việc phải duy nhất; owner không biết thì null. Chỉ tạo quan hệ khi có bằng chứng trực tiếp trong văn bản, ghi evidence ngắn. Không tự đoán quan hệ hay tự tính thứ tự. Nếu không có quan hệ rõ ràng, dependencies là [].'),
            ('human',text)])
    except Exception as exc: raise HTTPException(502,'OpenAI trích xuất thất bại') from exc
