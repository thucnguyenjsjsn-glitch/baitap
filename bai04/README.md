# Bài 04 — Xếp công việc theo thứ tự trước–sau

Dự án FastAPI độc lập, bám theo trang 8 của đề **Structured Output và thuật toán**. AI trích xuất `tasks` và `dependencies` từ biên bản họp; **code Python** kiểm tra dữ liệu và dùng **Topological Sort (Kahn + min-heap)** để xếp thứ tự. Không sử dụng chức năng ticket, booking hoặc expenses của các bài trước.

## Công nghệ

Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy, PostgreSQL (có thể dùng Supabase), LangChain `ChatOpenAI` + `with_structured_output`, HTML/JS, pytest.

## Cài đặt trên Windows

```powershell
cd bai04_fastapi
py -m venv myenv
.\myenv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Mở `.env`, thay `DATABASE_URL` bằng URL PostgreSQL thực tế lấy trong **Supabase → Connect**. Không để dấu `...` hoặc mật khẩu mẫu. Nếu dùng Supabase, URL thường cần SSL (`?sslmode=require`). Mật khẩu có ký tự đặc biệt phải URL-encode. Không đưa `.env` lên GitHub.

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres?sslmode=require
AI_MODE=mock
OPENAI_MODEL=gpt-5-mini
OPENAI_API_KEY=
```

`AI_MODE=mock` dùng dữ liệu ví dụ cố định của đề, **không đọc hiểu văn bản thực tế** (ngoại trừ khi nội dung nhập là JSON đúng schema). Để chạy AI thật, đặt `AI_MODE=openai` và điền `OPENAI_API_KEY` hợp lệ. API key chỉ nằm tại backend.

```powershell
uvicorn app.main:app --reload
```

Mở **http://127.0.0.1:8000/** (giao diện) hoặc **http://127.0.0.1:8000/docs** (Swagger). Lúc khởi động, SQLAlchemy tạo bảng `plans` nếu chưa có; cần database hoạt động.

## Cấu trúc

```text
bai04_fastapi/
├── app/
│   ├── main.py                 # Khởi tạo FastAPI, DB và static
│   ├── config.py               # .env
│   ├── database.py             # SQLAlchemy engine/session
│   ├── dependencies.py         # Cung cấp DB session cho router
│   ├── plan_models.py          # Bảng plans
│   ├── plan_schemas.py         # Pydantic request/response
│   ├── plan_ai_service.py      # OpenAI Structured Output / mock
│   ├── plan_service.py         # Validation, topological sort, cycle
│   ├── routers/plans.py        # Ba API bắt buộc
│   └── static/index.html       # Giao diện nhập/sửa/xem kết quả
├── tests/test_plan_service.py
├── requirements.txt
├── .env.example
└── README.md
```

## API

| Method | Endpoint | Công dụng |
|---|---|---|
| POST | `/plans/extract` | Trích xuất JSON từ biên bản |
| POST | `/plans/validate` | Kiểm tra ID, quan hệ, trùng ID, tự phụ thuộc; quan hệ lặp chỉ tính một lần |
| POST | `/plans/order` | Xếp thứ tự hoặc báo vòng; có thể lưu vào PostgreSQL |

### 1. POST /plans/extract

```json
{"text":"Chốt API và duyệt UI trước khi tích hợp frontend. Kiểm thử sau khi tích hợp."}
```

Trong `mock`, trả dữ liệu mẫu:

```json
{
  "extracted": {
    "tasks": [
      {"id":"A","title":"Chốt yêu cầu API","owner":"Product"},
      {"id":"B","title":"Duyệt thiết kế UI","owner":"Design"},
      {"id":"C","title":"Tích hợp frontend","owner":"Engineering"},
      {"id":"D","title":"Kiểm thử end-to-end","owner":"QA"}
    ],
    "dependencies": [
      {"before":"A","after":"C","evidence":"Sau khi chốt API mới tích hợp frontend"},
      {"before":"B","after":"C","evidence":"Duyệt UI trước khi tích hợp"},
      {"before":"C","after":"D","evidence":"Kiểm thử sau khi tích hợp"}
    ]
  }
}
```

### 2. POST /plans/validate

Dán toàn bộ `extracted` của API trước vào:

```json
{"extracted":{"tasks":[{"id":"A","title":"Việc A","owner":null},{"id":"B","title":"Việc B","owner":null}],"dependencies":[{"before":"A","after":"B","evidence":"A trước B"}]}}
```

Trả `valid=true` và số lượng công việc, quan hệ. Nếu ID lạ, ID trùng hoặc tự phụ thuộc, trả HTTP 422. **Vòng phụ thuộc được phát hiện ở API `/plans/order`**.

### 3. POST /plans/order

```json
{
  "original_text":"Sau khi A xong mới làm B",
  "extracted": {
    "tasks":[{"id":"A","title":"Việc A","owner":null},{"id":"B","title":"Việc B","owner":null}],
    "dependencies":[{"before":"A","after":"B","evidence":"A trước B"}]
  },
  "save":true
}
```

Trả `status=ordered`, `order=["A","B"]`, `cycle=[]` và `plan_id` nếu lưu. Có thể gửi thêm `ai_extracted` (bản AI chưa sửa) để lưu riêng bản AI và bản người dùng sửa. Khi không gửi `ai_extracted`, backend dùng `extracted` cho cả hai bản. Đặt `save=false` để chỉ chạy thuật toán mà không ghi database.

Nếu thêm quan hệ `D → A` vào ví dụ A → C → D, trả `status=cycle_detected`, `order=null`, và `cycle` là một vòng tìm được. Không hiển thị thứ tự chưa hoàn chỉnh.

## Kiểm thử

```powershell
python -m pytest -q
```

Các trường hợp: ví dụ A→B→C→D; đảo thứ tự task vẫn ra kết quả ổn định; vòng A→C→D→A; ID lạ; tự phụ thuộc; ID trùng; quan hệ lặp; không có quan hệ; danh sách rỗng.

## Kiểm tra Supabase

```sql
SELECT id, original_text, ai_json, confirmed_json, status, result_json, processed_at
FROM plans
ORDER BY id DESC;
```

## Phân chia trách nhiệm

- **GenAI:** đọc biên bản, trích xuất `tasks`, `dependencies`, `owner`, `evidence`. Không tự tạo quan hệ không có bằng chứng.
- **Pydantic/backend:** kiểm tra kiểu dữ liệu, ID lạ/trùng, tự phụ thuộc; loại bỏ quan hệ lặp khi tính.
- **Thuật toán:** Kahn + min-heap ưu tiên ID alphabet, tìm vòng nếu không thể xếp hết. Thời gian `O((V+E) log V)` trong trường hợp tổng quát với heap; vòng tìm bằng DFS `O(V+E)` (không kể chi phí sắp xếp danh sách kề để có kết quả ổn định).
- **Người dùng:** sửa JSON và xác nhận trước khi xem thứ tự. Không tự biến thứ tự thành lịch ngày/giờ.

Chỉ sử dụng dữ liệu giả để thực hành. Khi nộp bài, bổ sung ảnh/video luồng chính theo đề.
