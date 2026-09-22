@echo off
chcp 65001 >nul
echo =======================================================
echo  KHOI DONG HE THONG BAU CU BLOCKCHAIN (LOCAL DEV)
echo =======================================================

REM Kiem tra Redis dang chay (dich vu bat buoc cho RQ Worker)
where redis-cli >nul 2>&1
if %errorlevel%==0 (
    redis-cli ping >nul 2>&1
    if %errorlevel%==0 (
        echo [OK] Redis dang chay.
    ) else (
        echo [CANH BAO] Redis khong phan hoi! RQ Worker va Indexer co the khong hoat dong dung.
        echo    Chay: redis-server hoac kich hoat Redis trong WSL.
        pause
    )
) else (
    echo [CANH BAO] Khong tim thay redis-cli. Dam bao Redis dang chay tu WSL hoac cai dat rieng.
)

echo.
echo 1. Dang khoi dong Django Web Server (Daphne)...
start "Django Web Server" cmd /k "pipenv run daphne -b 127.0.0.1 -p 8000 core.asgi:application"

echo 2. Dang khoi dong RQ Worker...
start "RQ Worker" cmd /k "pipenv run python manage.py rqworker default"

echo 3. Dang khoi dong Blockchain Indexer...
start "Blockchain Indexer" cmd /k "pipenv run python indexer/indexer.py"

echo.
echo =======================================================
echo  HOAN TAT! 3 cua so Terminal moi da duoc mo.
echo  Moi cua so hien thi log rieng va tu dong dung lai neu gap loi.
echo.
echo  Truy cap: http://127.0.0.1:8000/
echo  Admin:    http://127.0.0.1:8000/admin/
echo  Logs:     http://127.0.0.1:8000/logs/
echo =======================================================
echo.
echo Nhan phim bat ky de dong cua so nay (3 cua so con lai van chay).
pause >nul
