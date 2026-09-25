@echo off
setlocal
cd /d "%~dp0"

echo [1/6] Verifying pre-build requirements...
if not exist ffmpeg.exe (
    echo Error: ffmpeg.exe not found at repository root.
    exit /b 1
)
powershell -NoProfile -Command "$expected = '228D7A8556258DE907FDB55F36850078EBC7680B84EC30D84EA02E99BEC1D1EB'; $actual = (Get-FileHash -Path 'ffmpeg.exe' -Algorithm SHA256).Hash; if ($actual -ne $expected) { Write-Error ('ffmpeg.exe SHA-256 mismatch! Expected: ' + $expected + ' but got: ' + $actual); exit 1 }" || exit /b 1

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
    echo Error: Python 3 was not found.
    exit /b 1
)

echo [2/6] Preparing virtual environment...
if not exist .build-venv (
    "%PYTHON_EXE%" %PYTHON_ARGS% -m venv .build-venv || exit /b 1
)
call ".build-venv\Scripts\activate.bat"
python -m pip install -r requirements-build.txt || exit /b 1

echo [3/6] Running pre-build quality gates...
python -m compileall -q Downloader\src Downloader\main.py || exit /b 1
python Downloader\tools\check_rules.py || exit /b 1
python Downloader\tools\check_ai_slop.py || exit /b 1
python -m pytest -q Downloader\tests || exit /b 1

echo [4/6] Building standalone executable with PyInstaller...
".build-venv\Scripts\pyinstaller.exe" --noconfirm --clean MediaDownloaderPRO.spec || exit /b 1

echo [5/6] Creating release archive and SHA-256 checksum...
powershell -NoProfile -Command "$zip = 'dist\MediaDownloaderPRO-Windows-x64.zip'; $sha = 'dist\MediaDownloaderPRO-Windows-x64.zip.sha256'; Compress-Archive -Path 'dist\MediaDownloaderPRO\*' -DestinationPath $zip -Force; (Get-FileHash -Path $zip -Algorithm SHA256).Hash.ToLower() | Out-File -FilePath $sha -Encoding ascii" || exit /b 1

echo [6/6] Executing smoke test on standalone binary...
"dist\MediaDownloaderPRO\MediaDownloaderPRO.exe" --test-startup || exit /b 1

echo ========================================================
echo Release build and automated verification successful!
echo Binary:   dist\MediaDownloaderPRO\MediaDownloaderPRO.exe
echo Package:  dist\MediaDownloaderPRO-Windows-x64.zip
echo Checksum: dist\MediaDownloaderPRO-Windows-x64.zip.sha256
echo ========================================================
endlocal
