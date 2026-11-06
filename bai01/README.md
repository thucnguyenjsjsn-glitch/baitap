# Bài 01 — Ticket Priority: Ưu tiên yêu cầu khách hàng

Ứng dụng FastAPI đọc tin nhắn khách hàng, trích xuất thông tin ticket bằng Structured Output và sắp xếp thứ tự xử lý theo hạn SLA. Giao diện thử nghiệm nằm tại `/`; trọng tâm là backend, thuật toán ưu tiên và lưu PostgreSQL.

## Chạy nhanh trên Windows

Yêu cầu: Python 3.11+ và PostgreSQL đang hoạt động (có thể dùng Supabase).

Mở terminal tại **thư mục chứa `requirements.txt`** của bài tương ứng:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Sửa `.env` theo database của bạn. Sau đó:

```powershell
uvicorn app.main:app --reload
```

- Giao diện: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs
- Chạy unit test: `python -m pytest -q`

Nếu PowerShell không cho kích hoạt môi trường, có thể chạy `cmd` và dùng `.venv\Scripts\activate.bat`.

## Cấu hình PostgreSQL/Supabase và OpenAI

Các dự án sử dụng SQLAlchemy + `psycopg` với PostgreSQL. Sao chép chuỗi kết nối **thực tế** từ Supabase Dashboard → Connect hoặc dùng PostgreSQL cục bộ:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB_NAME
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
AI_MODE=mock
```

`DATABASE_URL` cũng chấp nhận tiền tố `postgresql://` và được code chuyển sang driver `psycopg`. Với Supabase, lấy host, user, port đúng theo kiểu kết nối được cung cấp; thêm `?sslmode=require` khi cần. Không đưa `.env` hoặc API key lên GitHub.

- `AI_MODE=mock`: chế độ mô phỏng, không gọi OpenAI; phù hợp kiểm thử.
- `AI_MODE=openai`: dùng `langchain_openai.ChatOpenAI` và `with_structured_output(..., method="json_schema")`; phải có `OPENAI_API_KEY` hợp lệ.
- Model mặc định trong source: `gpt-5-mini`.

Ứng dụng tạo các bảng còn thiếu qua `Base.metadata.create_all()` khi khởi động. Lệnh này **không** tạo database PostgreSQL mới và **không** thay thế migration schema.

## Quy trình sử dụng

1. Nhập `ticket_id`, `received_at` (ISO 8601 **có múi giờ**) và tin nhắn.
2. Gọi **Extract** (`POST /tickets/extract`); kiểm tra `intent`, `severity`, `summary`, `needs_human_review` và hạn xử lý.
3. Sửa thông tin trích xuất nếu cần rồi **Confirm** (`POST /tickets/confirm`) để lưu ticket vào hàng đợi.
4. Xem **Queue** (`GET /tickets/queue?limit=...`) để lấy top K mà không xóa ticket.
5. Gọi **Next** (`POST /tickets/next`) để lấy và loại ticket ưu tiên nhất khỏi hàng đợi chờ.

## Quy tắc ưu tiên

| Severity | SLA | Hạng |
| --- | --- | --- |
| `critical` | 30 phút | 4 |
| `high` | 2 giờ | 3 |
| `medium` | 8 giờ | 2 |
| `low` | 24 giờ | 1 |

Khóa ưu tiên: `(deadline_at, -severity_rank, received_at, ticket_id)`. Khi cùng hạn, ưu tiên severity cao hơn, rồi thời gian nhận sớm hơn, rồi ID theo alphabet. Code dùng `heapq` trong `ticket_service.py` để lấy top K; danh sách ticket chờ được đọc từ database.

## API chính

| Method | Endpoint | Ý nghĩa |
| --- | --- | --- |
| `POST` | `/tickets/extract` | Trích xuất ticket và tính deadline |
| `POST` | `/tickets/confirm` | Kiểm tra và lưu ticket; HTTP 201 |
| `GET` | `/tickets/queue?limit=10` | Xem top K (1–100), không xóa |
| `POST` | `/tickets/next` | Lấy ticket kế tiếp |

## Ví dụ kiểm thử qua Swagger

**1.** `POST /tickets/extract`:

```json
{
  "ticket_id": "T01",
  "received_at": "2026-10-21T09:00:00+07:00",
  "message": "Tôi bị trừ tiền hai lần khi thanh toán."
}
```

Trong chế độ `mock`, đoạn này được nhận dạng là `billing`, `high`, deadline `11:00`.

**2.** `POST /tickets/confirm` (dùng bản `extracted` nhận từ bước trước, có thể sửa):

```json
{
  "ticket_id": "T01",
  "received_at": "2026-10-21T09:00:00+07:00",
  "message": "Tôi bị trừ tiền hai lần khi thanh toán.",
  "extracted": {
    "ticket_id": "T01",
    "intent": "billing",
    "severity": "high",
    "product": null,
    "summary": "Tôi bị trừ tiền hai lần khi thanh toán.",
    "needs_human_review": false
  }
}
```

**3.** Thêm `T02` mức `critical` nhận `09:20`, `T03` mức `medium` nhận `08:30` (có thể dùng bản `extracted` tự xác nhận). `GET /tickets/queue?limit=2` phải có thứ tự `T02`, `T01`; `POST /tickets/next` lấy `T02`. Nếu gọi `GET` trước, thứ tự `Next` không đổi.

**4.** Test lỗi: `ticket_id` trùng → 409; `severity` không hợp lệ, ID trích xuất không khớp hoặc `received_at` thiếu múi giờ → 422.

## Dữ liệu Structured Output

```json
{
  "ticket_id": "T01",
  "intent": "billing",
  "severity": "high",
  "product": null,
  "summary": "Khách bị tính tiền hai lần",
  "needs_human_review": false
}
```

`intent` chỉ nhận `billing`, `technical`, `account`, `other`; `severity` chỉ nhận `low`, `medium`, `high`, `critical`; `summary` tối đa 200 ký tự.

## Cấu trúc code

```text
app/
  main.py                 # Khởi tạo FastAPI, bảng và trang chủ
  config.py               # Đọc .env
  database.py             # SQLAlchemy engine và session
  dependencies.py         # Dependency lấy DB session
  models.py               # Bảng Ticket
  schemas.py              # Pydantic request/response
  ai_service.py           # Mock hoặc OpenAI Structured Output
  ticket_service.py       # SLA, heap ưu tiên, lý do xếp hạng
  ticket_repository.py    # Truy vấn và cập nhật ticket trong DB
  routers/tickets.py      # 4 API ticket
  static/index.html       # Giao diện thử nghiệm
tests/test_priority.py    # Unit test thuật toán
requirements.txt
.env.example
```

## Unit test

Chạy `python -m pytest -q`. File `tests/test_priority.py` kiểm tra ví dụ chuẩn, top K không phá hàng đợi, tie-break theo thời gian/ID, severity hoặc timezone sai và trường hợp T04 được ưu tiên đầu.

## Phân chia trách nhiệm AI và thuật toán

**GenAI** trích xuất các trường từ văn bản vào schema Pydantic. **Code backend** kiểm tra dữ liệu, áp dụng quy tắc nghiệp vụ, tính kết quả và ghi database. Kết quả AI không được coi là quyết định cuối cùng khi chưa được xác nhận.

## Phạm vi triển khai

Đây là dự án thực hành với dữ liệu giả. Chưa nên dùng trực tiếp với dữ liệu cá nhân hoặc chứng từ thật. Trước khi triển khai thực tế cần bổ sung xác thực/phân quyền, migration database, kiểm thử tích hợp, giám sát lỗi và quản lý khóa bí mật.
