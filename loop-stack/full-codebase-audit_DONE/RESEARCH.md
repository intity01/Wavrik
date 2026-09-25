# Research Log

## Context & Prior Work

### Architecture & Layering
MediaDownloaderPRO v2.1 is structured as a layered desktop application built with Python and PyQt6. Its architecture strictly enforces a top-down boundary: UI Layer -> Services Layer -> Domain Layer -> Core Layer.
- **Entry Point**: `Downloader/main.py` initializes `QApplication`, configures app metadata, and launches `MediaDownloaderUI` (`src/ui/main_window.py`).
- **Core Layer (`src/core`)**: `Config` (settings validation), `JsonStore` (atomic JSON persistence via `.tmp` -> `fsync` -> `os.replace`), `Logger` (rotating file handler), `Runtime` (discovering root, ffmpeg, deno), `Parser` (URL validation and normalization), `UpdateManager` (GitHub release verification with SHA-256), `TrayIcon` (system tray and OS notifications).
- **Domain Layer (`src/domain`)**: `MediaDownloader` (orchestrator with per-job session isolation), `yt_options.py` / `yt_download.py` / `yt_format.py` / `yt_policy.py` (yt-dlp integration with exponential backoff), `native_downloader.py` / `native_file.py` / `native_paths.py` (direct HTTP streaming to `.part` and FFmpeg HLS/DASH manifest streaming), `audio_batch.py` (all-audio format batching), `models.py` (typed dataclasses and enums), `presets.py` (28 presets).
- **Services Layer (`src/services`)**: `HistoryManager` (thread-safe RLock history backed by JsonStore), `platform_actions.py` (`open_path`, `open_parent`).
- **UI Layer (`src/ui`)**: `MediaDownloaderUI` (sidebar navigation, QStackedWidget), pages (`WorkspaceInterface`, `HistoryInterface`, `SettingsInterface`), workers (`DownloadWorker`, `MetaWorker`, `ThumbnailWorker` running on `QThreadPool`).

### Prior Issues & Design Decisions
- Centralized download options on the Downloads page.
- Asynchronous "Download all" readiness: items in fetching state automatically queue when metadata is ready.
- Direct media URL fast-path bypasses yt-dlp metadata inspection.
- Pre-flight write permission check before spawning download workers.
- Strict anti-AI-slop rules: max 150 lines per file, max 35 lines per function, max 120 lines per class; no gradients, drop shadows, or emoji icons.

### Architectural Risks & Stability Points
- **ARCH-01**: `ThumbnailWorker.run()` constructs and loads `QPixmap` inside background worker thread, violating Qt thread-safety rules (must use `QImage` in background threads).
- **ARCH-02**: Race condition in `download_files.py:resolve_output()`: fallback to folder `mtime >= started - 2` can misidentify another concurrent download's output.
- **ARCH-03**: macOS folder picker cancellation bug in `src/ui/macos/dialogs.py` silently resets folder to `Path.home() / "Downloads"`.
- **ARCH-04**: Architectural fragmentation due to 150-line caps causing companion classes (`workspace_jobs.py`, `workspace_interactions.py`) to access private properties directly.

---

## External Knowledge & Resources

### External Tools & Libraries
- **PyQt6 (>=6.7,<7)**: Core GUI framework (GPLv3 copyleft obligation if distributed without commercial license).
- **yt-dlp (>=2024.8.6)**: Extraction engine wrapped via `YoutubeDL`. Note: pinned lower bound is vulnerable to CVEs (CVE-2024-38519, CVE-2025-54072, CVE-2026-50023); recommend `>=2026.6.9`.
- **yt-dlp-ejs & Deno (>=2.9,<3)**: JavaScript engine for YouTube signature/EJS challenge solving.
- **requests (>=2.32,<3)**: Direct streaming and update checking. Recommend `>=2.34.2` to resolve CVE-2024-47081.
- **FFmpeg (8.1.1 essentials build)**: Local binary `ffmpeg.exe` (101.5 MB) used for remuxing and HLS/DASH streaming.

