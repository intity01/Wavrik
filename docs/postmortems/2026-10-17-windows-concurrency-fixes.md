# Post-Mortem: Windows File-Lock, Socket Leak & Cancellation Hardening

- **Status:** Resolved / Verified
- **Date:** 2026-10-17
- **Owner:** Antigravity & Pair Programmer
- **Scope:** Engine & Workers (`Downloader/src/domain/`, `Downloader/src/ui/workers/`, `Downloader/src/ui/pages/`)

---

### 1. Summary
A deep scrutiny pass over the Media Downloader PRO 2.1 backend identified 1 Blocker and 3 Major concurrency/lifecycle issues on Windows: (1) an active file handle lock preventing `.part` deletion and misrepresenting cancellation as a permission error, (2) an unclosed socket stream leak in `ThumbnailWorker`, (3) yt-dlp ignoring cancellation during FFmpeg postprocessing/remuxing, and (4) non-cancellable batch audio rendering. All issues were remediated without violating the strict 150-line limit across all modules, verified with 102 passing test cases and static architectural compliance.

---

### 2. Symptom
1. **Windows Native Cancellation Error:** When a user cancelled an in-flight direct/native download, the card transitioned to `JobState.FAILED` displaying `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process` instead of `Cancelled`.
2. **Resource Exhaustion on Large Queues:** Rapidly queuing playlists with invalid or oversized artwork resulted in stale HTTP socket descriptors held open by `urllib3` until garbage collection.
3. **Unresponsive Cancel during Remuxing:** Clicking Cancel while downloading 1080p/4K YouTube videos or audio extractions had zero effect during FFmpeg merger/transcoding; the background process ran to completion.
4. **Runaway Batch Audio Workloads:** Closing the window or cancelling a batch pitch-shift job left background workers executing all queued audio files.
5. **Transient Save Path Failure:** Concurrently clicking "Download All" on multiple cards occasionally triggered a transient `PermissionError` on the shared `.write_test` file.

---

### 3. Root Cause
1. **File Handle Lock (`native_file.py:61`):** In `_stream()`, when `cancel.is_set()` was detected, `temporary.unlink(missing_ok=True)` was invoked *inside* the `with temporary.open("wb") as handle:` context. On Windows, open file descriptors hold an exclusive lock. Calling `unlink()` raised `PermissionError` (a subclass of `OSError`), which was caught by the generic `except (OSError, NativeDownloadError)` handler and mapped to `JobState.FAILED`.
2. **Missing Stream Teardown (`thumbnail_worker.py:23`):** `requests.get(..., stream=True)` was called without a context manager or a `finally:` block. Early returns on unsupported mime-types or size overflows skipped closing the underlying socket connection.
3. **Missing Postprocessor Hook (`yt_options.py` & `media_downloader.py`):** yt-dlp only had `progress_hooks` registered, which only fires during network chunk transfer. During the postprocessing phase (merging audio/video or converting containers with FFmpeg), `progress_hooks` is dormant.
4. **Lack of Cooperative Cancellation in `BatchAudioWorker`:** The worker loop lacked an internal `_cancelled` boolean flag and a `cancel()` method.
5. **Static File Collision (`workspace_jobs.py:37`):** Write verification used a static filename `output_dir_obj / ".write_test"`. Rapid concurrent invocations created collisions between `.touch()` and `.unlink()`.

---

### 4. Why it Produced the Symptom
- **Windows OS Invariants:** Unlike POSIX systems where unlinking an open file simply detaches its directory inode while allowing the process to hold the descriptor, Windows NT enforces mandatory locking. Attempting deletion of an open handle raises `WinError 32`.
- **yt-dlp Execution Lifecycle:** yt-dlp transitions from downloaders to postprocessors (`PP`). Without a registered `postprocessor_hooks`, user-triggered cancellation events are invisible to the FFmpeg postprocessing pipeline.

---

### 5. Fix
1. **`Downloader/src/domain/native_file.py`:** Removed `temporary.unlink()` from within the `with open` block. Upon cancellation, `_CancelledDownload` is raised immediately, closing the handle. The outer `finally:` block then safely unlinks `temporary` on disk.
2. **`Downloader/src/ui/workers/thumbnail_worker.py`:** Added a defensive `finally: if response is not None and hasattr(response, "close"): response.close()`, guaranteeing socket closure across both normal execution and mock test environments.
3. **`Downloader/src/domain/media_downloader.py` & `yt_options.py` & `yt_download.py`:** Added `_postprocessor_hook` that polls `self._cancel.is_set()` and raises `DownloadCancelled()`. Registered this hook into yt-dlp's `postprocessor_hooks`.
4. **`Downloader/src/ui/workers/batch_worker.py`:** Added `self._cancelled = False`, `cancel()`, and `if self._cancelled: break` inside the processing loop.
5. **`Downloader/src/domain/native_downloader.py`:** Added cancellation pre-check before `Popen()` and protected process termination with `try/except OSError`.
6. **`Downloader/src/ui/pages/workspace_jobs.py`:** Made directory write test probe unique using `output_dir_obj / f".write_test_{time.monotonic_ns()}"`.

---

### 6. How it was Found
- **Diagnostic Method:** Systematic code audit using the upgraded `/scrutinize` 9-vector matrix (Concurrency, Failure Modes, Resource Lifecycle, and `PROJECT_RULES.md` compliance).
- **Traced Seams:** Walked the cancellation propagation flow from `QueueItemCard.cancelRequested` &rarr; `WorkspaceInterface._cancelDownload` &rarr; `DownloadWorker.cancel` &rarr; `MediaDownloader.cancelDownload` &rarr; engine primitives.
- **Hypotheses Tested & Rejected:**
  - *Hypothesis 1 (QThreadPool Thread Starvation):* Investigated whether pool max workers caused cancellation lag. Rejected: pool sizing is 2–4 workers; lag was inside child processes.
  - *Hypothesis 2 (yt-dlp Socket Timeout Hang):* Considered increasing socket timeouts. Rejected: the issue was absence of postprocessor hooks, not network timeouts.

---

### 7. Why it Slipped Through
- **Cross-Platform Discrepancy:** The `temporary.unlink()` pattern works on POSIX/macOS because Linux/Darwin permits unlinking open file descriptors. The bug is Windows-specific and only manifest under runtime cancellation.
- **Mock Test Blindspot:** Existing tests mocked network responses using objects that bypassed the actual Windows filesystem handle locking.

---

### 8. Validation
- **Unit & Integration Suite:** All 102 tests in `Downloader/tests/` passed cleanly in `64.58s`.
- **Static Project Rules (`tools/check_rules.py`):** Verified passed. All 8 modified files strictly adhere to the $\le 150$ physical lines limit (ranges: 33 to 107 lines), zero `print()` statements, and zero inline stylesheets.
- **AI-Slop Check (`tools/check_ai_slop.py`):** Verified passed.
- **Coverage Boundaries:** Validated on Windows 11 x64 environment with Python 3.11 and PyQt6. macOS AppleScript/Menu specifics were verified through existing unit test shims.

---

### 9. Action Items
- [x] Eliminate Windows file handle locking in native downloads. (Merged in current commit)
- [x] Implement socket lifecycle cleanup in thumbnail loaders. (Merged in current commit)
- [x] Wire postprocessor cancellation into yt-dlp options. (Merged in current commit)
- [x] Add cooperative cancellation to `BatchAudioWorker`. (Merged in current commit)
- [ ] Add an automated Windows file-locking regression test specifically asserting unlinking behavior under cancellation. (Target: `tests/test_native_downloader.py`)
