# Discovered Tools
## Status
CONFIRMED LOCAL — 2026-09-20

## Local tools
- Python 3.14.6: `C:\Users\Intity01\AppData\Local\Programs\Python\Python314\python.exe` (runs only with the host permission needed for executable launch).
- FFmpeg: `ffmpeg.exe` at the project root.
- Git: not available for this directory; `git status` reports that the directory is not a repository.
- Confirmed Python 3.11 runtime: `.venv\Scripts\python.exe` is verified functional with PyQt6 6.8.0, pytest 9.1.1, pytest-qt, requests 2.34.2, and yt-dlp 2026.6.9.
- Python 3.14.6: `C:\Users\Intity01\AppData\Local\Programs\Python\Python314\python.exe` available at system level.

## Project tooling
- Launch source app: `RunApp.bat` from the project root.
- Build Windows package: `build_windows.bat` from the project root.
- Compile: from `Downloader`, `..\.venv\Scripts\python.exe -m compileall -q src main.py tools`.
- Rule check: from `Downloader`, `..\.venv\Scripts\python.exe tools\check_rules.py`.
- AI-slop check: from `Downloader`, `..\.venv\Scripts\python.exe tools\check_ai_slop.py`.
- Tests: from `Downloader`, `..\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-temp-verify`.

## Confirmed dependencies
- `PyQt6 6.8.0`, `pytest 9.1.1`, `pytest-qt`, `requests 2.34.2`, and `yt-dlp 2026.6.9` are installed and verified in `.venv`.

## Relevant project resources
- `README.md`: source setup, usage flow, release and test commands.
- `PROJECT_RULES.md` and `Downloader\PROJECT_RULES.md`: correctness, security, UX, file-size, and definition-of-done rules.
- `Downloader\PROJECT.md`: architecture and worker/thread-pool boundaries.
- `docs\ARCHITECTURE.md` and `docs\GITHUB_UPDATES.md`: design and update-system details.

## Not relevant / unavailable
- No configured Git worktree in the project directory.
- No verified GUI/runtime acceptance tool is available from this Codex session; UI behavior remains unverified until dependencies and an executable app can run.

## Newly Discovered Resources (Online — Unconfirmed Local)

## Resource Usage Guide
- Compile → `python -m compileall -q src main.py`
- Rules → `python tools/check_rules.py`
- AI-slop → `python tools/check_ai_slop.py`
- Ruff → `python -m ruff check src tests`
- Tests → `python -m pytest -q`
