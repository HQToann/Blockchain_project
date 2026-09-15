#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "📦 Đang cài đặt thư viện..."
pipenv install --system --deploy

echo "📦 Gộp file tĩnh (CSS/JS)..."
python manage.py collectstatic --no-input

echo "📦 Tự động tạo bảng trên Database (Supabase)..."
python manage.py migrate
