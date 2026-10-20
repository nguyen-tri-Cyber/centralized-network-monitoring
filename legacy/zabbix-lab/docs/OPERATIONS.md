# Hướng dẫn vận hành và xử lý lỗi

## Hằng ngày

1. Mở Docker Desktop; chạy `docker compose up -d` trong thư mục dự án.
2. Chạy `py -3.12 .\a1.py verify`. Tệp `output/verify-*.json` cho biết item nào thiếu hoặc cũ.
3. Trong Zabbix xem Dashboards, Monitoring → Latest data, Monitoring → Problems.
4. Trong Mailpit xem email problem/recovery. Mailpit chỉ là hộp thư thử nghiệm.
5. Khi cần số liệu cho báo cáo, chạy `py -3.12 .\a1.py report --hours 24`. Mở `output/operations-*.md` để đọc thống kê và CSV cùng tên để kiểm tra từng mẫu gốc.
6. Sau khi chạy các test riêng lẻ, dùng `py -3.12 .\a1.py summarize` để có bảng TC01–TC12 từ các bằng chứng mới nhất.
7. Dừng bằng `docker compose down` để giữ volume DB.

## Tài khoản và quyền

`Admin` cấu hình host, action và người dùng. `a1-operator` có quyền đọc/ghi host group A1 để xử lý sự cố; `a1-viewer` chỉ đọc nhóm A1 và không được sửa cấu hình. Mật khẩu demo và Admin sau xoay vòng nằm trong `local-accounts.json`, bị `.gitignore` loại. Không đăng tệp này, `.env`, backup hoặc output chứa địa chỉ nội bộ lên Git/công khai.

Chạy `py -3.12 .\a1.py secure-admin` sau provision. Tài khoản mặc định bị thay bằng mật khẩu ngẫu nhiên; phiên Zabbix đang mở có thể yêu cầu đăng nhập lại. Không dùng tài khoản demo trên mạng thật.

## Sao lưu và khôi phục

1. `powershell -File .\backup.ps1` tạo thư mục `backups/<timestamp>` có dump, `.env`, tài khoản và manifest hash.
2. `powershell -File .\verify-backup.ps1 -BackupDir .\backups\<timestamp>` khôi phục vào database tạm, xác nhận 3 host rồi dọn database tạm.
3. Khi cần phục hồi database lab hiện tại, dùng `powershell -File .\restore.ps1 -BackupDir .\backups\<timestamp> -ConfirmRestore`.
4. Sau đó chạy `py -3.12 .\a1.py verify`. Trên máy mới, sao chép `.env` từ backup vào thư mục dự án trước khi khởi động Compose. Giữ backup ở nơi chỉ bạn truy cập.

## Lỗi thường gặp

| Hiện tượng | Kiểm tra và cách xử lý |
|---|---|
| Không mở được Zabbix | `docker compose ps`, `docker compose logs --tail=100 web zabbix-server db`; chờ DB/web healthy. |
| Agent không có dữ liệu | Kiểm tra `lab-agent` running, host name `lab-linux-agent`, template và `docker compose logs lab-agent`. |
| SNMP unsupported | Kiểm tra `lab-snmp` và `.env` community; chạy lại `a1.py provision` để cập nhật macro. |
| Không có email | Kiểm tra media `A1 Lab Mailpit`, user `a1-operator`, action `A1 Lab - Email su co`, `Reports → Action log` và Mailpit. |
| TC06 không đạt | `docker compose exec -T lab-endpoint tc qdisc show dev eth0`; bảo đảm `NET_ADMIN` và chờ đủ hai mẫu ICMP 1 phút. |
| Trùng cổng 8080/8025 | Đóng ứng dụng dùng cổng hoặc đổi binding localhost trong `compose.yaml`. |
| Docker không chạy | Mở Docker Desktop và kiểm tra `docker info`; không xóa volume khi xử lý. |

## Điều kiện an toàn lab

Chỉ chạy `a1.py test` khi đây là Compose project lab ở thư mục này. Lệnh gây lỗi chỉ dừng endpoint, tạo traffic, ghi tệp trong container, áp độ trễ và restart Zabbix Server lab. `restore.ps1` thay database nên có cờ xác nhận riêng. Không dùng các lệnh này trên thiết bị LIC/sản xuất.
