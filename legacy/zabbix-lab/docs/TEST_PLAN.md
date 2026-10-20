# Kế hoạch kiểm thử A1 Lab

## Điều kiện đầu vào

`docker compose ps` có 7 service chạy; `a1.py provision` và `a1.py verify` đã hoàn tất. Thời gian máy chủ Docker và Windows được đồng bộ. Chỉ thử trên các container `lab-*`.

| Mã | Thao tác | Kết quả mong đợi | Bằng chứng |
|---|---|---|---|
| TC01 | Đọc ba host và số item | Host tồn tại, có item | hostid, số item |
| TC02 | Đọc dữ liệu ICMP, Agent, SNMP | Item có giá trị mới, supported | lastvalue/lastclock |
| TC03 | Stop `lab-endpoint` | Trigger outage sau 3 mẫu lỗi | eventid, T_det |
| TC04 | Start `lab-endpoint` | Event recovery liên kết với problem | recovery eventid |
| TC05 | Stop endpoint 5 giây, start lại | Không có event outage mới sau 2 chu kỳ | danh sách event trước/sau |
| TC06 | `tc netem delay 500ms` | RTT > 200ms và trigger A1 sau 2 mẫu | RTT, eventid |
| TC07 | Ping từ SNMP container | Giá trị interface in tăng ở mẫu tiếp | itemid, trước/sau |
| TC08 | Tạo tệp 128 MiB trong Agent container | % dùng root filesystem tăng | itemid, trước/sau |
| TC09 | Dùng sự cố TC03 | Alert status sent và Mailpit nhận thư | alertid, mail id, T_notify |
| TC10 | Admin xác nhận payload `host.update` hợp lệ; viewer thử cùng payload | Viewer đọc được host/dashboard/map, API từ chối sửa | phản hồi quyền API |
| TC11 | Restart `zabbix-server` | Có mẫu ICMP mới sau restart, lịch sử trước restart còn | lastclock trước/sau, lastvalue |
| TC12 | Tra cứu event TC03/TC04 | Có problem và recovery trong lịch sử | eventid đôi |

Mỗi lần chạy sinh `output/test-run-*.json` gồm `id`, mục tiêu, actual, timestamp, trạng thái và evidence. Markdown cùng tên là bảng tóm tắt. Nếu có lỗi hoặc hết thời gian chờ, ca đó phải FAIL; không sửa kết quả thủ công thành PASS. Nếu nguồn dữ liệu không hỗ trợ một ca ở máy khác, ghi SKIP và lý do trong báo cáo riêng, không dùng số liệu giả.

## Chỉ số đánh giá

- `T_det = event.clock - fault_at` (giây).
- `T_notify = Mailpit.Created - event.clock` (giây).
- Tỷ lệ phát hiện = số lỗi hợp lệ có event / số lỗi hợp lệ đã chạy × 100%.
- Tỷ lệ thông báo = thư nhận được / thư dự kiến × 100%.
- Cảnh báo sai: đếm event khi endpoint đối chứng vẫn phản hồi, ghi thời gian quan sát.

Các tỷ lệ chỉ được tính trên ca đã thực sự chạy; không ngoại suy cho hạ tầng LIC. Riêng TC05 là phép thử hạn chế cảnh báo sai trong một cửa sổ ngắn, không chứng minh tỷ lệ cảnh báo sai dài hạn.

## Kịch bản trình diễn

1. Mở dashboard, giải thích ba nguồn dữ liệu và nhóm `A1 Lab`.
2. Mở Latest data cho ICMP, Agent và SNMP; chỉ ra biểu đồ.
3. Chạy `py -3.12 .\a1.py test --case TC03` và theo dõi Problems.
4. Kiểm tra thư problem và recovery trong Mailpit.
5. Mở `output/test-run-*.json` để trình bày timestamp, T_det/T_notify và hạn chế.
