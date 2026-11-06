from datetime import datetime
from sqlalchemy import select
from app.config import get_settings
from app.database import Base,make_session_factory
from app.dock_models import Dock,Booking

engine,factory=make_session_factory(get_settings().database_url)
Base.metadata.create_all(engine)
with factory() as db:
    for name in ('A','B'):
        if db.get(Dock,name) is None: db.add(Dock(dock_id=name,dock_type='standard'))
    db.commit()
    examples=[('DEMO-A1','A','09:00','10:00'),('DEMO-A2','A','10:00','11:00'),('DEMO-B1','B','09:30','10:15')]
    for rid,dock,start,end in examples:
        if db.get(Booking,rid): continue
        db.add(Booking(request_id=rid,dock_id=dock,start_at=datetime.fromisoformat('2026-10-21T'+start+':00+07:00'),end_at=datetime.fromisoformat('2026-10-21T'+end+':00+07:00'),duration_minutes=int((datetime.fromisoformat("2026-10-21T"+end+":00+07:00")-datetime.fromisoformat("2026-10-21T"+start+":00+07:00")).total_seconds()//60),original_email='Dữ liệu mẫu',ai_json={},confirmed_json={},confirmed_at=datetime.now().astimezone()))
    db.commit()
print('Đã tạo cửa A, B và lịch mẫu; chạy lại an toàn, không tạo trùng.')
