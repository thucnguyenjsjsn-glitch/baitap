from datetime import datetime, timedelta, timezone
import pytest
from app.ticket_service import deadline, top_k

TZ = timezone(timedelta(hours=7))
def ticket(tid, hour, minute, severity):
    received = datetime(2026, 10, 21, hour, minute, tzinfo=TZ)
    return {"ticket_id": tid, "received_at": received, "severity": severity,
            "deadline_at": deadline(received, severity)}

def test_sample_and_non_destructive_top_k():
    items = [ticket("T01",9,0,"high"), ticket("T02",9,20,"critical"), ticket("T03",8,30,"medium")]
    assert [x['ticket_id'] for x in top_k(items,2)] == ["T02","T01"]
    assert len(items) == 3
    assert [x['ticket_id'] for x in top_k(items,3)] == ["T02","T01","T03"]

def test_boundary_tie_received_and_id():
    a = ticket("B",9,0,"high")
    b = ticket("A",9,0,"high")
    assert [x['ticket_id'] for x in top_k([a,b],2)] == ["A","B"]
    assert deadline(a['received_at'], 'high') == datetime(2026,10,21,11,0,tzinfo=TZ)

def test_invalid_severity_and_timezone():
    with pytest.raises(ValueError): deadline(datetime(2026,10,21,9), 'high')
    with pytest.raises(ValueError): deadline(datetime(2026,10,21,9,tzinfo=TZ), 'urgent')

def test_t04_first():
    items = [ticket("T01",9,0,"high"),ticket("T02",9,20,"critical"),ticket("T03",8,30,"medium"),ticket("T04",7,0,"high")]
    assert top_k(items,1)[0]['ticket_id'] == 'T04'
