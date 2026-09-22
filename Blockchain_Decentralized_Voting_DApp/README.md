# README — Hướng Dẫn Đọc Tài Liệu Dự Án

## Dự án: Hệ Thống Bỏ Phiếu Phi Tập Trung (Decentralized Voting DApp)

> **Tóm tắt:** Ứng dụng bỏ phiếu trực tuyến kết hợp Blockchain (Ethereum Sepolia) và Django Web Framework. Mỗi phiếu bầu là một giao dịch on-chain — bất biến, minh bạch, không thể giả mạo.

---

## Đọc theo thứ tự này nếu bạn mới tiếp cận dự án:

### 📖 Hiểu dự án (Đọc trước)
| Thứ tự | File | Nội dung |
|:---:|:---|:---|
| 1 | [project_summary.md](./project_summary.md) | **Bắt đầu tại đây** — Tổng kết toàn bộ dự án, tính năng, vấn đề đã sửa |
| 2 | [Overview/1_Tong_Quan_Du_An.md](./Overview/1_Tong_Quan_Du_An.md) | Kiến trúc 5 tầng, luồng dữ liệu chi tiết, tính năng |
| 3 | [Overview/5_Cong_Cu_Va_Thu_Vien.md](./Overview/5_Cong_Cu_Va_Thu_Vien.md) | Tech stack, cấu trúc thư mục thực tế, biến môi trường |

### 🛠️ Chạy dự án
| Thứ tự | File | Nội dung |
|:---:|:---|:---|
| 4 | [Overview/6_Huong_Dan_Chay_Local.md](./Overview/6_Huong_Dan_Chay_Local.md) | Cài đặt từ đầu, chạy local Windows, URL truy cập |

### 📐 Chi tiết kỹ thuật (Đọc sâu hơn)
| File | Nội dung |
|:---|:---|
| [Overview/2_Smart_Contract.md](./Overview/2_Smart_Contract.md) | Solidity: `ElectionFactory.sol` + `Election.sol` |
| [Overview/3_Backend_API.md](./Overview/3_Backend_API.md) | API Endpoints, Django Models, Tasks, Web3 Auth |
| [Overview/4_Frontend_Web3.md](./Overview/4_Frontend_Web3.md) | Ethers.js, MetaMask flow, WebSocket, Chart.js |

### 🚀 Phát triển tương lai
| File | Nội dung |
|:---|:---|
| [Overview/7_Huong_Phat_Trien.md](./Overview/7_Huong_Phat_Trien.md) | ZKP, L2, DAO Governance, Mobile App |

---

## Truy Cập Nhanh

```
Trang chủ:        /
Chi tiết bầu cử:  /election/<id>/
Xác minh phiếu:   /verify/
Admin Panel:      /admin/
System Logs:      /logs/
```

## Công Nghệ Cốt Lõi

```
Blockchain:  Solidity + Hardhat + Ethereum Sepolia
Backend:     Python + Django 5 + Daphne + django-rq
Database:    PostgreSQL (Supabase) / SQLite (local)
Frontend:    HTML + Vanilla JS + Ethers.js v6 + Chart.js
Real-time:   Django Channels + Redis (WebSocket)
Storage:     Pinata IPFS (ảnh ứng viên)
Deploy:      Render (Web + Worker + Indexer)
```
