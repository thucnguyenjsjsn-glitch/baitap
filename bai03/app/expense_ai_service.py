import re
from fastapi import HTTPException
from app.config import settings
from app.expense_schemas import ExpenseExtracted

def extract(payload):
    if settings.ai_mode=='mock':
        text=payload.text
        def field(label):
            m=re.search(r'^'+label+r'\s*:\s*(.+)$',text,re.I|re.M)
            return m.group(1).strip() if m else None
        raw={'submission_id':payload.submission_id,'vendor':field('vendor'),'invoice_number':field('invoice_number'),'transaction_date':field('transaction_date'),'amount_minor':field('amount_minor'),'currency':field('currency'),'receipt_id':field('receipt_id')}
        try: result=ExpenseExtracted(**raw)
        except Exception as exc:raise HTTPException(422,'Dữ liệu mẫu không đúng schema') from exc
    elif settings.ai_mode=='openai':
        if not settings.openai_api_key:raise HTTPException(503,'Thiếu OPENAI_API_KEY')
        from langchain_openai import ChatOpenAI
        model=ChatOpenAI(model=settings.openai_model,api_key=settings.openai_api_key,temperature=0).with_structured_output(ExpenseExtracted,method='json_schema')
        try:result=model.invoke([('system','Trích xuất hóa đơn theo schema. Không suy đoán trường thiếu: null và liệt kê missing_fields. amount_minor là số nguyên đơn vị nhỏ nhất, VND đồng, USD cent. Giữ nguyên submission_id được cấp. Không tự kết luận trùng hoặc gian lận.'),('human',f'submission_id: {payload.submission_id}\nVăn bản:\n{payload.text}')])
        except Exception as exc:raise HTTPException(502,'OpenAI trích xuất thất bại') from exc
    else:raise HTTPException(503,'AI_MODE không hợp lệ')
    if result.submission_id!=payload.submission_id:raise HTTPException(422,'AI trả sai submission_id')
    result.missing_fields=[k for k in ('vendor','invoice_number','transaction_date','amount_minor','currency','receipt_id') if getattr(result,k) is None]
    return result
