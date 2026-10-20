# A1 Monitoring Lab — đặc tả sản phẩm

## Mục tiêu

Tái tạo được một hệ thống giám sát mạng tập trung hoàn chỉnh trong Docker trên máy cá nhân, dùng Zabbix 7.4, PostgreSQL và Mailpit. Không truy cập hoặc mô tả dữ liệu LIC thật.

## Phạm vi và điều kiện đạt

| Năng lực | Điều kiện kiểm chứng |
|---|---|
| Thu thập | 3 host lab ICMP, SNMP, Linux Agent; có ping/loss/RTT, interface octets, CPU/RAM/disk. |
| Hiển thị | Dashboard A1 Lab có trạng thái host, sự cố và chỉ số quan trọng; Zabbix lưu lịch sử và biểu đồ. |
| Cảnh báo | Trigger tạo sự cố/phục hồi; action chỉ áp dụng cho A1 Lab, email vào Mailpit. |
| Quyền | Quản trị dùng Admin; operator và viewer có tài khoản riêng, viewer không sửa cấu hình. |
| Mở rộng lab | Có hai zone, sơ đồ ba host logic và xuất báo cáo theo cửa sổ cùng CSV mẫu gốc. |
| Kiểm thử | TC01–TC12 có lệnh hoặc hướng dẫn, expected, actual, timestamp, evidence và trạng thái; thiếu dữ liệu phải ghi SKIP, không tự nhận PASS. |
| Vận hành | Có lệnh chạy, kiểm tra, sao lưu, khôi phục và xử lý lỗi; bí mật chỉ lưu trong tệp bị Git bỏ qua. |

## Công nghệ và lệnh

- Docker Compose, Zabbix 7.4, PostgreSQL 16, Mailpit, SNMP và Python 3.12 (chỉ thư viện chuẩn).
- Cài/chạy: `powershell -File .\setup.ps1 -Start`
- Tạo cấu hình: `py -3.12 .\a1.py provision`
- Kiểm tra: `py -3.12 .\a1.py verify`
- Kiểm thử: `py -3.12 .\a1.py test --case TC03`
- Tổng hợp: `py -3.12 .\a1.py summarize`
- Báo cáo vận hành: `py -3.12 .\a1.py report --hours 24`
- Unit test: `py -3.12 -m unittest discover -s tests -v`
- Sao lưu: `powershell -File .\backup.ps1`

## Cấu trúc

- `compose.yaml`, `lab-snmp/`: hạ tầng lab.
- `a1.py`, `a1lab/`: mã nguồn cấu hình, kiểm tra, đo và tạo báo cáo.
- `tests/`: kiểm thử logic độc lập với Docker.
- `docs/`: kiến trúc, vận hành, ma trận test và mẫu báo cáo.
- `output/`: minh chứng sinh khi chạy, không commit.

## Quy tắc mã và dữ liệu

Python 3.12, kiểu dữ liệu rõ, tên hàm `snake_case`, mỗi lệnh trả mã lỗi khác 0 khi điều kiện bắt buộc không đạt. API call không ghi password/token vào log. Tệp `.env`, tài khoản demo, backup và output không đưa vào Git. Mọi thử nghiệm gây gián đoạn chỉ nhắm container lab.

## Giới hạn

Agent hiện chạy trong container nên số liệu tài nguyên phản ánh môi trường container/host Docker, không đại diện máy chủ LIC. Mailpit nhận thư nội bộ, không gửi Internet. Không thể tự tạo kết quả cho giai đoạn quan sát dài ngày hoặc chứng nhận nghiệm thu của giảng viên/LIC.
