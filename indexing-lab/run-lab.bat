@echo off
rem ============================================================
rem  Bookvice indexing lab - run everything and save results
rem  Double-click this file. Results go to the "results" folder.
rem  First run seeds 1,000,000 bookings: allow 2-5 minutes.
rem ============================================================
cd /d "%~dp0"

echo.
echo === 1/4 Start 2 PostgreSQL containers (with index / no index) ===
rem Start from a clean database every time, so results always match the SQL files
rem (init scripts only run on an empty volume). Seeding takes about 1 minute.
docker compose down -v >nul 2>&1
docker compose up -d
if errorlevel 1 goto nodocker

echo.
echo === 2/4 Wait until both databases finish seeding ===
call :waitdb bv_lab_index
if errorlevel 1 goto timeout
call :waitdb bv_lab_noindex
if errorlevel 1 goto timeout

echo.
echo === 3/4 Run labs ===
if not exist results mkdir results
call :run 01-explain    bv_lab_index   index
call :run 01-explain    bv_lab_noindex noindex
call :run 02-size       bv_lab_index   index
call :run 02-size       bv_lab_noindex noindex
call :run 03-old-vs-new bv_lab_index   index
call :run 04-pitfalls   bv_lab_index   index
call :run 05-insert-cost bv_lab_index  index
call :run 05-insert-cost bv_lab_noindex noindex
call :run 06-usage      bv_lab_index   index

echo.
echo === 4/4 Done ===
echo Results saved in: %cd%\results
echo Tell Claude "run-lab finished" so the report can be written from these numbers.
pause
exit /b 0

rem ------------------------------------------------------------
:waitdb
set tries=0
:waitloop
docker exec %1 psql -U student -d appdb -tAc "SELECT 'READY' FROM lab_ready" 2>nul | findstr READY >nul
if not errorlevel 1 (
  echo   %1 is ready
  exit /b 0
)
set /a tries+=1
if %tries% geq 120 exit /b 1
echo   %1 still seeding ... (%tries%)
timeout /t 5 /nobreak >nul
goto waitloop

:run
echo   %1 on %2
docker exec -i %2 psql -U student -d appdb -f /labs/%1.sql > "results\%1_%3.txt" 2>&1
exit /b 0

:nodocker
echo.
echo Docker did not start. Open Docker Desktop first, then run this file again.
pause
exit /b 1

:timeout
echo.
echo Seeding took longer than 10 minutes. Check: docker compose logs bv_lab_noindex
pause
exit /b 1
