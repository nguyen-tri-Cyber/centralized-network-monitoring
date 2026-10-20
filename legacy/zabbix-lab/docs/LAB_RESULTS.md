# Kết quả kiểm chứng A1 Docker Lab — 10/10/2026

## Phạm vi và bằng chứng

Hệ thống gồm 7 service Docker, 3 host giám sát và 3 nguồn dữ liệu: ICMP, Linux Agent, SNMPv2c. Lệnh `a1.py verify` lúc 09:41:53 UTC đạt 8/8 chỉ số có dữ liệu mới và xác nhận dashboard, sơ đồ, action, media type, tài khoản và service. Đây là kết quả trên máy lab; không có phép đo trên hạ tầng LIC.

Tệp gốc trên máy chạy lab: `output/verify-20261010T094153Z.json`, `output/test-summary.json`, `output/test-run-*.json` và `output/operations-20261010T094234Z.csv`. Các tệp này chứa dữ liệu đo cụ thể, được loại khỏi gói nguồn để tránh công bố ngoài ý muốn.

## Kết quả TC01–TC12

Lệnh `a1.py summarize` chọn kết quả mới nhất cho từng ca: **12/12 PASS**. Các ca được thực hiện riêng hoặc theo nhóm TC03/04/09/12; đây không phải một lần chạy `--case all` liên tục.

| Quan sát | Kết quả |
|---|---:|
| Ngắt ICMP endpoint → sự kiện TC03 | 140 giây (T_det) |
| Sự kiện TC03 → email Mailpit TC09 | 3 giây (T_notify) |
| Khôi phục endpoint TC04 | Có event recovery liên kết với problem |
| Tạo độ trễ 500 ms ở TC06 | RTT 0,5 giây; trigger sau 91 giây |
| Tạo lưu lượng SNMP TC07 | Giá trị interface in 184 → 4808 bps |
| Tạo tệp 128 MiB ở TC08 | Root disk used 1,028013% → 1,041094% |
| Tài khoản viewer TC10 | Đọc host/dashboard/map; API từ chối update host hợp lệ |
| Restart Zabbix Server TC11 | Mẫu ICMP mới sau restart; mẫu cũ còn trong DB |
| Ngắt ngắn 5 giây TC05 | Không có outage event mới trong thời gian quan sát |

Trong hai lần gây lỗi hợp lệ được tính (TC03 và TC06), cả hai có sự kiện: 2/2 = 100%. Trong một lần thử thông báo TC09, email và alert đều được ghi nhận: 1/1 = 100%. Đây là tỷ lệ của số lần thử ít ỏi trong lab, không phải ước lượng độ tin cậy hay SLA. TC05 chỉ kiểm tra một tình huống ngắn, không chứng minh tỷ lệ cảnh báo sai dài hạn.

## Báo cáo vận hành và phục hồi

`a1.py report --hours 24` tạo cửa sổ truy vấn 24 giờ, nhưng hệ thống chỉ có **57 mẫu ICMP** trong cửa sổ đó: 87,72% mẫu có phản hồi. Con số này bị ảnh hưởng bởi các sự cố được tạo có chủ đích. Có 359 mẫu chỉ số xuất CSV; không được gọi 87,72% là uptime 24 giờ liên tục.

`backup.ps1` tạo bản sao lưu sau khi đổi mật khẩu Admin; `verify-backup.ps1` khôi phục vào database tạm và xác nhận đủ 3 host. Mật khẩu Admin mặc định đã bị từ chối; mật khẩu mới lưu cục bộ trong `local-accounts.json` bị Git bỏ qua. Chưa chạy khôi phục ghi đè database hiện tại vì phép khôi phục tạm đã xác nhận bản dump và tránh mất lịch sử đo đang dùng.

## Giới hạn

Agent chạy trong container nên số liệu CPU/RAM/disk không đại diện máy chủ LIC. SNMP là container mô phỏng với v2c trên mạng Docker riêng; email chỉ tới Mailpit. Bản đồ là sơ đồ logic ba host, không phải topology mạng vật lý. Chưa có quan sát dài ngày, kiểm thử tải nhiều thiết bị, SMTP thật, SNMPv3 hoặc phê duyệt nghiệm thu từ LIC/UTH.
