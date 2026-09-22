#!/bin/bash
# Script khởi động Production (Render)
# Chạy 3 dịch vụ trong cùng 1 process (Free plan)

set -e  # Dừng nếu có lệnh nào lỗi nghiêm trọng

echo "🚀 Khởi động hệ thống bầu cử Blockchain..."

# --- Hàm restart loop: tự động khởi động lại nếu process crash ---
run_with_restart() {
    local name="$1"
    local cmd="$2"
    while true; do
        echo "[$(date '+%H:%M:%S')] ▶ Khởi động $name..."
        eval "$cmd" || true
        echo "[$(date '+%H:%M:%S')] ⚠️  $name đã dừng. Khởi động lại sau 5 giây..."
        sleep 5
    done
}

# Chạy RQ Worker ngầm với restart loop
run_with_restart "RQ Worker" "python manage.py rqworker default" &

# Chạy Blockchain Indexer ngầm với restart loop
run_with_restart "Indexer" "python indexer/indexer.py" &

# Chạy Django Web Server (foreground — Render cần process này)
echo "🌐 Khởi động Django Web Server trên cổng $PORT..."
exec daphne -b 0.0.0.0 -p "$PORT" core.asgi:application
