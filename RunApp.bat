@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE="
set "PYTHON_ARGS="
where py >nul 2>nul
if not errorlevel 1 (
    py -3 --version >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=py"
        set "PYTHON_ARGS=-3"
    )
)
if not defined PYTHON_EXE (
    where python >nul 2>nul
    if not errorlevel 1 (
        python --version >nul 2>nul
        if not errorlevel 1 set "PYTHON_EXE=python"
    )
)
if not defined PYTHON_EXE (
    for /f "delims=" %%P in ('dir /b /s "%LocalAppData%\Programs\Python\Python*\python.exe" 2^>nul') do if not defined PYTHON_EXE (
        "%%P" --version >nul 2>nul
        if not errorlevel 1 set "PYTHON_EXE=%%P"
    )
)
if not defined PYTHON_EXE (
    echo Python 3 was not found.
    echo Install Python from python.org and enable "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating the local environment...
    "%PYTHON_EXE%" %PYTHON_ARGS% -m venv .venv || goto :error
) else (
    echo Testing existing environment...
    ".venv\Scripts\python.exe" --version >nul 2>nul
    if errorlevel 1 (
        echo Existing environment is broken. Recreating...
        rmdir /s /q .venv
        echo Creating the local environment...
          "%PYTHON_EXE%" %PYTHON_ARGS% -m venv .venv || goto :error
    )
)

call ".venv\Scripts\activate.bat"
python -m pip install --disable-pip-version-check -r requirements.txt || goto :error
cd Downloader
python main.py
goto :end

:error
echo.
echo Setup could not be completed. Copy the error above when reporting an issue.
pause
exit /b 1

:end
endlocal
