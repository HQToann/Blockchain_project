# 🟢 NGÀY 11: HƯỚNG DẪN ĐƯA TRANG WEB LÊN MẠNG INTERNET (RENDER & SUPABASE) DÀNH CHO NGƯỜI MỚI

Chúc mừng bạn đã đi đến chặng cuối cùng! Hiện tại trang web Bầu cử Blockchain của bạn chỉ đang chạy "offline" trên máy tính cá nhân (localhost:8000). Hôm nay, chúng ta sẽ đưa nó lên Internet để bất kỳ ai trên thế giới cũng có thể truy cập được thông qua đường link `ten-du-an.onrender.com`.

Để làm được điều này, chúng ta cần 2 nền tảng hoàn toàn MIỄN PHÍ:
1. **Supabase:** Nơi lưu trữ dữ liệu (Database).
2. **Render:** Nơi chạy trang web và máy quét Blockchain.

Hãy làm theo từng bước thật chậm rãi nhé, cầm tay chỉ việc từ A-Z!

---

## BƯỚC 1: Đẩy toàn bộ mã nguồn lên GitHub (Nếu bạn chưa làm)

Render cần lấy mã nguồn từ GitHub để chạy, nên bước đầu tiên là bạn phải đẩy code lên đó.

1. Đăng nhập vào [GitHub](https://github.com/) và tạo một kho lưu trữ (Repository) mới. Đặt tên là `blockchain-voting-dapp` (hoặc tên tùy thích). **Không** tích vào ô "Add a README".
2. Mở cửa sổ dòng lệnh (Terminal/CMD) tại thư mục dự án của bạn (thư mục chứa file `manage.py`).
3. Chạy lần lượt các lệnh sau:
   ```bash
   git init
   git add .
   git commit -m "San sang dua len mang"
   git branch -M main
   git remote add origin https://github.com/TÊN_GITHUB_CỦA_BẠN/blockchain-voting-dapp.git
   git push -u origin main
   ```
*(Nếu nó đòi mật khẩu GitHub, hãy đăng nhập theo hướng dẫn trên màn hình nhé).*

---

## BƯỚC 2: Tạo Cơ Sở Dữ Liệu trên Supabase

Trên máy tính, bạn dùng SQLite (file `db.sqlite3`). Nhưng trên Internet, chúng ta cần một Database thực thụ mạnh mẽ hơn, đó là PostgreSQL.

1. Truy cập [Supabase.com](https://supabase.com/) và nhấn **"Start your project"** (Đăng nhập bằng GitHub luôn cho tiện).
2. Nhấn nút **"New Project"**, chọn tên tổ chức của bạn (thường là tên tài khoản GitHub).
3. Điền thông tin:
   - **Name:** Bầu Cử Blockchain (hoặc gì cũng được).
   - **Database Password:** Gõ một mật khẩu **thật khó** và **NHỚ COPY LẠI MẬT KHẨU NÀY** ra file Notepad (Rất quan trọng!).
   - **Region:** Chọn `Singapore` (để tốc độ tải trang về Việt Nam nhanh nhất).
4. Nhấn **"Create new project"**. Đợi khoảng 2-3 phút để Supabase xây dựng Database cho bạn.
5. Khi xong, nhìn sang thanh menu bên trái, cuộn xuống dưới cùng chọn biểu tượng ⚙️ **Project Settings**.
6. Chọn mục **Database** ở menu con bên trái.
7. Cuộn xuống phần **"Connection string"**, chọn tab **URI**.
8. Bạn sẽ thấy một đường link màu đen giống như thế này:
   `postgresql://postgres.xxxxxxxx:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres`
9. **Copy đường link đó**, thay chữ `[YOUR-PASSWORD]` bằng chính cái mật khẩu bạn vừa lưu ở bước 3.
   *(Ví dụ: Nếu mật khẩu là `MatKhau123`, link sẽ thành: `postgresql://postgres.xxxxxxxx:MatKhau123@...`)*.
10. Lưu lại link hoàn chỉnh này ra Notepad. Chút nữa ta sẽ dùng đến nó.

---

## BƯỚC 3: Tạo Tài Khoản Render và Triển Khai (Deploy) Tự Động

Mã nguồn của chúng ta đã được tích hợp sẵn chức năng "Triển khai 1 chạm". Tức là bạn không cần cấu hình bằng tay lằng nhằng, Render sẽ tự hiểu cấu trúc code thông qua file `render.yaml`.

1. Truy cập [Render.com](https://render.com/) và nhấn **"Get Started"** (Tiếp tục đăng nhập bằng GitHub).

   Dưới đây là nội dung file `render.yaml` trong mã nguồn của bạn:
   ```yaml
   services:
     # Dịch vụ Web Chính (Django + Indexer chạy ngầm)
     - type: web
       name: voting-dapp-web
       env: python
       plan: free
       buildCommand: "./build.sh"
       startCommand: "bash ./start.sh"
       envVars:
         - key: PYTHON_VERSION
           value: 3.11.0
         - key: REDIS_URL
           sync: false # Sẽ nhập tay từ dự án cũ trên Dashboard
         - key: DJANGO_SECRET_KEY
           generateValue: true
         - key: USE_SQLITE
           value: "False"
         - key: DATABASE_URL
           sync: false # Sẽ nhập tay từ Supabase trên Dashboard
         - key: ALCHEMY_RPC_URL
           sync: false # Sẽ nhập tay trên Dashboard
         - key: PRIVATE_KEY
           sync: false # Sẽ nhập tay trên Dashboard
         - key: ADMIN_WALLET_ADDRESS
           sync: false # Sẽ nhập tay trên Dashboard
         - key: PINATA_JWT
           sync: false # Sẽ nhập tay trên Dashboard
   ```

   > **Tại sao không tách Indexer thành một Worker độc lập?**
   > Render **KHÔNG MIỄN PHÍ** cho loại hình dịch vụ Worker. Nếu bạn tách riêng Worker, Render sẽ bắt buộc bạn nhập thẻ tín dụng (Visa/Mastercard) và tính phí ít nhất $7/tháng.
   > Để lách luật và tận dụng hoàn toàn gói Free, chúng ta tạo một file `start.sh` để bắt cái Web Service miễn phí "cõng" luôn cả Indexer chạy ngầm.

   ### Tạo script Build và Khởi động
   
   **1. Tạo file `build.sh` (Cài đặt thư viện)**
   ```bash
   #!/bin/bash
   echo "📦 Đang cài đặt thư viện..."
   python -m pip install --upgrade pip
   pip install -r requirements.txt

   echo "📦 Gộp file tĩnh (CSS/JS)..."
   python manage.py collectstatic --no-input

   echo "📦 Tạo bảng Database..."
   python manage.py migrate --noinput
   ```

   **2. Tạo file `start.sh` (Chạy song song Web + Indexer)**
   ```bash
   #!/bin/bash
   # Chạy Indexer ngầm
   python indexer/indexer.py &

   # Chạy Django Web Server
   daphne -b 0.0.0.0 -p $PORT core.asgi:application
   ```

2. Khi vào đến màn hình điều khiển (Dashboard), nhìn lên góc trên bên phải, nhấn nút **"New +"** và chọn **"Blueprint"** (Lựa chọn cuối cùng).
3. Render sẽ hiện danh sách các kho code GitHub của bạn. Tìm kho `blockchain-voting-dapp` vừa tạo ở Bước 1 và nhấn nút **"Connect"**.
4. Render sẽ quét file `render.yaml` trong code của bạn và hiện ra một bảng yêu cầu nhập các "Biến Môi Trường" (Environment Variables). Hãy điền cẩn thận nhé:

   - **DATABASE_URL:** Dán cái đường link Supabase hoàn chỉnh (đã sửa mật khẩu) ở Bước 2.
   - **ALCHEMY_RPC_URL:** Dán link Alchemy mạng Sepolia của bạn (Lấy trong file `.env`).
   - **PRIVATE_KEY:** Dán Private Key ví MetaMask của Admin (Lấy trong file `.env`).
   - **ADMIN_WALLET_ADDRESS:** Dán địa chỉ ví Admin public (Lấy trong file `.env`).
   - **PINATA_JWT:** Dán mã token Pinata (Lấy trong file `.env`).

5. Kéo xuống dưới cùng và nhấn nút **"Apply"**.

---

## BƯỚC 4: Ngồi Chờ Và Tận Hưởng Phép Màu ☕

Lúc này, Render sẽ bắt đầu "cày cuốc" thay cho bạn. Nó đang tạo ra **2 máy chủ** cùng một lúc (hãy nhìn vào bảng theo dõi trên Render):
1. **voting-redis:** Trạm trung chuyển để báo tin (WebSocket).
2. **voting-dapp-web:** Trạm chính chạy giao diện Website (kiêm luôn Indexer chạy ngầm).

**Quá trình này mất khoảng 5 - 10 phút.**
Khi bạn thấy cả 2 dịch vụ chuyển sang trạng thái chữ **"Live"** màu xanh lá cây, tức là MỌI THỨ ĐÃ XONG!

---

## BƯỚC 5: Nghiệm Thu Thành Quả

1. Bấm vào dịch vụ có tên là **`voting-dapp-web`** trên Render.
2. Nhìn lên góc trái trên cùng, bạn sẽ thấy một đường link dạng `https://voting-dapp-web-xxxx.onrender.com`.
3. Bấm vào link đó! Giao diện trang web của bạn sẽ hiện ra rực rỡ!

### Chạy thử luồng người dùng:
1. Bạn hãy mở link trang web (ở Bước 5.2) bằng điện thoại hoặc máy tính khác để đóng vai Cử tri.
2. Vào đường link `https://voting-dapp-web-xxxx.onrender.com/admin/`, đăng nhập bằng Ví MetaMask (Web3 Auth).
3. Thử tạo một cuộc bầu cử mới, tải ảnh ứng viên lên IPFS.
4. Lấy điện thoại (vai Cử tri) vote thử 1 ứng viên.
   5. **Cảm nhận sự kỳ diệu:** Biểu đồ trên màn hình Admin và máy tính sẽ TỰ ĐỘNG nhảy phần trăm ngay lập tức (nhờ WebSockets) mà không cần F5!
   
---

## BƯỚC 6: 4 LỖI "TỬ THẦN" THƯỜNG GẶP KHI ĐƯA LÊN PRODUCTION VÀ CÁCH XỬ LÝ

Trong quá trình đưa lên Render, bạn chắc chắn sẽ gặp phải những khác biệt giữa môi trường "Máy tính ở nhà (Windows)" và "Máy chủ (Linux)". Hãy kiểm tra xem bạn đã xử lý các lỗi sau chưa:

### 1. Lỗi xung đột Hashing của thư viện `pipenv` (Khác biệt Windows vs Linux)
**Hiện tượng:** Render báo lỗi `ERROR: No matching distribution found for pywin32==312` hoặc `Package installation failed...`
**Cách xử lý:** 
- KHÔNG dùng lệnh `pipenv install --deploy` trên máy chủ Render.
- Thay vào đó, ở máy tính bạn chạy lệnh: `pipenv requirements > requirements.txt`.
- Sau đó mở file `requirements.txt` ra, **xóa dòng chứa `pywin32`** đi (vì đây là thư viện chỉ chạy trên Windows).
- Đẩy `requirements.txt` lên GitHub và dùng `pip install -r requirements.txt` trong `build.sh`.

### 2. Lỗi Không tìm thấy file ABI (Thư mục artifacts bị Git ẩn đi)
**Hiện tượng:** Web chạy lên bị văng lỗi 500: `FileNotFoundError: [Errno 2] No such file or directory: 'artifacts/contracts/VotingSystem.sol/ElectionFactory.json'`
**Cách xử lý:** Thư mục `artifacts` mặc định bị liệt kê trong `.gitignore` nên không được đẩy lên mạng. Bạn cần:
- Copy 2 file ABI ra thư mục gốc, đổi tên thành `Factory_ABI.json` và `Election_ABI.json`.
- Vào file `election/admin.py` và `indexer/indexer.py` sửa lại đường dẫn đọc file chỉ còn `open("Factory_ABI.json", ...)` thay vì chui vào `artifacts/...`

### 3. Lỗi Bảo mật CSRF 403 Forbidden của Django
**Hiện tượng:** Vào trang Admin, bấm nút Đóng/Mở hòm phiếu bị văng màn hình trắng báo lỗi `CSRF verification failed`.
**Cách xử lý:** Django bảo vệ web cực kỳ chặt. Nó không cho phép nhận dữ liệu từ một tên miền lạ chưa khai báo. 
- Mở `core/settings.py`.
- Thêm dòng: `CSRF_TRUSTED_ORIGINS = ['https://ten-du-an-cua-ban.onrender.com']` (Thay bằng link web thực tế của bạn).

### 4. Lỗi Kẹt Cổng Nội Bộ (WebSockets chết đứng)
**Hiện tượng:** Bỏ phiếu xong thành công nhưng máy tính không tự nhảy số, phải F5 mới thấy phiếu.
**Cách xử lý:** Dưới local, Web và Indexer gọi nhau qua `http://127.0.0.1:8000`. Nhưng trên Render, Web chạy qua cổng động `$PORT`.
- Mở `indexer/indexer.py`.
- Sửa hàm gửi tín hiệu lại thành: `requests.post(f"http://127.0.0.1:{os.environ.get('PORT')}/api/internal/notify_vote/")`
- Đồng thời, trình duyệt sẽ chặn WebSocket `ws://` nếu web đang chạy `https://`. Mở `static/js/app.js`, cấu hình để nó tự động đổi sang `wss://` nếu đang ở môi trường HTTPS.

> [!NOTE]
> **Lưu ý nhỏ:** Vì chúng ta dùng gói Miễn Phí của Render, nên nếu trang web không có ai truy cập trong 15 phút, máy chủ sẽ tự động "Ngủ gật" để tiết kiệm điện. Lần tiếp theo có người truy cập, máy chủ sẽ mất khoảng 30 - 50 giây để "Thức dậy". Đây là chuyện hoàn toàn bình thường của gói miễn phí. Nếu muốn web luôn thức và chạy siêu tốc, bạn có thể cân nhắc nâng cấp lên gói trả phí (khoảng 7$/tháng).
 
**🎉 CHÚC MỪNG BẠN! DỰ ÁN CỦA BẠN ĐÃ CHÍNH THỨC LIVE TRÊN INTERNET!**