### Security Audit Points
- **SEC-01 (High)**: `native_paths.py` allows server `Content-Disposition` to dictate file extension, and `open_path` calls `os.startfile` on Windows. A malicious server returning `.bat` or `.exe` will be executed when the user clicks "Open File" from history.
- **SEC-02 (Medium)**: `tray.py:53` formats unescaped string into AppleScript `osascript -e 'display notification "{message}"...'`, creating syntax error or command injection risks on macOS.
- **SEC-03 (Medium)**: `native_downloader.py` runs `ffmpeg` without network/socket timeout (`-rw_timeout`), hanging indefinitely on stalled HLS streams.
- **SEC-04 (Low)**: Missing `creationflags=subprocess.CREATE_NO_WINDOW` when launching `ffmpeg` via `subprocess.Popen`, causing console flashing in frozen GUI mode on Windows.
- **SEC-05 (Medium)**: CI release workflow bundles `ffmpeg.exe` without cryptographic SHA-256 hash verification.
- **SEC-06 (Low)**: `native_paths.py` does not filter Windows reserved DOS device names (`CON`, `PRN`, `AUX`, `NUL`, etc.).
- **SEC-07 (Low)**: `_ffmpeg_executable()` in `native_downloader.py` hardcodes `ffmpeg.exe` on all OSes.

---

## Requirements & Constraints

### Reliability & Quality Standards
- **Atomic Data Persistence**: `JsonStore` atomic replacement with `.corrupt` quarantine.
- **Physical Line Limits**: Under 150 lines per file, 120 lines per class, 35 lines per function.
- **Banned Visual Patterns**: Zero gradients, zero drop shadows, zero inline stylesheets setting colors, zero emoji icons. Maximum border radius 12px.

### Error Handling & Edge Cases
- **Resume Support**: `native_file.py` direct streaming does not send HTTP `Range` headers; drops wipe `.part` files without resume.
- **Batch Audio Cleanup**: `audio_batch.py` aggressively removes partials between formats.
- **Cancellation Responsiveness**: Blocking `time.sleep(delay)` in `yt_download.py` delays cancellation during exponential backoff sleep (should use `owner._cancel.wait(timeout=delay)`).
- **Progress Signal Flooding**: High-speed downloads emit progress events on every stream chunk without throttling, saturating the GUI thread event loop.
- **History UI Overload**: Non-virtualized history card list rebuilds up to 1,000 cards on every keystroke without debouncing.

### PROJECT_RULES.md Violations
- `DownloadWorker.__init__` in `src/ui/workers/download_worker.py`: Has 8 parameters (limit is 6).
- `HistoryManager.addEntry` in `src/services/history_manager.py`: Has 10 parameters (limit is 6).

---

## Verification Criteria

### What Passing Looks Like:
1. All modules pass static compilation and linting (`compileall`, `check_rules.py`, `check_ai_slop.py`).
2. Function parameter counts <= 6; file lengths <= 150 lines.
3. Thread safety: background workers never allocate `QPixmap` (use `QImage`).
4. Cancellation is responsive within 100ms even during exponential backoff.
5. Path sanitization strictly enforces preset extensions, blocking executable extensions (.exe, .bat, .cmd) and DOS reserved names.
6. Subprocess invocations pass `CREATE_NO_WINDOW` on Windows and socket timeouts to FFmpeg.

### What Failing Looks Like:
1. Remote server controls file extension executed via `os.startfile`.
2. Worker threads manipulate GUI resources (`QPixmap`).
3. GUI freezes during folder checks or unthrottled signal bursts.
4. Hanging subprocesses on network disconnects.

---

## Task-Specific Research — Audit Core Architecture, Data Persistence & Rule Limits
- **Layering Violations**:
  - ARCH-V01: `src/core/config.py:75-79` imports `src.ui.macos.appearance.is_system_dark_mode` (Core -> UI layer inversion).
  - ARCH-V02: `src/core/tray.py` imports `PyQt6.QtWidgets` widgets into Core layer.
  - ARCH-V03: `src/core/updater.py:14` imports `src.domain.update_models` (Core -> Domain layer inversion).
  - ARCH-V04: `src/core/tray.py:50-54` AppleScript execution without timeout or character escaping.
  - ARCH-V05: `src/core/logger.py:30` attaches `sys.stdout` unconditionally without `if sys.stdout is not None:` guard (risks crashing in windowed frozen mode).
