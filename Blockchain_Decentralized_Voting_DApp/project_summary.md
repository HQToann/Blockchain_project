# BÁO CÁO TỔNG KẾT DỰ ÁN

> **Phiên bản:** 2.0 — Cập nhật 09/2026

Dự án đã trải qua quá trình phát triển liên tục từ một ứng dụng cơ bản thành một hệ thống **DApp (Decentralized Application)** hoàn chỉnh, đạt chuẩn Production về cả kiến trúc lẫn trải nghiệm người dùng.

---

## Phần 1: Điểm Nổi Bật Của Dự Án

### ✅ Bảo Mật & Đáng Tin Cậy
| Tính năng | Chi tiết |
|:---|:---|
| **Web3 Auth** | Đăng nhập Admin bằng chữ ký MetaMask — không mật khẩu, không thể giả mạo |
| **CSRF Protection** | Tất cả API thay đổi dữ liệu đều có CSRF token |
| **Rate Limiting** | Giới hạn 5 lần đăng nhập/phút, 10 nonce/phút theo IP |
| **Nội bộ bảo mật** | Webhook Indexer → Django dùng `INTERNAL_API_SECRET` riêng biệt |
| **XSS Prevention** | Hàm `escapeHTML()` cho toàn bộ data render từ API |
| **Admin Wallet DB** | Danh sách admin lưu trong Database, quản lý từ UI — không sửa code |
| **CDN SRI Hash** | ethers.js có SRI integrity hash, Chart.js và Toastify pin version cố định |

### ✅ Kiến Trúc Tốt
| Tính năng | Chi tiết |
|:---|:---|
| **Broadcast-only TX** | Task gửi TX rồi trả về ngay — không block request thread |
| **Web3 Singleton** | Khởi tạo Web3 provider 1 lần, tái dụng toàn process |
| **N+1 Query Eliminated** | Dùng `annotate()` thay vì loop query trong `get_elections` |
| **Thread-safe Nonce** | `NONCE_LOCK` + `CURRENT_NONCE` ngăn TX conflict khi nhiều task chạy đồng thời |
| **Atomic DB Write** | `transaction.atomic()` đảm bảo cộng phiếu + ghi VoteRecord không bị tách đôi |
| **SystemLog Auto-rotation** | Signal tự xóa log cũ, giữ tối đa 1000 bản ghi mới nhất |

### ✅ Trải Nghiệm Người Dùng
| Tính năng | Chi tiết |
|:---|:---|
| **Real-time** | Biểu đồ cập nhật tức thì qua WebSocket, không cần F5 |
| **TX Status Badge** | pending → broadcasted → confirmed/failed với animation |
| **MetaMask Events** | Phát hiện đổi ví/đổi mạng ngay lập tức, thông báo user |
| **Voter List** | Danh sách cử tri đã tham gia, copy địa chỉ, link Etherscan |
| **Xác Minh Phiếu** | Trang `/verify/` tra cứu TxHash bất kỳ lúc nào |
| **Toast Notifications** | Thay toàn bộ `alert()` bằng Toastify |
| **Timezone** | Hiển thị giờ Việt Nam (UTC+7) thay vì UTC |

---

## Phần 2: Những Vấn Đề Đã Sửa

### 🔴 Lỗi Nghiêm Trọng
| Lỗi | Giải pháp |
|:---|:---|
| CSRF bị tắt trên `add_whitelist_api` | Bỏ `@csrf_exempt`, JS gửi `X-CSRFToken` header |
| `DJANGO_SECRET_KEY` dùng làm webhook secret | Tách thành `INTERNAL_API_SECRET` riêng |
| Whitelist không retry được khi TX fail | Logic `update_or_create` cho phép retry khi `tx_status='failed'` |
| Indexer mất block khi crash | `IndexerState` lưu checkpoint vào DB, không dùng file txt |
| ERR_BLOCKED_BY_RESPONSE trên IPFS | Chuyển sang `gateway.pinata.cloud` |
| SyntaxError SVG `onerror` | URL-encode dấu ngoặc kép trong attribute |

### 🟡 Cải Thiện Chất Lượng
| Vấn đề | Giải pháp |
|:---|:---|
| N+1 Query | `annotate(total_votes=Sum(...))` trong `get_elections` |
| Web3 khởi tạo mỗi request | Singleton pattern `get_w3()` |
| `ALLOWED_HOSTS = ['*']` | Liệt kê domain cụ thể |
| Không rate-limit | Decorator `rate_limit()` dùng Django cache |
| SystemLog phình vô hạn | `post_save` signal tự trim còn 1000 bản ghi |
| CDN không có SRI | SRI hash cho ethers.js, pin version cho Chart.js + Toastify |
| Địa chỉ ví không validate | Regex `^0x[a-fA-F0-9]{40}$` trước khi insert |

---

## Phần 3: Kiến Trúc Triển Khai (Render + Supabase)

```yaml
# render.yaml — 3 Service độc lập
services:
  - Web Service:    Django + Daphne (ASGI)
  - Worker Service: RQ Worker (xử lý background tasks)
  - Redis:          Channel Layer + Task Queue

databases:
  - PostgreSQL:     Supabase (external)
  
storage:
  - IPFS:           Pinata Cloud (ảnh ứng viên)
  - Blockchain:     Ethereum Sepolia (Alchemy RPC)
```

---

## Phần 4: Giới Hạn Hiện Tại & Hướng Phát Triển

### Giới hạn chấp nhận ở đồ án
- **Nonce in-memory:** `CURRENT_NONCE` dùng RAM — chỉ vấn đề khi scale >1 RQ Worker
- **Contract không emit StatusEvent:** Indexer dùng field `tx_error` để theo dõi — hoạt động ổn nhưng là anti-pattern
- **Không thể xóa whitelist:** Cần sửa Solidity contract để thêm `removeFromWhitelist()`
- **Không phân trang:** API trả toàn bộ elections — ổn ở quy mô đồ án

### Hướng phát triển xem thêm
→ Xem [7_Huong_Phat_Trien.md](./Overview/7_Huong_Phat_Trien.md)
