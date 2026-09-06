@echo off
setlocal EnableExtensions

set "BACKEND=C:\Users\Armaan\Documents\train-info-finder\backend"
set "PYTHON=%BACKEND%\venv\Scripts\python.exe"
set "SCRIPT=%BACKEND%\sync_rail_data.py"
set "LOG=%BACKEND%\data_sync_task.log"

>> "%LOG%" echo.
>> "%LOG%" echo ==========================================================
>> "%LOG%" echo [%date% %time%] Scheduled data sync starting

if not exist "%PYTHON%" (
    >> "%LOG%" echo [%date% %time%] ERROR: Python not found at %PYTHON%
    exit /b 1
)

if not exist "%SCRIPT%" (
    >> "%LOG%" echo [%date% %time%] ERROR: sync_rail_data.py not found at %SCRIPT%
    exit /b 1
)

cd /d "%BACKEND%"

"%PYTHON%" "%SCRIPT%" >> "%LOG%" 2>&1
set "EXITCODE=%ERRORLEVEL%"

>> "%LOG%" echo [%date% %time%] Scheduled data sync finished with code %EXITCODE%

endlocal & exit /b %EXITCODE%
