@echo off
REM ==============================================
REM  Website Audit Report Builder - Start Script
REM  Launches both backend (Flask) and frontend (Vite)
REM ==============================================

echo ==============================================
echo   Website Audit Report Builder
echo ==============================================
echo.

echo Starting Flask backend on http://localhost:5000 ...
start "Backend" cmd /c "python run.py"

timeout /t 3 /nobreak > NUL

echo Starting Vite frontend on http://localhost:5173 ...
cd frontend
start "Frontend" cmd /c "npm run dev"
cd ..

echo.
echo ==============================================
echo   Backend:  http://localhost:5000
echo   Frontend: http://localhost:5173  -- open this
echo ==============================================
echo.
echo Close both terminal windows to stop servers.
pause
