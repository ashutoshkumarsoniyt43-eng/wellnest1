@echo off
setlocal
set "PROJECT_DIR=%~dp0model_data"
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0server.py" --project-dir "%PROJECT_DIR%"
) else (
  python "%~dp0server.py" --project-dir "%PROJECT_DIR%"
)
endlocal
