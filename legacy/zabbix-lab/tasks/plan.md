# Kế hoạch hoàn thiện A1 Lab

Thứ tự: API và cấu hình → trạng thái chạy → kiểm thử và đo → tài liệu/bàn giao.

1. API client, CLI và bí mật: đăng nhập an toàn, API lỗi rõ, có unit test.
2. Provision idempotent: host/nhóm, media type, user/nhóm quyền, action, dashboard. Chạy lại không tạo trùng.
3. Kiểm tra trạng thái: xác nhận từng nguồn có dữ liệu mới và các cấu hình tồn tại; xuất JSON/Markdown.
4. Kịch bản TC01–TC12: tự động hóa những bước có thể thực hiện trong Docker; ghi SKIP cho tình huống không hỗ trợ, có thời điểm và bằng chứng.
5. Sao lưu/khôi phục PostgreSQL; kiểm tra backup không rỗng và tài liệu cách khôi phục.
6. Tài liệu vận hành, kiến trúc, kiểm thử, demo và mẫu báo cáo; chỉ nhận hoàn tất sau khi kiểm thử trên lab hiện tại.

Rủi ro: API Zabbix thay đổi theo phiên bản ảnh. Giữ nhánh 7.4 và kiểm tra runtime thật. Các thao tác dừng endpoint phải luôn khôi phục trong `finally`.
