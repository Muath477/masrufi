@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist masrufi.Q4_K_M.gguf (
  echo حط ملف masrufi.Q4_K_M.gguf من Google Drive في هذا المجلد اول
  pause
  exit /b
)
ollama create masrufi -f Modelfile
python agent.py
pause
