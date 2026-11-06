from datetime import datetime, time, timedelta
from fastapi import HTTPException

def validate_request(r):
    if r.earliest_start is None or r.duration_minutes is None or r.dock_type is None:
        raise HTTPException(422, {"missing_fields": [k for k in ("earliest_start", "duration_minutes", "dock_type") if getattr(r,k) is None]})
    if r.earliest_start.utcoffset() is None: raise HTTPException(422, "earliest_start phải có múi giờ")
    return r

def merge_intervals(intervals):
    merged=[]
    for start,end in sorted(intervals):
        if end <= start: raise ValueError("Khoảng giờ không hợp lệ")
        if merged and start <= merged[-1][1]: merged[-1]=(merged[-1][0],max(merged[-1][1],end))
        else: merged.append((start,end))
    return merged

def suggest(r,docks,bookings):
    validate_request(r)
    tz=r.earliest_start.tzinfo
    day=r.earliest_start.date()
    opening=datetime.combine(day,time(8),tzinfo=tz)
    closing=datetime.combine(day,time(18),tzinfo=tz)
    duration=timedelta(minutes=r.duration_minutes)
    results=[]
    for dock in docks:
        if dock.dock_type != r.dock_type: continue
        busy=merge_intervals([(b.start_at.astimezone(tz),b.end_at.astimezone(tz)) for b in bookings if b.dock_id==dock.dock_id and b.start_at < closing and b.end_at > opening])
        cursor=max(opening,r.earliest_start)
        for start,end in busy:
            if cursor+duration <= start: break
            if cursor < end: cursor=end
        if cursor+duration <= closing: results.append((cursor,dock.dock_id,cursor+duration))
    if not results: return {"status":"no_slot","reason":"Không có cửa phù hợp trong ngày"}
    start,dock_id,end=min(results,key=lambda v:(v[0],v[1]))
    return {"status":"available","dock_id":dock_id,"start_at":start,"end_at":end,"reason":"Giờ bắt đầu sớm nhất; hòa thì chọn mã cửa theo alphabet"}
