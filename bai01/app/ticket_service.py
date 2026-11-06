import heapq
from datetime import datetime, timedelta
from app.schemas import ExtractedTicket

SLA_MINUTES = {"critical": 30, "high": 120, "medium": 480, "low": 1440}
RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}

def deadline(received_at: datetime, severity: str) -> datetime:
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise ValueError("Thời điểm nhận phải có múi giờ")
    if severity not in SLA_MINUTES:
        raise ValueError("Mức khẩn cấp không hợp lệ")
    return received_at + timedelta(minutes=SLA_MINUTES[severity])

def priority_key(item: dict):
    return (item["deadline_at"], -RANK[item["severity"]], item["received_at"], item["ticket_id"])

def top_k(items: list[dict], limit: int) -> list[dict]:
    return heapq.nsmallest(limit, items, key=priority_key)

def reason(item: dict) -> str:
    return (f"Hạn {item['deadline_at'].isoformat()}; mức {item['severity']} "
            f"(hạng {RANK[item['severity']]}); nhận {item['received_at'].isoformat()}; "
            f"mã {item['ticket_id']}. Xếp theo hạn, độ khẩn cấp, thời điểm nhận, mã.")
