# Loop Memory
Updated continuously by all agents as they discover things.
## Learnings

### Completed Engineering Fixes (2025-09-20)

1. **RunApp.bat environment verification**: Added check to test if existing `.venv\Scripts\python.exe` is actually executable before using it. If it fails, the script now recreates the environment automatically. This fixes the "stale .venv blocks launch without terminal" issue.

2. **Direct media URL metadata routing**: Modified `MetaWorker.run()` to check if URLs are direct media files using `native_kind()` before attempting yt-dlp inspection. Direct `.mp4`, `.mp3`, etc. URLs now bypass yt-dlp metadata and become ready immediately, enabling native downloads without unnecessary inspection failures.

3. **DownloadWorker exception handling**: Wrapped `downloader.download()` and `_record()` calls in try/except blocks in `DownloadWorker.run()`. Unexpected domain/history/file errors now emit friendly error messages instead of crashing the worker silently.

4. **Error signal order preservation**: Changed signal emission order in `DownloadWorker.run()` to emit error signals before finished signals for failed states. Modified `QueueItemCard.finish()` to preserve specific error messages instead of overwriting them with generic "Failed" text.

5. **Config folder creation failure handling**: Added pre-validation in `workspace_jobs.startDownload()` to test folder creation and write permissions before starting the download worker. If folder creation fails, the card now shows a specific error message instead of the worker crashing.

6. **Completed card missing file handling**: Modified `QueueItemCard._handle_action()` to check if the file still exists before attempting to open its parent folder. If the file is missing, the card now transitions to failed state with a clear error message instead of silently doing nothing.

7. **Metadata error message specificity**: Changed `MetaWorker.run()` exception handling to include the actual exception message in the error signal, providing more actionable feedback for users.

8. **Regression tests added**: Added 5 new tests in `test_ui.py`:
   - `test_folder_creation_failure_shows_error_on_card`: Verifies folder permission errors are shown on cards
   - `test_direct_media_url_becomes_ready_without_yt_dlp`: Confirms direct media URLs bypass yt-dlp inspection
   - `test_download_worker_exception_handling`: Tests that unexpected exceptions are caught and reported
   - `test_error_message_preserved_after_finish`: Ensures specific error messages are preserved
   - `test_completed_card_handles_missing_file`: Verifies missing file scenarios are handled gracefully

### Remaining Issues from Research

The following issues from the original research remain unaddressed but were deemed lower priority for this fix iteration:
- Download all button visibility for single items (design decision needed)
- Clipboard monitoring duplicate banners (UX improvement)
- Update manager GITHUB_REPO configuration (release preparation task)
- Native direct-file fallback duplicate work (edge case improvement)
- yt-dlp output resolution fallback risk (shared folder edge case)
- Cancelled jobs in history (product behavior decision needed)
