from datetime import datetime
from types import SimpleNamespace
from fastapi import HTTPException
import pytest
from app.dock_schemas import DockExtracted
from app.dock_service import suggest,merge_intervals

def dt(s):return datetime.fromisoformat('2026-10-21T'+s+':00+07:00')
def dock(name):return SimpleNamespace(dock_id=name,dock_type='standard')
def booking(name,start,end):return SimpleNamespace(dock_id=name,start_at=dt(start),end_at=dt(end))
def request(start='09:00',duration=60):return DockExtracted(request_id='R01',earliest_start=dt(start),duration_minutes=duration,dock_type='standard')
def test_example():
    result=suggest(request(),[dock('A'),dock('B')],[booking('A','09:00','10:00'),booking('A','10:00','11:00'),booking('B','09:30','10:15')]);assert result['dock_id']=='B' and result['start_at']==dt('10:15') and result['end_at']==dt('11:15')
def test_touching_intervals_and_boundary():
    assert merge_intervals([(dt('09:00'),dt('10:00')),(dt('10:00'),dt('11:00'))])==[(dt('09:00'),dt('11:00'))]
    assert suggest(request('10:00'),[dock('A')],[booking('A','09:00','10:00')])['start_at']==dt('10:00')
def test_no_slot():
    assert suggest(request('17:30'),[dock('A')],[])['status']=='no_slot'
def test_invalid():
    with pytest.raises(ValueError): request(duration=0)
    with pytest.raises(ValueError): DockExtracted(request_id='R01',earliest_start=datetime(2026,10,21,9),duration_minutes=60,dock_type='standard')
