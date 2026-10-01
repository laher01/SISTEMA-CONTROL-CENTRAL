@echo off
setlocal
set "FACT_CENTRAL_ROOT=%~dp0"
cd /d "%FACT_CENTRAL_ROOT%"

where uv >nul 2>nul || (
  echo ERROR: instala uv antes de iniciar FACT CENTRAL.
  echo https://docs.astral.sh/uv/getting-started/installation/
  pause
  exit /b 1
)

where npm >nul 2>nul || (
  echo ERROR: instala Node.js antes de iniciar FACT CENTRAL.
  echo https://nodejs.org/
  pause
  exit /b 1
)

cd backend
if not exist .env copy .env.local.example .env >nul
call uv sync || goto :error
call uv run python -m scripts.inicializar_local || goto :error

cd ..\frontend
call npm ci || goto :error

cd ..
start "FACT CENTRAL - Backend" cmd /k "cd /d ""%FACT_CENTRAL_ROOT%backend"" && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "FACT CENTRAL - Frontend" cmd /k "cd /d ""%FACT_CENTRAL_ROOT%frontend"" && npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo FACT CENTRAL se esta iniciando.
echo Interfaz: http://127.0.0.1:5173
echo API:      http://127.0.0.1:8000/docs
timeout /t 3 >nul
start http://127.0.0.1:5173
exit /b 0

:error
echo.
echo No se pudo iniciar FACT CENTRAL. Revisa el error mostrado arriba.
pause
exit /b 1
