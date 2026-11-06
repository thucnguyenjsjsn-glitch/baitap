# Bài 03 — Expense Duplicate Review: Rà soát hóa đơn gửi trùng

Ứng dụng FastAPI nhận văn bản hóa đơn (đã OCR hoặc nhập tay), dùng Structured Output để trích xuất thông tin và tìm chứng từ nghi trùng theo các khóa tra cứu. Người duyệt có thể xác nhận nghi vấn, bỏ nghi vấn hoặc chuyển kiểm tra thủ công. Hệ thống **không tự kết luận gian lận**.

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

1. Nhập `submission_id` và **văn bản hóa đơn** vào `POST /expenses/extract`.
2. Xem và sửa các trường GenAI trích xuất (`vendor`, `invoice_number`, `receipt_id`, `amount_minor`...).
3. Gọi `POST /expenses/check` để kiểm tra khóa trùng với các chứng từ đã lưu.
4. Xem `status`, `matches`, `matched_by` và các trường khác biệt trong `differences`.
5. Gọi `POST /expenses/review` với quyết định của người duyệt để lưu văn bản gốc, JSON AI, JSON đã xác nhận và kết quả rà soát.

**Lưu ý về OCR:** Source hiện nhận `text` đã OCR/nhập tay; chưa có endpoint upload ảnh/PDF hoặc OCR tự động.

## Quy tắc thuật toán

Tạo tối đa hai loại khóa:

- `receipt`: `(currency, receipt_id)` nếu có mã biên nhận.
- `invoice`: `(currency, vendor, invoice_number)` nếu đủ nơi bán và số hóa đơn.

Trước khi so sánh, code chuẩn hóa Unicode NFKC, bỏ khoảng trắng thừa và không phân biệt hoa/thường. **Không xóa dấu gạch nối:** `INV-0042` và `INV0042` vẫn khác nhau.

| Trạng thái | Ý nghĩa |
| --- | --- |
| `duplicate_candidate` | Có khóa trùng; hiển thị chứng từ cũ và khác biệt |
| `needs_review` | Không đủ thông tin tạo khóa đáng tin cậy |
| `unique_under_current_rules` | Chưa thấy khóa trùng theo quy tắc hiện tại |

Code dùng dictionary làm hash map để lập chỉ mục khóa tra cứu. Tiền âm, tiền tệ ngoài `VND`/`USD`, ngày giao dịch tương lai → 422. Kết quả `unique_under_current_rules` **không** có nghĩa chứng từ chắc chắn hợp lệ.

## API chính

| Method | Endpoint | Ý nghĩa |
| --- | --- | --- |
| `POST` | `/expenses/extract` | Trích xuất thông tin hóa đơn |
| `POST` | `/expenses/check` | So sánh với chứng từ đã lưu |
| `POST` | `/expenses/review` | Lưu quyết định người duyệt; HTTP 201 |

## Ví dụ kiểm thử qua Swagger

**1.** `POST /expenses/extract` (định dạng nhãn `field: value` hỗ trợ chế độ `mock`):

```json
{
  "submission_id": "E01",
  "text": "vendor: ABC Travel\ninvoice_number: INV-0042\ntransaction_date: 2026-10-19\namount_minor: 1250000\ncurrency: VND\nreceipt_id: R-42"
}
```

**2.** `POST /expenses/check`:

```json
{
  "extracted": {
    "submission_id": "E01",
    "vendor": "ABC Travel",
    "invoice_number": "INV-0042",
    "transaction_date": "2026-10-19",
    "amount_minor": 1250000,
    "currency": "VND",
    "receipt_id": "R-42",
    "missing_fields": []
  }
}
```

Nếu database chưa có chứng từ tương ứng, kết quả là `unique_under_current_rules`.

**3.** `POST /expenses/review` để lưu E01:

```json
{
  "original_text": "vendor: ABC Travel; invoice_number: INV-0042; receipt_id: R-42",
  "extracted": {
    "submission_id": "E01",
    "vendor": "ABC Travel",
    "invoice_number": "INV-0042",
    "transaction_date": "2026-10-19",
    "amount_minor": 1250000,
    "currency": "VND",
    "receipt_id": "R-42",
    "missing_fields": []
  },
  "decision": "dismiss_suspicion",
  "note": "Chưa có khóa trùng theo quy tắc hiện tại"
}
```

**4.** Kiểm tra E02 với `vendor: " abc  travel "`, `invoice_number: "inv-0042"`, `receipt_id: "R-42"` và `submission_id: "E02"`: kết quả `duplicate_candidate`, khớp E01. Sau đó review với `decision: "confirm_suspicion"` để lưu quyết định nghi trùng.

**5.** Kiểm tra E03 chỉ có `vendor`, `amount_minor`, `currency`, không có `invoice_number` và `receipt_id`: trả `needs_review`; khi lưu phải dùng `decision: "needs_review"`.

**6.** Test lỗi: `amount_minor: -1`, `currency: "XYZ"` → 422; `submission_id` đã lưu → 409; dùng `confirm_suspicion` khi không có ứng viên trùng → 422.

## Dữ liệu Structured Output

```json
{
  "submission_id": "E01",
  "vendor": "ABC Travel",
  "invoice_number": "INV-0042",
  "transaction_date": "2026-10-19",
  "amount_minor": 1250000,
  "currency": "VND",
  "receipt_id": "R-42",
  "missing_fields": []
}
```

`amount_minor` là số nguyên đơn vị nhỏ nhất: VND tính bằng đồng, USD tính bằng cent. Trường không đọc được phải là `null` và được liệt kê trong `missing_fields`.

## Cấu trúc code

```text
app/
  main.py                  # Khởi tạo FastAPI và bảng
  config.py                # Cấu hình .env
  database.py              # SQLAlchemy PostgreSQL
  dependencies.py          # DB session dependency
  expense_models.py        # Bảng Expense
  expense_schemas.py       # Pydantic schema
  expense_ai_service.py    # Mock/OpenAI trích xuất hóa đơn
  expense_service.py       # Chuẩn hóa và kiểm tra trùng
  routers/expenses.py      # 3 API expenses
  static/expense.html      # Giao diện thử nghiệm
tests/test_expense_service.py
requirements.txt
.env.example
```

## Unit test

Chạy `python -m pytest -q`. File `tests/test_expense_service.py` kiểm tra E01/E02/E03, giữ dấu gạch nối, vẫn báo nghi trùng khi số tiền khác và từ chối tiền âm hoặc tiền tệ không hỗ trợ. Unit test không cần gọi OpenAI.

## Phân chia trách nhiệm AI và thuật toán

**GenAI** trích xuất các trường từ văn bản vào schema Pydantic. **Code backend** kiểm tra dữ liệu, áp dụng quy tắc nghiệp vụ, tính kết quả và ghi database. Kết quả AI không được coi là quyết định cuối cùng khi chưa được xác nhận.

## Phạm vi triển khai

Đây là dự án thực hành với dữ liệu giả. Chưa nên dùng trực tiếp với dữ liệu cá nhân hoặc chứng từ thật. Trước khi triển khai thực tế cần bổ sung xác thực/phân quyền, migration database, kiểm thử tích hợp, giám sát lỗi và quản lý khóa bí mật.
