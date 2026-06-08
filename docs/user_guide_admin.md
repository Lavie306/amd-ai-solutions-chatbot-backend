# Sổ Tay Vận Hành Admin Dashboard — AMD Chatbot

Tài liệu này hướng dẫn người quản trị vận hành giao diện Admin Dashboard của hệ thống **AMD Chatbot**. Hệ thống bao gồm chatbot tự động thu thập lead, chăm sóc khách hàng bằng RAG (Retrieval-Augmented Generation) và tự động kích hoạt email follow-up theo kịch bản được định sẵn.

---

## Mục Lục
1. [Tổng Quan Giao Diện](#1-tổng-quan-giao-diện)
2. [Quản Lý Khách Hàng (Leads)](#2-quản-lý-khách-hàng-leads)
3. [Cấu Hình Chatbot & Tùy Biến Giao Diện](#3-cấu-hình-chatbot--tùy-biến-giao-diện)
4. [Quản Lý Kho Tri Thức (Knowledge Base)](#4-quản-lý-kho-tri-thức-knowledge-base)
5. [Thiết Lập Quy Tắc Chăm Sóc Tự Động (Follow-up Rules)](#5-thiết-lập-quy-tắc-chăm-sóc-tự-động-follow-up-rules)
6. [Quản Lý & Theo Dõi Tác Vụ (Follow-up Jobs)](#6-quản-lý--theo-dõi-tác-vụ-follow-up-jobs)

---

## 1. Tổng Quan Giao Diện

Khi đăng nhập vào Admin Dashboard bằng tài khoản quản trị (sử dụng JWT token dưới nền hệ thống), bạn sẽ thấy bảng điều khiển trung tâm bao gồm:
*   **Thống kê nhanh**: Tổng số lead thu thập được, số lead đang được tư vấn (`CONSULTING`), số lead đã chốt đơn thành công (`WON`), và số lượng email follow-up đang chờ gửi.
*   **Menu điều hướng**:
    *   **Dashboard / Leads**: Quản lý thông tin khách hàng và lịch sử hội thoại.
    *   **Knowledge Base**: Quản lý các file tài liệu hướng dẫn và dữ liệu huấn luyện chatbot.
    *   **Follow-up Rules**: Cài đặt kịch bản gửi email tự động chăm sóc lead.
    *   **Settings**: Điều chỉnh hành vi chatbot và cấu hình chung.

---

## 2. Quản Lý Khách Hàng (Leads)

Module Leads cho phép bạn theo dõi và chuyển đổi cơ hội bán hàng từ các cuộc hội thoại của chatbot.

### 2.1. Tìm kiếm và Bộ lọc
*   **Tìm kiếm**: Nhập tên, số điện thoại hoặc email của khách hàng vào ô Tìm kiếm để tìm lead tương ứng nhanh chóng.
*   **Bộ lọc trạng thái**: Phân loại lead theo các trạng thái trong chu trình bán hàng (Sales Pipeline):
    *   `NEW`: Lead mới đăng ký hoặc mới chat.
    *   `CONTACTED`: Đã liên hệ hoặc đã có tương tác sơ bộ từ chatbot.
    *   `CONSULTING`: Chatbot/Nhân viên đang tư vấn chi tiết.
    *   `QUOTED`: Đã gửi báo giá.
    *   `NEGOTIATING`: Đang thương lượng.
    *   `WON`: Đã chốt hợp đồng thành công.
    *   `LOST`: Không chốt được.
    *   `COLD`: Khách hàng không phản hồi trong thời gian dài.

### 2.2. Chi tiết Lead & Nhật ký chat (Chat Log)
Bấm vào một dòng lead cụ thể để xem chi tiết:
*   **Thông tin cá nhân**: Tên, Số điện thoại, Email, Nhu cầu chính được chatbot nhận diện (`intent`).
*   **Lịch sử chat**: Xem toàn bộ cuộc đối thoại thực tế giữa khách hàng và AI theo thời gian thực. Điều này giúp bạn hiểu khách hàng đã hỏi những câu hỏi gì, RAG trả lời ra sao và ngữ cảnh của lead trước khi bạn gọi điện trực tiếp.
*   **Ghi chú nội bộ (Notes)**: Nhập thông tin bổ sung sau khi trao đổi trực tiếp (Ví dụ: *"Khách hàng thích sản phẩm X, yêu cầu gửi báo giá qua Zalo vào sáng mai"*). Bấm **Lưu** để cập nhật. Ghi chú này sẽ được lưu trữ đồng bộ cùng hồ sơ lead.
*   **Cập nhật Trạng thái thủ công**: Bạn có thể thay đổi trạng thái bán hàng của lead trực tiếp từ giao diện (Ví dụ: Chuyển từ `CONSULTING` sang `WON`). Việc chuyển trạng thái này sẽ **tự động cập nhật hoặc lên lịch lại** các kịch bản follow-up đi kèm.

---

## 3. Cấu Hình Chatbot & Tùy Biến Giao Diện

Module Settings cho phép cấu hình các tham số vận hành mà không cần chỉnh sửa mã nguồn backend.

### 3.1. Các tham số cấu hình chính
Hệ thống hỗ trợ các cặp khóa-giá trị (Key-Value) có thể sửa đổi:
1.  **`chatbot_name`**: Tên hiển thị của chatbot (Ví dụ: *"AMD Virtual Assistant"*).
2.  **`welcome_message`**: Tin nhắn chào mừng tự động khi người dùng mở cửa sổ chat (Ví dụ: *"Chào bạn! Mình là trợ lý ảo AMD. Mình có thể giúp gì cho bạn hôm nay?"*).
3.  **`handoff_zalo`**: Số điện thoại hoặc liên kết Zalo để khách hàng nhấn liên hệ trực tiếp với nhân viên hỗ trợ khi chatbot không trả lời được hoặc nhận diện khách hàng cần hỗ trợ khẩn cấp.
4.  **`max_tokens` / `temperature`**: Các tham số kỹ thuật để điều chỉnh độ dài câu trả lời và tính sáng tạo của AI.

### 3.2. Lưu cấu hình
*   Mỗi khi thay đổi giá trị cấu hình, bấm **Save Settings** để lưu trữ xuống cơ sở dữ liệu.
*   Các thiết lập này sẽ lập tức đồng bộ sang chatbot widget đang nhúng trên website thông qua endpoint API công khai `/api/settings/public/config`. Người dùng trên website sẽ thấy giao diện và lời chào mới ngay sau khi tải lại trang.

---

## 4. Quản Lý Kho Tri Thức (Knowledge Base)

Quyết định chất lượng câu trả lời của chatbot phụ thuộc vào dữ liệu được nạp tại module này. Hệ thống sử dụng công nghệ RAG giúp AI chỉ trả lời dựa trên tài liệu được cung cấp, hạn chế tối đa hiện tượng "ảo tưởng" (hallucination).

### 4.1. Định dạng tài liệu hỗ trợ
*   Hệ thống hỗ trợ upload các định dạng tài liệu phổ biến: `.txt`, `.pdf`, `.docx`, `.md`.
*   Tài liệu tải lên nên được trình bày rõ ràng dưới dạng Hỏi & Đáp (FAQ) hoặc tài liệu mô tả sản phẩm có cấu trúc phân cấp tốt để tối ưu hiệu quả tìm kiếm vector store.

### 4.2. Upload tài liệu mới
1.  Truy cập vào trang **Knowledge Base**.
2.  Bấm nút **Upload Document** hoặc kéo thả file vào vùng chỉ định.
3.  Hệ thống sẽ tải file lên máy chủ, tự động thực hiện chia nhỏ file (chunking), tạo embedding thông qua OpenAI API và lưu trữ vào cơ sở dữ liệu vector store (ChromaDB).
4.  Sau khi tải xong, tài liệu sẽ hiển thị trong danh sách kèm trạng thái `indexed`.

### 4.3. Quản lý, Re-index và Xóa tài liệu
*   **Xem danh sách**: Dashboard liệt kê tất cả các file tài liệu kèm kích thước, số lượng đoạn văn (chunks) được cắt nhỏ, và thời gian cập nhật.
*   **Re-index**: Nếu bạn chỉnh sửa nội dung file vật lý trên server hoặc muốn tạo lại embedding cho file, bấm nút **Re-index** bên cạnh tài liệu.
*   **Xóa tài liệu**: Bấm biểu tượng thùng rác (**Delete**). Hệ thống sẽ xóa file vật lý trên server đồng thời loại bỏ toàn bộ dữ liệu vector của file đó khỏi ChromaDB. Chatbot sẽ lập tức không còn tham chiếu thông tin từ tài liệu này nữa.

---

## 5. Thiết Lập Quy Tắc Chăm Sóc Tự Động (Follow-up Rules)

Quy trình chăm sóc khách hàng sau khi nhận thông tin (Lead) được thiết lập tự động qua các Quy tắc gửi mail (Follow-up Rules).

### 5.1. Cấu trúc một Rule chăm sóc khách hàng
Khi thêm một quy tắc mới, bạn cần điền các thông tin sau:
1.  **Trạng thái kích hoạt (Trigger Status)**: Trạng thái của lead mà quy tắc này áp dụng (Ví dụ: `NEW` hoặc `QUOTED`).
2.  **Thời gian chờ (Delay Hours / Days)**: Khoảng thời gian hệ thống sẽ chờ kể từ khi lead chuyển sang trạng thái kích hoạt trước khi thực thi hành động (Ví dụ: Chờ `2` ngày).
3.  **Loại hành động (Action Type)**: Hiện tại hệ thống hỗ trợ gửi Email tự động (`SEND_EMAIL`).
4.  **Tiêu đề Email (Subject)**: Tiêu đề email gửi đi (Ví dụ: *"Giải pháp AI từ AMD - Cảm ơn quý khách đã quan tâm"*).
5.  **Mẫu nội dung (Email Template / Body)**: Hỗ trợ cú pháp HTML và các biến động để cá nhân hóa email:
    *   `{{ name }}`: Tên của khách hàng.
    *   `{{ phone }}`: Số điện thoại của khách hàng.
    *   `{{ email }}`: Email của khách hàng.
    *   *Ví dụ mẫu*:
        ```html
        <p>Chào bạn <strong>{{ name }}</strong>,</p>
        <p>Cảm ơn bạn đã quan tâm đến giải pháp AI của AMD. Chúng tôi nhận thấy bạn đang tìm hiểu giải pháp này và muốn hỗ trợ bạn thêm...</p>
        ```

### 5.2. Cách thức hoạt động
*   Khi trạng thái của lead thay đổi (Ví dụ từ `NEW` sang `CONTACTED`), hệ thống sẽ **hủy bỏ tất cả các lịch trình chăm sóc đang chờ** của trạng thái cũ (`NEW`).
*   Đồng thời, hệ thống tự động quét các rules áp dụng cho trạng thái mới (`CONTACTED`) để tạo các tác vụ chờ (Jobs) gửi email trong tương lai.

---

## 6. Quản Lý & Theo Dõi Tác Vụ (Follow-up Jobs)

Trang **Follow-up Jobs** là nơi hiển thị danh sách các tác vụ gửi email đang được xếp hàng đợi hoặc đã thực thi.

### 6.1. Trạng thái của tác vụ (Job Status)
*   `PENDING`: Tác vụ đang được lên lịch và chờ đến giờ thực thi.
*   `COMPLETED`: Tác vụ đã thực thi gửi email thành công.
*   `FAILED`: Gửi email thất bại (do sai định dạng email, lỗi kết nối nhà cung cấp SendGrid, v.v.).
*   `CANCELLED`: Tác vụ đã bị hủy tự động do lead thay đổi trạng thái sang bước mới trước khi tác vụ kịp chạy, hoặc do admin chủ động bấm hủy.

### 6.2. Hủy tác vụ thủ công (Cancel Job)
Nếu bạn nhận thấy một lead đã được liên hệ trực tiếp ngoài hệ thống và không cần gửi email tự động theo kịch bản nữa:
1.  Tìm tác vụ tương ứng của lead đó tại trang **Follow-up Jobs** (lọc theo trạng thái `PENDING`).
2.  Bấm nút **Cancel** bên cạnh tác vụ đó.
3.  Trạng thái tác vụ sẽ chuyển sang `CANCELLED` và hệ thống sẽ không thực hiện gửi email đó nữa.
