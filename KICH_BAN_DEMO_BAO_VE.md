# Kịch bản Demo Bảo Vệ (2 phút)

## 1) Mục tiêu demo
- Chứng minh hệ thống đáp ứng đủ 4 yêu cầu đề tài:
  - Ghi chép thu nhập - chi tiêu
  - Phân loại chi tiêu theo danh mục
  - Thống kê theo tháng
  - Cảnh báo vượt ngân sách

## 2) Kịch bản thao tác theo thời gian

### 0:00 - 0:15 | Mở đầu
- Câu nói gợi ý:
  - Em xin demo hệ thống quản lý tài chính cá nhân bằng giao diện dòng lệnh.
  - Hệ thống có 4 chức năng chính: ghi chép thu chi, phân loại danh mục, thống kê tháng và cảnh báo vượt ngân sách.

### 0:15 - 0:35 | Tạo dữ liệu mẫu nhanh
- Thao tác:
  - Chọn menu 7: Demo nhanh (tạo dữ liệu mẫu).
- Câu nói gợi ý:
  - Em dùng chức năng demo nhanh để tạo dữ liệu mẫu gồm 1 giao dịch thu và 2 giao dịch chi, giúp kiểm tra toàn bộ luồng nhanh và ổn định.

### 0:35 - 0:55 | Xem lịch sử giao dịch
- Thao tác:
  - Chọn menu 1: Xem danh sách giao dịch.
- Câu nói gợi ý:
  - Hệ thống hiển thị ngày giờ, loại Thu/Chi, danh mục, số tiền và ghi chú.
  - Đây là phần thể hiện chức năng ghi chép thu nhập - chi tiêu.

### 0:55 - 1:25 | Thống kê tháng và cảnh báo ngân sách
- Thao tác:
  - Chọn menu 5: Thống kê theo tháng.
  - Nhập năm/tháng hiện tại.
- Câu nói gợi ý:
  - Hệ thống tổng hợp tổng thu, tổng chi, số dư và số lượng giao dịch theo tháng.
  - Đồng thời so sánh với hạn mức ngân sách.
  - Nếu tổng chi vượt hạn mức, hệ thống hiển thị cảnh báo và số tiền vượt cụ thể.

### 1:25 - 1:45 | Tổng kết theo danh mục
- Thao tác:
  - Chọn menu 6: Tổng kết theo danh mục.
- Câu nói gợi ý:
  - Màn hình này cho thấy chi tiêu theo từng nhóm danh mục.
  - Cuối bảng có tổng THU và tổng CHI để theo dõi tổng quan.

### 1:45 - 2:00 | Kết luận
- Câu nói gợi ý:
  - Qua demo, hệ thống đã đáp ứng đủ yêu cầu đề tài.
  - Hướng phát triển tiếp theo là giao diện web, biểu đồ trực quan và phân quyền người dùng.

## 3) Bản nói ngắn 30-40 giây (phòng khi hết giờ)
- Bản đọc nhanh:
  - Nhóm em xây dựng hệ thống quản lý tài chính cá nhân chạy trên CLI.
  - Hệ thống cho phép thêm giao dịch thu chi, phân loại danh mục, thống kê theo tháng và cảnh báo vượt ngân sách.
  - Em dùng chức năng demo nhanh để tạo dữ liệu mẫu, sau đó kiểm tra lần lượt lịch sử giao dịch, báo cáo tháng và tổng kết danh mục.
  - Kết quả cho thấy hệ thống hoạt động ổn định và đáp ứng đúng yêu cầu đề bài.

## 4) 5 câu hỏi giảng viên hay hỏi và cách trả lời

1. Vì sao chọn SQLite?
- Trả lời gợi ý:
  - Vì SQLite nhẹ, không cần cài server, phù hợp bài tập học phần và dễ triển khai trên máy cá nhân.

2. Nếu người dùng nhập sai dữ liệu thì sao?
- Trả lời gợi ý:
  - Hệ thống đã kiểm tra số tiền phải lớn hơn 0, bắt lỗi định dạng số, và kiểm tra danh mục hợp lệ trước khi lưu.

3. Cảnh báo ngân sách được tính như thế nào?
- Trả lời gợi ý:
  - Lấy tổng chi theo tháng rồi so sánh với budget_limit.
  - Nếu tổng chi lớn hơn hạn mức thì hiển thị cảnh báo kèm số tiền vượt.

4. Dự án đã phân công công việc ra sao?
- Trả lời gợi ý:
  - Mỗi thành viên phụ trách các nhóm chức năng riêng và thể hiện qua commit trên Git.
  - Em phụ trách các phần nhập liệu an toàn, báo cáo tháng và tổng kết danh mục.

5. Hướng nâng cấp tiếp theo là gì?
- Trả lời gợi ý:
  - Nâng cấp giao diện web/mobile, thêm biểu đồ, xuất báo cáo PDF/Excel, và hỗ trợ nhiều người dùng.

## 5) Checklist trước khi demo
- Chạy chương trình thành công trên máy demo.
- Kiểm tra menu 1, 5, 6, 7 hoạt động.
- Có dữ liệu mẫu để tránh màn hình trống.
- Có sẵn 1 bản nói ngắn để xử lý khi bị giới hạn thời gian.