- **Data Persistence**:
  - `JsonStore`: Atomic replacement pattern (`.tmp` -> `flush` -> `fsync` -> `os.replace`) verified.
  - Edge case: catching generic `OSError` in `read()` causes transient file locks to falsely trigger `.corrupt` quarantine.
  - `HistoryManager`: Schema 2 migration, 1000 item cap, and `RLock` synchronization verified.
- **Rule Limits**:
  - 100% PASS on file limits (all <= 150 lines), class limits (all <= 120 lines), and function limits (all <= 35 lines).
  - Parameter limit violations: `HistoryManager.addEntry` (10 params), `DownloadWorker.__init__` (8 params), `_attempt` (7 params), `MediaDownloaderUI.__init__` (7 params).

---

## Task-Specific Research — Audit Security, Subprocess & Network Integrity
- **SEC-01 (High RCE)**: `src/domain/native_paths.py:10-15` trusts `Content-Disposition` header extension; paired with `platform_actions.py:17` (`os.startfile`), a server returning `.bat` or `.exe` will be executed when opened from history.
- **SEC-02 (Medium Injection)**: `src/core/tray.py:50-54` formats unescaped string into AppleScript `osascript -e`.
- **SEC-03 (Medium DoS)**: `src/domain/native_downloader.py:68, 76` FFmpeg CLI invocation lacks network timeout (`-rw_timeout`) and `communicate()` timeout.
- **SEC-04 (Low Glitch)**: `native_downloader.py:72-75` missing `creationflags=CREATE_NO_WINDOW` on Windows.
- **SEC-05 (Medium Supply Chain)**: `.github/workflows/release.yml:29-35` packages `ffmpeg.exe` without SHA-256 verification.
- **SEC-06 (Low Traversal)**: Missing Windows reserved DOS device name sanitization (`CON`, `PRN`, `AUX`, `NUL`, etc.) in `native_paths.py`.
- **SEC-07 (Low Portability)**: `native_downloader.py:93-98` hardcodes `ffmpeg.exe` on all platforms.
- **DEP-01 / DEP-02 (CVEs)**: `requirements.txt` lower bounds (`yt-dlp>=2024.8.6`, `requests>=2.32,<3`) allow CVE-2024-38519, CVE-2025-54072, CVE-2026-26331, and CVE-2024-47081. Minimums should be `yt-dlp>=2026.6.9` and `requests>=2.32.4,<3`.
- **STAB-01**: `yt_download.py:28-30` `time.sleep` ignores cancellation during retry backoff.
- **STAB-02**: `updater.py:96` unhandled `ValueError` on malformed Content-Length.

---

## Task-Specific Research — Audit UI Threading, Worker Safety & Stability
- **ARCH-01 (High Safety)**: `src/ui/workers/thumbnail_worker.py:35-37` instantiates and loads `QPixmap` on background thread pool thread. Must use `QImage` in background threads.
- **STAB-01 (Medium Responsiveness)**: `yt_download.py:28-30` blocking `time.sleep(delay)` during exponential backoff. Must use `owner._cancel.wait(timeout=delay)`.
- **PERF-01 (Medium Thrashing)**: `DownloadWorker._progress()` emits status and progress signals on every chunk (up to 400–4000/s), triggering repeated `style().unpolish()` and `style().polish()` in `QueueItemCard.setStatus()`. Must throttle progress signals to <= 10 Hz and only emit status on actual change.
- **PERF-02 (High Freeze)**: `history_page.py` search bar lacks debouncing, instantiates up to 1000 `HistoryCard` composite widgets synchronously, and invokes `Path.is_file()` twice per card on the UI thread (up to 2000 blocking filesystem calls per keystroke).
- **UX-01 (Medium UX)**: `src/ui/macos/dialogs.py` folder picker cancellation silently resets download folder to `~/Downloads`; file open picker cancellation returns `Path()` (`"."`), triggering a false error banner in `input_bar.py`.
- **Worker Lifecycle**: `ThumbnailWorker` is spawned untracked in `_metaPool` without cancellation token; `MetaWorker` error handler emits error even when cancelled.

