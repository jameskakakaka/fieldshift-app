# FieldShift – App trợ lý luân canh

App Streamlit cho nông dân: xem dự báo mùa khô và nhận gợi ý luân canh, dựa trên dữ liệu NASA POWER.

## Cấu trúc

```
app.py            giao diện 3 tab: Dự báo khí hậu, Tư vấn luân canh, Về dữ liệu
engine.py         danh mục luân canh và cách chấm điểm (không phụ thuộc Streamlit)
power_client.py   tải NASA POWER, lưu cache, tính chỉ số khí hậu
data/             đặt forecast_*.csv từ notebook train model vào đây
.streamlit/       màu sắc giao diện
```

## Chạy trên máy

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
streamlit run app.py
```

Trình duyệt tự mở ở http://localhost:8501. Lần đầu chọn một địa điểm, app tải khoảng 35 năm dữ liệu (10–30 giây),
các lần sau đọc từ cache.

## Đưa lên mạng để có link nộp bài (miễn phí)

1. Đẩy thư mục này lên repo GitHub public (ví dụ vào `app/` của repo `fieldshift`).
2. Vào https://share.streamlit.io, đăng nhập bằng GitHub, chọn **Create app**.
3. Chọn repo, nhánh `main`, đường dẫn file chính `app/app.py`, bấm **Deploy**.

## Nguồn

- NASA POWER (CC BY 4.0) – dữ liệu khí hậu ngày.
- NOAA CPC ONI – chỉ số El Niño (dùng trong notebook train model).
- Su et al. (2026), *Crop Rotation for Sustainable Agriculture*, Applied Sciences 16(13):6511.
- Có sử dụng AI (Claude) để hỗ trợ viết code: ghi vào mục "Use of AI" khi nộp bài.
