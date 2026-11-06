# Bài 02 — Dock Scheduling: Tìm giờ nhận xe tại kho

Ứng dụng FastAPI trích xuất email đăng ký nhận hàng, tìm cửa kho phù hợp có giờ trống sớm nhất và lưu booking vào PostgreSQL. Có giao diện tại `/`, Swagger tại `/docs` và dữ liệu seed cho ví dụ của đề.

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

## Tạo dữ liệu cửa kho mẫu

Chạy **một lần sau khi cấu hình database**, trước khi kiểm thử gợi ý khung giờ:

```powershell
python seed_docks.py
```

Script tạo hai cửa thường `A`, `B` và các booking ngày 21/10/2026: A bận `09:00–10:00`, `10:00–11:00`; B bận `09:30–10:15`. Script kiểm tra ID đã tồn tại nên có thể chạy lại mà không thêm bản trùng.

## Quy trình sử dụng

1. Nhập `request_id` và email nhà vận chuyển; gọi `POST /requests/extract`.
2. Xem/sửa thông tin AI đọc ra, nhất là `earliest_start`, `duration_minutes`, `dock_type`.
3. Gọi `POST /slots/suggest` để nhận cửa và khung giờ còn trống.
4. Gọi `POST /bookings/confirm` để xác nhận. Backend **kiểm tra xung đột lần nữa** trên dữ liệu mới nhất trước khi lưu.
5. Gọi `GET /docks/schedule` để xem lịch từng cửa.

## Quy tắc thuật toán

- Chỉ xét cửa đúng loại: `standard` hoặc `refrigerated`.
- Gộp lịch chồng nhau hoặc nối sát nhau; giờ hoạt động `08:00–18:00`.
- Chọn giờ bắt đầu sớm nhất; nếu bằng nhau chọn `dock_id` theo alphabet.
- Khoảng giờ dùng quy tắc `[start, end)`: kết thúc lúc `10:00` và bắt đầu lúc `10:00` không xung đột.
- Không còn giờ trong ngày → `status: no_slot`; không tự chuyển ngày.
- `POST /bookings/confirm` dùng PostgreSQL advisory transaction lock để tuần tự hóa xác nhận, trả 409 khi trùng ID hoặc xung đột giờ.

## API chính

| Method | Endpoint | Ý nghĩa |
| --- | --- | --- |
| `POST` | `/requests/extract` | Trích xuất email thành schema |
| `POST` | `/slots/suggest` | Tìm giờ/cửa phù hợp |
| `POST` | `/bookings/confirm` | Xác nhận booking; HTTP 201 |
| `GET` | `/docks/schedule` | Xem lịch các cửa kho |

## Ví dụ kiểm thử qua Swagger

**1.** `POST /requests/extract` (ví dụ mock nhận thời gian và thời lượng theo mẫu):

```json
{
  "request_id": "R01",
  "email": "Xe giao hàng đến từ 2026-10-21T09:00:00+07:00, cần 60 phút, cửa thường."
}
```

Trong chế độ `mock`, `carrier` có thể là `null` vì code mock chưa trích xuất tên nhà vận chuyển; có thể bổ sung thủ công trước khi gợi ý.

**2.** `POST /slots/suggest`:

```json
{
  "extracted": {
    "request_id": "R01",
    "carrier": "ACME Logistics",
    "earliest_start": "2026-10-21T09:00:00+07:00",
    "duration_minutes": 60,
    "dock_type": "standard",
    "missing_fields": []
  }
}
```

Với lịch seed, kết quả phải là `status: available`, `dock_id: B`, `start_at: 2026-10-21T10:15:00+07:00`, `end_at: 2026-10-21T11:15:00+07:00`.

**3.** `POST /bookings/confirm`:

```json
{
  "email": "Xe ACME cần nhận hàng lúc 09:00, thời lượng 60 phút.",
  "extracted": {
    "request_id": "R01",
    "carrier": "ACME Logistics",
    "earliest_start": "2026-10-21T09:00:00+07:00",
    "duration_minutes": 60,
    "dock_type": "standard",
    "missing_fields": []
  },
  "dock_id": "B",
  "start_at": "2026-10-21T10:15:00+07:00",
  "end_at": "2026-10-21T11:15:00+07:00"
}
```

Xác nhận thành công trả 201; sau đó `GET /docks/schedule` thấy R01. Nếu thử lại cùng ID hoặc đặt chồng lịch → 409. Nếu đã chạy ví dụ này, dữ liệu database sẽ thay đổi kết quả gợi ý tiếp theo.

**4.** Test lỗi: thiếu `duration_minutes`, thời gian không có timezone, thời lượng không khớp, ngoài giờ làm việc → 422; hết chỗ → `no_slot`.

## Dữ liệu Structured Output

```json
{
  "request_id": "R01",
  "carrier": "ACME Logistics",
  "earliest_start": "2026-10-21T09:00:00+07:00",
  "duration_minutes": 60,
  "dock_type": "standard",
  "missing_fields": []
}
```

Trường chưa rõ để `null`, thêm tên vào `missing_fields`. `duration_minutes` phải lớn hơn 0.

## Cấu trúc code

```text
app/
  main.py                 # Khởi tạo app và bảng
  config.py               # Cấu hình môi trường
  database.py             # PostgreSQL SQLAlchemy session
  dependencies.py         # Dependency lấy DB session
  dock_models.py          # Bảng Dock và Booking
  dock_schemas.py         # Pydantic schema
  dock_ai_service.py      # Mock/OpenAI trích xuất email
  dock_service.py         # Gộp khoảng bận và tìm slot
  routers/docks.py        # API lịch cửa kho
  static/dock.html        # Giao diện thử nghiệm
seed_docks.py             # Tạo cửa và lịch mẫu
tests/test_dock_service.py
requirements.txt
.env.example
```

## Unit test

Chạy `python -m pytest -q`. Các test trong `tests/test_dock_service.py` kiểm tra kết quả cửa B lúc 10:15, gộp lịch nối sát, ranh giới không trùng, hết slot và dữ liệu thời gian sai. Unit test không cần gọi OpenAI.

## Phân chia trách nhiệm AI và thuật toán

**GenAI** trích xuất các trường từ văn bản vào schema Pydantic. **Code backend** kiểm tra dữ liệu, áp dụng quy tắc nghiệp vụ, tính kết quả và ghi database. Kết quả AI không được coi là quyết định cuối cùng khi chưa được xác nhận.

## Phạm vi triển khai

Đây là dự án thực hành với dữ liệu giả. Chưa nên dùng trực tiếp với dữ liệu cá nhân hoặc chứng từ thật. Trước khi triển khai thực tế cần bổ sung xác thực/phân quyền, migration database, kiểm thử tích hợp, giám sát lỗi và quản lý khóa bí mật.
