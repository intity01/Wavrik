# Research Log

## Context & Prior Work
- **Audit Context**: Previous full codebase audit identified critical security vulnerabilities (SEC-01 RCE, DEP-01/02 CVEs), Qt thread-safety violations (ARCH-01 QPixmap in background worker), persistence data loss risks (DATA-01 generic OSError in JsonStore), UI responsiveness freeze (PERF-02 un-debounced search & 2000 disk I/O calls), event loop thrashing (PERF-01 unthrottled signal style thrashing), and cancellation stalls (STAB-01 blocking time.sleep).
- **Patch Goal**: Remediate Phase 1 (critical security & crashes) and Phase 2 (performance & concurrency) items while maintaining 100% compliance with PROJECT_RULES.md (<= 150 lines/file, <= 120 lines/class, <= 35 lines/function, <= 6 params, zero UI slop).

---

## External Knowledge & Resources

### 1. Security & Persistence (SEC-01, DATA-01, DEP-01/02)
- `src/domain/native_paths.py`: Strip server-supplied extensions; strictly enforce user-selected preset container (e.g. `f"{stem}.{fallback_extension}"`); sanitize Windows reserved DOS device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).
- `src/services/platform_actions.py`: Add `BLOCKED_EXTENSIONS` blacklist (`.bat`, `.cmd`, `.exe`, `.ps1`, `.vbs`, `.scr`, `.msi`, `.com`, etc.) to prevent `open_path` from invoking `os.startfile` on dangerous executables.
- `src/core/json_store.py`: Reserve `_backup_corrupt_file()` exclusively for `(json.JSONDecodeError, UnicodeDecodeError)`. Handle `OSError` with retry backoff and return default without wiping user state.
- `requirements.txt`: Bump `yt-dlp>=2026.6.9` and `requests>=2.32.4,<3`.

### 2. Thread Safety & Concurrency (ARCH-01, STAB-01, PERF-01)
- `src/ui/workers/thumbnail_worker.py`: Decode and load image chunks into `QImage` (thread-safe), never `QPixmap`.
- `src/ui/components/queue_card.py`: In `setThumbnail(image: QImage | QPixmap | bytes)`, convert to `QPixmap` on the GUI main thread via `QPixmap.fromImage(image)`. In `setStatus()`, guard `style().unpolish()/polish()` so it only runs when visual `state` actually changes.
- `src/domain/yt_download.py`: Replace blocking `time.sleep(delay)` with `owner._cancel.wait(timeout=delay)` for sub-millisecond cancellation response during backoff.
- `src/ui/workers/download_worker.py`: Throttle progress signal emissions to <= 10 Hz (interval >= 0.1s); deduplicate status signals.

### 3. UI Responsiveness & Subprocesses (PERF-02, SEC-03/04, UX-01)
- `src/ui/pages/history_page.py`: Add 250ms single-shot `QTimer` debounce on `searchBar.textChanged`; paginate initial view to 50 cards with "Load more" button.
- `src/ui/components/history_card.py`: Remove all synchronous `Path.is_file()` disk I/O calls from `__init__`; perform file existence checks on-demand when the user clicks "Open File" or "Open Folder".
- `src/domain/native_downloader.py`: Inject `-rw_timeout 15000000` (15s socket timeout) into FFmpeg CLI; add `timeout=300` to `communicate()`; pass `creationflags=CREATE_NO_WINDOW` on Windows.
- `src/ui/macos/dialogs.py`, `download_options.py`, `input_bar.py`: Return `None` on dialog cancellation across all helpers; guard callers against resetting paths or flashing false error banners.

---

## Requirements & Constraints
- All modified files must remain <= 150 lines.
- All classes <= 120 lines.
- All functions/methods <= 35 lines.
- Zero UI gradients, drop shadows, emojis, or inline style colors.
- Zero print statements in production source.

---

## Verification Criteria
- `python -m compileall -q src main.py` passes with 0 errors.
- `python tools/check_rules.py` and `python tools/check_ai_slop.py` pass with 0 errors.
- `target_path` forces preset extensions, rejects executable extensions, and prefixes Windows DOS device names.
- `open_path` blocks executable extensions.
- `ThumbnailWorker` emits `QImage`, not `QPixmap`.
- Cancellation during backoff returns immediately (< 50ms).
- History search debounces by 250ms and performs 0 synchronous `is_file()` calls on card initialization.
- FFmpeg command includes `-rw_timeout 15000000` and `CREATE_NO_WINDOW` on Windows.
- Dialog cancellations return `None` without side effects.
