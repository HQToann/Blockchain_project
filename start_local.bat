@echo off
chcp 65001 >nul
echo =======================================================
echo KHOI DONG HE THONG BAU CU BLOCKCHAIN LOCAL
echo =======================================================

echo 1. Dang khoi dong Django Web Server...
start "Django Web Server" pipenv run daphne -b 127.0.0.1 -p 8000 core.asgi:application

echo 2. Dang khoi dong RQ Worker...
start "RQ Worker" pipenv run python manage.py rqworker default

echo 3. Dang khoi dong Blockchain Indexer...
start "Blockchain Indexer" pipenv run python indexer/indexer.py

echo.
echo HOAN TAT! 3 cua so Terminal moi da duoc mo de chay ngam 3 dich vu.
echo Truy cap: http://127.0.0.1:8000/
echo.
pause
