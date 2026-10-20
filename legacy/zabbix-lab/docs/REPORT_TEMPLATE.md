# Khung báo cáo HKDN — A1 Lab

> Chỉ điền kết quả sau khi tự chạy và lưu bằng chứng. Bản này chưa phải báo cáo đã được LIC/giảng viên nghiệm thu.

## 1. Bối cảnh và phạm vi

Mục tiêu: hệ thống giám sát tập trung trên lab Docker. Nêu rõ không truy cập LIC và lý do điều chỉnh phạm vi. Đính kèm chấp thuận của giảng viên/mentor nếu có.

## 2. Yêu cầu và thiết kế

Tóm tắt FR01–FR10, NFR01–NFR06; dùng sơ đồ và ánh xạ ở `docs/ARCHITECTURE.md`. Giải thích lựa chọn Zabbix, ICMP, SNMP, Agent, PostgreSQL, Mailpit.

## 3. Triển khai

Phiên bản công cụ, cấu hình Compose, ba host, template/item/trigger, dashboard, action email, quyền. Không chèn mật khẩu hoặc community. Mô tả đóng góp của nhóm: thiết kế, cấu hình API, kịch bản kiểm thử, đo và tài liệu; không nhận đã lập trình Zabbix.

## 4. Kiểm thử và kết quả

Đính bảng TC01–TC12 từ `output/test-run-*.md`, tệp JSON làm minh chứng. Với mỗi ca ghi actual, thời điểm, PASS/FAIL/SKIP, ảnh màn hình nếu được phép. Tính T_det, T_notify và các tỷ lệ chỉ từ timestamp thực. Nêu rõ tổng thời gian quan sát và cảnh báo sai được ghi nhận.

## 5. Vận hành, sao lưu và hạn chế

Mô tả backup và lần khôi phục tạm đã kiểm tra; phân quyền; giới hạn container Agent, SNMP mô phỏng, email Mailpit, quy mô 3 host. Trình bày bước cần có nếu triển khai thật: quyền truy cập, SNMPv3, HTTPS, SMTP thật, sizing, backup, giám sát dài ngày.

## 6. Kết luận và hướng phát triển

Kết luận theo kết quả thực nghiệm; không suy luận hiệu năng hoặc tính phù hợp LIC từ 3 host lab. Đề xuất một cải tiến ưu tiên có cơ sở từ lỗi/hạn chế đã đo.
