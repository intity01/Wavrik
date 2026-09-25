# Loop Memory
Updated continuously by all agents as they discover things.

## Learnings

### Task 1: Core Architecture, Data Persistence & Rule Limits
- [Task 1] **Data Persistence (JsonStore False Quarantine)**: `src/core/json_store.py:26` catches generic `OSError`, which causes transient Windows file locks (`SharingViolation`) to falsely quarantine valid config and history files to `.corrupt` and wipe user data. Atomic loaders should catch `json.JSONDecodeError` specifically.
- [Task 1] **Rule Checker Tool Gap**: `tools/check_rules.py` only validates physical lines/file, lines/func, lines/class, banned tokens, and emoji; it does not validate function parameter counts, allowing violations like `HistoryManager.addEntry` (10 parameters) and `DownloadWorker.__init__` (8 parameters) to slip past CI.
- [Task 1] **Architectural Layer Inversions**: The Core layer violates strict architectural boundaries by depending on outer layers: `src/core/config.py:76` imports UI (`src.ui.macos.appearance`), `src/core/updater.py:14` imports Domain (`src.domain.update_models`), and `src/core/tray.py:9` imports `PyQt6.QtWidgets`.
- [Task 1] **Headless/Windowed Logger Crash**: `src/core/logger.py:30` attaches `sys.stdout` unconditionally without an `if sys.stdout is not None:` guard, which crashes in windowed frozen GUI environments (PyInstaller `-w` / `pythonw`).
- [Task 1] **Approaching Rule Limits**: `src/core/updater.py` (148 lines) and `src/core/config.py` (146 lines) are within 4 lines of the 150-line file cap; `UpdateManager` (119 lines) is 1 line from the 120-line class cap.

### Task 2: Security, Subprocess & Network Integrity
- [Task 2] **SEC-01 (Remote Extension Trust & os.startfile RCE)**: `src/domain/native_paths.py` allows remote server `Content-Disposition` headers to dictate file extensions; paired with `platform_actions.py` invoking `os.startfile` on Windows, a malicious server returning `.bat` or `.exe` achieves arbitrary code execution when the user clicks "Open File". Extensions must be strictly validated against client preset whitelists.
- [Task 2] **SEC-02 (AppleScript Command Injection)**: `src/core/tray.py:53` formats unescaped strings directly into AppleScript `osascript -e 'display notification "{message}"...'`, risking script injection and syntax failures on quotes.
- [Task 2] **SEC-03 (FFmpeg CLI Unbounded Hang)**: `src/domain/native_downloader.py` executes FFmpeg CLI for HLS/DASH streaming without socket network timeouts (`-rw_timeout`) or process timeouts in `communicate()`, causing the worker to hang indefinitely on stalled or disconnected streams.
- [Task 2] **SEC-04 & SEC-06 (Windows Subprocess & DOS Device Traps)**: Subprocesses launched without `creationflags=subprocess.CREATE_NO_WINDOW` flash console windows in frozen GUI mode; `native_paths.py` fails to filter reserved DOS device names (`CON`, `PRN`, `AUX`, `NUL`, etc.), leading to filesystem errors.
- [Task 2] **DEP-01/02 (Vulnerable Dependency Bounds)**: Pinned lower bounds in `requirements.txt` (`yt-dlp>=2024.8.6`, `requests>=2.32,<3`) allow known CVEs (CVE-2024-38519, CVE-2025-54072, CVE-2026-26331, CVE-2024-47081); bounds must be bumped to `yt-dlp>=2026.6.9` and `requests>=2.32.4`.

### Task 3: UI Threading, Worker Safety & Stability
- [Task 3] **ARCH-01 (Qt Thread Safety Violation)**: `src/ui/workers/thumbnail_worker.py:35-37` instantiates and loads `QPixmap` off the main thread in `QThreadPool`. Qt strictly requires GUI paint devices to reside on the main thread; worker threads must handle raw bytes or `QImage` and convert to `QPixmap` via signals on the main thread slot.
- [Task 3] **PERF-02 (Severe UI Thread Freeze)**: `HistoryInterface` connects `searchBar.textChanged` directly to `refresh()` without debouncing. Each keystroke synchronously instantiates up to 1,000 `HistoryCard` composite widgets, each executing `Path.is_file()` twice (up to 2,000 blocking disk I/O calls on the UI thread).
- [Task 3] **PERF-01 (Event Loop Thrashing & Style Invalidation)**: `DownloadWorker._progress` emits progress and status signals on every stream chunk without rate-limiting (hundreds to thousands per second). `QueueItemCard.setStatus` calls `unpolish()` and `polish()` on every status event, thrashing widget styles and freezing the Qt event loop. Must throttle progress to <= 10 Hz and emit status only on state changes.
- [Task 3] **STAB-01 (Cancellation Lag in Backoff)**: `yt_download.py` uses blocking `time.sleep(delay)` during exponential backoff, delaying cancellation response by up to 60s. Must use `owner._cancel.wait(timeout=delay)` for sub-100ms cancellation response.
- [Task 3] **UX-01 (macOS Dialog Cancellation Edge Cases)**: `src/ui/macos/dialogs.py` returns `Path.home() / "Downloads"` on folder picker cancel (silently overwriting custom download paths) and `Path()` on file open cancel (triggering a false URL import error banner).
- [Task 3] **Worker Cancellation State Leaks**: `MetaWorker` exception handler emits user-facing error dialogs even when cancelled; `ThumbnailWorker` runs untracked in `_metaPool` without cancellation handles.
