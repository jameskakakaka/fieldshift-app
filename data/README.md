# Thư mục data

Chép vào đây 2 file do notebook `FieldShift_Train_DrySeason_Model.ipynb` sinh ra (tải từ thanh Files của Colab):

- `forecast_DBSCL.csv`
- `forecast_TAYNGUYEN.csv`

Mỗi file có các cột `cell, lat, lon, p_kho_han`. App lấy ô gần ruộng nhất để hiển thị xác suất mùa khô khắc nghiệt.
Chưa có file thì app vẫn chạy, dùng tỷ lệ lịch sử 33%.

Thư mục `power_cache/` được app tự tạo để lưu dữ liệu NASA POWER đã tải. Nên chạy app một lần cho các địa điểm sẽ demo
khi có mạng, để lúc trình bày mất mạng vẫn chạy được.
