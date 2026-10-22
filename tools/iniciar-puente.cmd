@echo off
REM Inicia el puente NFC del laboratorio con el token guardado en el archivo .env.
REM Uso: doble clic o "iniciar-puente.cmd" desde una terminal.
setlocal
cd /d "%~dp0.."
set "TOKEN="
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
  if "%%a"=="NFC_BRIDGE_TOKEN" set "TOKEN=%%b"
)
if not defined TOKEN (
  echo No se encontro NFC_BRIDGE_TOKEN en el archivo .env.
  echo Copia .env.example a .env y define un token de 32 caracteres o mas.
  pause
  exit /b 1
)
echo Iniciando el puente NFC. Deja esta ventana abierta mientras uses el laboratorio.
echo Para detenerlo pulsa Ctrl+C.
powershell -ExecutionPolicy Bypass -File "%~dp0nfc-bridge.ps1" -Token "%TOKEN%"
echo.
echo El puente se ha detenido.
pause
