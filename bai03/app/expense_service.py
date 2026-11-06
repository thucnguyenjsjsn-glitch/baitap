import unicodedata
from datetime import date
from fastapi import HTTPException

def norm(value):
    return ' '.join(unicodedata.normalize('NFKC',value).casefold().split()) if value else None

def validate(e):
    if not e.submission_id.strip(): raise HTTPException(422,'submission_id trống')
    if e.amount_minor is not None and e.amount_minor<0: raise HTTPException(422,'Số tiền không được âm')
    if e.currency is not None and e.currency.upper() not in ('VND','USD'): raise HTTPException(422,'Loại tiền không hỗ trợ (VND/USD)')
    if e.transaction_date is not None and e.transaction_date>date.today(): raise HTTPException(422,'Ngày giao dịch ở tương lai')
    return e

def keys(e):
    currency=norm(e.currency)
    if not currency:return []
    result=[]
    if norm(e.receipt_id):result.append(('receipt',currency,norm(e.receipt_id)))
    if norm(e.vendor) and norm(e.invoice_number):result.append(('invoice',currency,norm(e.vendor),norm(e.invoice_number)))
    return result

def check(e,previous):
    validate(e)
    own=keys(e)
    if not own:return {'status':'needs_review','matches':[],'reason':'Thiếu mã biên nhận hoặc cặp nơi bán + số hóa đơn hoặc loại tiền'}
    index={}
    for old in previous:
        for key in keys(old):index.setdefault(key,[]).append(old)
    matches={}
    for key in own:
        for old in index.get(key,[]):
            if old.submission_id==e.submission_id:continue
            entry=matches.setdefault(old.submission_id,{'submission_id':old.submission_id,'matched_by':[],'differences':{}})
            entry['matched_by'].append(key[0])
            for field in ('vendor','invoice_number','transaction_date','amount_minor','currency','receipt_id'):
                a=getattr(e,field);b=getattr(old,field)
                if (norm(a)!=norm(b) if isinstance(a,str) or isinstance(b,str) else a!=b):
                    entry['differences'][field]={'current':str(a) if isinstance(a,date) else a,'previous':str(b) if isinstance(b,date) else b}
    return {'status':'duplicate_candidate' if matches else 'unique_under_current_rules','matches':list(matches.values()),'reason':'Có khóa trùng' if matches else 'Chưa có khóa trùng theo quy tắc hiện tại'}
