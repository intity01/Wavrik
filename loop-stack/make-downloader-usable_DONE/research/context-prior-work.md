## Context & Prior Work

### Loop scope

- Goal from `loop-stack/make-downloader-usable/PLAN.md`: make the Windows app usable end-to-end: launch without terminal, paste a supported URL, select media/quality/save location, download or fail clearly, open the result, and keep queue/history/settings/update flows reliable.
- Current loop state from `loop-stack/make-downloader-usable/STATUS.md`: planning in progress, no completed tasks, no prior executor/audit attempts.
- Researcher instruction normally asks for `STATUS.md` heartbeats and `RESEARCH.md` updates, but this spawned task explicitly says not to edit shared `RESEARCH.md` or `STATUS.md`; findings are written only here.

### Entry points and launch/package surface

- Source entry point is `Downloader/main.py`. It creates `QApplication`, `Config`, `Logger`, `HistoryManager`, a shared root `MediaDownloader`, `UpdateManager`, `TrayIcon`, then `MediaDownloaderUI`, starts tray callbacks, shows the main window, and enters the Qt event loop (`Downloader/main.py:18-33`).
- `MediaDownloaderUI` owns the app shell/navigation and creates three pages: Downloads/Workspace, History, and Settings (`Downloader/src/ui/main_window.py:53-67`). It also sets minimum size 760x600 (`Downloader/src/ui/main_window.py:28-30`), applies theme, registers clipboard monitoring, schedules update checks, and cleans up workspace workers on close (`Downloader/src/ui/main_window.py:34-39`, `107-128`).
- User-facing source launcher is `RunApp.bat`. It locates `py` or `python`, creates `.venv` only if `.venv\Scripts\python.exe` is missing, installs `requirements.txt`, then runs `Downloader/main.py` (`RunApp.bat:5-27`). Prior tool discovery says the existing `.venv` launcher is stale and points to a missing uv-managed Python 3.11 runtime; because `RunApp.bat` only checks existence, launch can fail without recreating the environment.
- Windows package build is `build_windows.bat`, which creates `.build-venv`, installs `requirements-build.txt`, and runs PyInstaller with `MediaDownloaderPRO.spec` (`build_windows.bat:4-8`). Prior tool discovery says `.build-venv\Scripts\python.exe` is not executable in the current sandbox, and final packaged EXE launch remains unverified.

### Architecture and boundary map

- Project rules make the app's core flow and boundaries explicit: UI must not do network, yt-dlp, or direct download writes; domain/services must not import UI; each job needs its own session and cancellation token; thread pool must enforce `maxConcurrentDownloads`; completed is valid only when an output file exists (`PROJECT_RULES.md:13-34`).
- `Downloader/PROJECT.md` matches the implementation split: `src/core` for config/runtime/updater/logging, `src/domain` for typed presets and download engine, `src/services` for history and OS file actions, `src/ui/components` and `src/ui/pages` for widgets/pages, and `src/ui/workers` for background QRunnable jobs.
- `docs/ARCHITECTURE.md` documents four layers and top-down dependency flow: UI -> services/domain -> core, with UI isolation, domain independence, and single-session job isolation (`docs/ARCHITECTURE.md`, Architecture Boundaries / Boundary Rules).
- Actual source mostly follows that: UI pages/components wire signals and hold widgets, workers call `MediaDownloader`, domain code calls yt-dlp/requests/FFmpeg, services persist history and open OS paths.

### Downloads page and queue workflow

- `WorkspaceInterface` owns `_cards`, `_metaWorkers`, `_downloadWorkers`, a metadata pool capped at 4, and a download pool capped from `maxConcurrentDownloads` (`Downloader/src/ui/pages/workspace_page.py:21-27`).
- Adding a URL normalizes it, rejects empty/duplicates, creates `QueueItemCard` with the current global preset and engine, wires remove/download/cancel signals, inserts the card, marks `firstRun=False`, updates empty state, then starts metadata fetch (`Downloader/src/ui/pages/workspace_page.py:36-52`).
- Input UI supports manual add, paste from clipboard, and `.txt` import. It validates through `normalizeUrl` and emits normalized URLs only (`Downloader/src/ui/components/input_bar.py:33-83`).
- URL normalization accepts only http/https with hostname, rejects embedded username/password, removes known tracking params, lowercases host/scheme, and preserves path/query (`Downloader/src/core/parser.py:11-30`).
- Download options live on the Downloads page: media type, preset, save location, and an advanced engine selector (`Downloader/src/ui/components/download_options.py:25-54`, `111-123`). Preset/engine changes persist to config and emit to queued cards (`Downloader/src/ui/components/download_options.py:99-109`).
- `_applyPresetToQueued` and `_applyEngineToQueued` call every card, but `QueueItemCard.setPreset/setEngine` no-op for active or completed items; this snapshots options for active jobs while letting pending/failed/cancelled items update (`Downloader/src/ui/pages/workspace_interactions.py:42-48`; `Downloader/src/ui/components/queue_card.py:46-58`).
- `Download all` iterates cards and calls `beginDownload()` only if each card is downloadable (`Downloader/src/ui/pages/workspace_interactions.py:37-40`). Queue button state is based on `any(card.isDownloadable())` (`Downloader/src/ui/pages/workspace_interactions.py:50-57`), while `DownloadOptions.setQueueState()` only shows the batch button when count > 1 (`Downloader/src/ui/components/download_options.py:125-131`).
- A card starts as `fetching`, disables its action until ready/failed/cancelled, treats queued/downloading/processing as active, and maps the primary action to Download, Cancel, Retry, or Open folder (`Downloader/src/ui/components/queue_card.py:15-23`, `84-113`, `116-136`).

### Metadata and playlist workflow

- `workspace_jobs.startMetadata()` creates a fresh `WorkerSignals`, a `MetaWorker` with `page._dl.newSession()`, wires meta/thumbnail/status/error/playlist signals, records it in `_metaWorkers`, and starts it on `_metaPool` (`Downloader/src/ui/pages/workspace_jobs.py:11-20`; `Downloader/src/ui/workers/meta_worker.py:10-18`).
- `MetaWorker.run()` emits `fetching`, calls `MediaDownloader.inspect()`, then emits either playlist data or video metadata plus `ready`; thumbnails are delegated to `ThumbnailWorker` on the same pool passed in (`Downloader/src/ui/workers/meta_worker.py:24-44`).
- Playlist handling removes the original card, shows a `PlaylistBanner`, and adds all entry URLs when requested (`Downloader/src/ui/pages/workspace_interactions.py:10-16`). `_map_entries()` uses `webpage_url` or `url` for each entry (`Downloader/src/domain/media_downloader.py:162-163`).

### Download workflow and engines

- `workspace_jobs.startDownload()` resolves the selected preset, calls `config.getDownloadPath(preset.media_type)`, creates `DownloadWorker`, wires progress/status/error/finished signals, stores it by URL, and starts it on `_downloadPool` (`Downloader/src/ui/pages/workspace_jobs.py:23-39`).
- `Config.getDownloadPath()` appends `Audio` or `Videos` under `downloadPath` and creates the directory immediately (`Downloader/src/core/config.py:98-102`).
- `DownloadWorker` creates its own downloader session in `__init__`, emits "Starting with Auto/Native/yt-dlp", calls `MediaDownloader.download()`, records history for every result, then emits finished (`Downloader/src/ui/workers/download_worker.py:12-31`, `42-55`).
- `DownloadWorker._record()` writes URL, title, media type, preset plus actual engine, file path, file size if present, state/status, error, and thumbnail path to `HistoryManager` (`Downloader/src/ui/workers/download_worker.py:57-78`).
- `MediaDownloader.download()` chooses engine: explicit `native`, explicit `yt-dlp`, or Auto. Auto tries native only when `native_kind(url)` recognizes direct file/HLS/DASH; otherwise it goes straight to yt-dlp. If Auto native fails non-cancelled, it falls back to yt-dlp; explicit Native returns the native result (`Downloader/src/domain/media_downloader.py:72-85`).
- Native recognizes file extensions and `.m3u8`/`.mpd` without fetching (`Downloader/src/domain/native_downloader.py:23-32`). Direct native file downloads use `requests.get(..., stream=True, timeout=(10, 60), User-Agent=MediaDownloaderPRO/2.1)`, reject 401/403 and `text/html`, write `.part`, delete partials on cancel, then atomically replace to target (`Downloader/src/domain/native_downloader.py:61-98`).
- Native manifest downloads require FFmpeg, run `ffmpeg -y -nostdin -i URL -map 0 -c copy target`, report protected/expired/access failures, and require a non-empty output file (`Downloader/src/domain/native_downloader.py:100-130`).
- yt-dlp options set format, outtmpl, progress hooks, `continuedl`, `noplaylist`, Windows filenames, timeouts/retries, no skipped fragments, optional Deno runtime, optional FFmpeg location, optional cookie file, thumbnail options, and preset postprocessors/merge format (`Downloader/src/domain/yt_options.py:36-68`, `71-95`, `97-123`).
- yt-dlp output resolution checks requested download paths, `_filename`/`filepath`, audio postprocessor suffixes, then falls back to the newest file in the output folder with mtime at or after `started - 2` (`Downloader/src/domain/media_downloader.py:87-110`, `130-142`).

### History/open-result workflow

- Completed card action opens the parent folder when `_file_path` exists (`Downloader/src/ui/components/queue_card.py:100-113`).
- `HistoryManager` loads/migrates history, backs up corrupt/unsupported schema files, caps history at 1000 entries, and persists atomically through `JsonStore` (`Downloader/src/services/history_manager.py:25-53`, `55-80`; `Downloader/src/core/json_store.py:30-38`).
- History page filters by title/URL/media/status, refreshes when navigated to, and shows summary plus empty states (`Downloader/src/ui/pages/history_page.py:75-107`, `122-129`; `Downloader/src/ui/main_window.py:86-88`).
- `HistoryCard` shows open-file/open-folder actions only when the recorded `filePath` still exists; otherwise it offers Download again if a URL exists and warns when a completed file is no longer available (`Downloader/src/ui/components/history_card.py:41-80`).
- OS open helpers return false when the path does not exist and use `os.startfile` on Windows (`Downloader/src/services/platform_actions.py:11-30`).

### Existing tests and what they cover

- UI smoke tests cover beginner add/download/history with a fake downloader, invalid/duplicate URL messaging, history redownload, options on workspace, queued-item preset/engine snapshot, disabled download before metadata ready, toggles, compact empty queue, disabled updater when unconfigured, and empty history text (`Downloader/tests/test_ui.py:20-124`).
- Domain tests cover URL validation, metadata inspect for video/playlist, mocked yt-dlp download success, output resolution candidate/mtime/collision fallback, friendly errors, and Deno option injection (`Downloader/tests/test_media_downloader.py:10-137`).
- Parser tests cover allowed public http/https, tracking param removal, rejected file/ftp/credential URLs, and import de-duplication (`Downloader/tests/test_parser.py:4-20`).
- Native downloader tests cover `native_kind`, direct file save/progress, and actionable rejection of HTML/page URLs (`Downloader/tests/test_native_downloader.py:10-54`).
- History tests cover actual file path/stats/schema writes and corrupted/invalid settings/history recovery (`Downloader/tests/test_history.py:8-55`).
- Preset tests cover audio/video option separation, retry settings, and Deno path (`Downloader/tests/test_presets.py:7-27`).
- Updater tests cover GitHub headers, version comparison, verified SHA-256 package download, unverified release blocking, and unconfigured no-network behavior (`Downloader/tests/test_updater.py:61-104`).
- Test fixtures run Qt offscreen and use `FakeDownloader`, which writes a local dummy output and returns completed results (`Downloader/tests/conftest.py:4-55`). This means the UI tests do not exercise real yt-dlp, native requests, FFmpeg, packaged launch, Windows file opening, real clipboard UX, or physical rendering.

### Concrete source-level risks and missing behavior that can block the user flow

1. Stale `.venv` blocks "launch without terminal": `RunApp.bat` does not verify that `.venv\Scripts\python.exe` can actually run; it skips environment recreation if the file exists (`RunApp.bat:19-25`). Loop tools already recorded this checkout's `.venv` as stale/missing its uv-managed Python runtime.
2. Packaging and GUI runtime are unverified in this environment: current local tools say host Python can compile/check some things but PyQt6/pytest/Ruff are missing, `.build-venv` is not executable, and no GUI acceptance tool is confirmed. Do not claim end-to-end usability until a packaged or source GUI run is physically verified.
3. `Config.getDownloadPath()` creates folders before the worker starts (`Downloader/src/core/config.py:98-102`). If the selected save location is unavailable or unwritable, the failure can happen during UI-side `startDownload()` (`Downloader/src/ui/pages/workspace_jobs.py:27-30`) before the worker/history/error path handles it. Executor should make folder failures actionable and not crash the click path.
4. `DownloadWorker.run()` does not wrap `downloader.download()` or `_record()` in `try/except` (`Downloader/src/ui/workers/download_worker.py:42-55`). Unexpected domain/history/file stat errors can kill a worker without emitting a friendly card error or history entry.
5. Finished/error signal order can overwrite useful failure text. `_record()` emits `signals.error(url, result.error)` for failures (`Downloader/src/ui/workers/download_worker.py:73-78`), then `run()` emits `finished`, and `_onFinished()` calls `card.finish(result)` (`Downloader/src/ui/pages/workspace_page.py:115-120`). `QueueItemCard.finish()` then sets status to `result.state.value` (`Downloader/src/ui/components/queue_card.py:100-105`), likely replacing the actionable error with plain `Failed`.
6. Cancelled jobs are recorded in history even when cancelled before run starts (`Downloader/src/ui/workers/download_worker.py:43-48`, `57-72`). That may be acceptable, but if users cancel queued items frequently, history may fill with low-value cancelled rows. Verifier should confirm expected product behavior.
7. Metadata failure message is generic and discards cause (`Downloader/src/ui/workers/meta_worker.py:44-45`). For the main flow, unsupported/login/geo/rate-limited/cookie-needed metadata failures may all look the same, reducing "fail clearly."
8. Metadata fetch is always yt-dlp; Auto/Native does not skip inspection for direct files (`Downloader/src/ui/workers/meta_worker.py:29-40`; `Downloader/src/domain/media_downloader.py:42-55`). A direct media URL that native could download may be blocked at the metadata stage if yt-dlp cannot inspect it, because the card never reaches `ready`.
9. Native direct-file fallback can produce misleading duplicate work in Auto. Auto tries native for recognized media extensions, but if native downloads most of a file then fails before replace, it falls back to yt-dlp unless cancelled (`Downloader/src/domain/media_downloader.py:77-85`; `Downloader/src/domain/native_downloader.py:61-98`). Ensure partial cleanup and user messaging are verified for network interruption and permission failures.
10. yt-dlp output resolution fallback may pick the newest unrelated file in the output folder if info paths are missing (`Downloader/src/domain/media_downloader.py:130-142`). Tests cover this fallback as designed, but the behavior is risky in a real shared Downloads folder and could mark the wrong file completed.
11. Completed card "Open folder" ignores the boolean from `open_parent()` and does not surface failure (`Downloader/src/ui/components/queue_card.py:106-113`; `Downloader/src/services/platform_actions.py:27-30`). If the file is moved/deleted after completion, the card may appear to do nothing; History handles missing files better (`Downloader/src/ui/components/history_card.py:74-80`).
12. `Download all` button is hidden for a single queue item (`Downloader/src/ui/components/download_options.py:125-128`). That is probably intentional, but tests assert the button is enabled after adding one item (`Downloader/tests/test_ui.py:50-66`) without checking visibility, so visible user behavior may not match test intent.
13. Clipboard monitoring validates against the shared root downloader (`Downloader/src/ui/main_window.py:112-118`) and then asks the user via banner. It is read-only, but duplicated clipboard banners can accumulate because only duplicate queued URLs are checked (`Downloader/src/ui/pages/workspace_interactions.py:18-24`).
14. Update manager is disabled while `Config.GITHUB_REPO` is empty (`Downloader/src/core/config.py:36-39`; `Downloader/tests/test_ui.py:109-118`). That is correct for unreleased source, but package release readiness requires setting the repo before build.
15. Prior memory warns not to integrate or rely on private cloud conversion endpoints: discovered `/api/wav/start` and `/api/wav/progress` behavior was passive evidence only, not a public authorized API. Native routing does not solve ordinary YouTube page URLs or YouTube 403.

## Existing Tools & Resources

- Confirmed local files/resources: `README.md`, `PROJECT_RULES.md`, `Downloader/PROJECT.md`, `docs/ARCHITECTURE.md`, `docs/GITHUB_UPDATES.md`, source/tests under `Downloader/src` and `Downloader/tests`.
- Confirmed local runtime/tooling from loop tools: `ffmpeg.exe` exists at project root; host Python 3.14.6 exists but executable launch was denied in this sandbox during this pass; PyQt6/pytest/Ruff are unavailable to the host interpreter per loop tool inventory.
- Existing libraries in source: PyQt6 for UI, yt-dlp for compatibility downloads, requests for native direct file downloads, FFmpeg for HLS/DASH manifests, Deno/yt-dlp-ejs support through yt-dlp `js_runtimes`.
- I did not add new online resources to TOOLS because this pass was source-context research only and no new external dependency was needed.

## Requirements & Constraints

- Preserve app layering: UI cannot directly perform network/download file writes; workers/domain should own expensive/network operations.
- Main user journey must work without terminal: launch app, paste supported URL, select output options/save location, download or fail clearly, open result.
- Keep one session/cancellation token per job; keep `maxConcurrentDownloads` enforced by download pool.
- Completed state must mean an actual output file was found.
- Errors shown to users must be actionable and avoid raw exceptions.
- Do not add DRM bypass or private/unauthorized cloud conversion behavior.
- Maintain project rules: production file/function/class size limits, no gradients/AI-slop UI patterns, atomic persistence, no secret query logging, and release updater SHA-256 safety.

## Suggested Approach

First fix launch/runtime gating and the direct URL metadata/download path, because those determine whether the basic user flow can start at all. Then harden worker exception/error propagation so failures remain visible and actionable, and add regression tests for save-folder failure, direct media URL readiness, failure message preservation, and open-result missing-file behavior.

## Verification Criteria

- Source launch path: `RunApp.bat` handles a stale/broken `.venv` by recreating or reporting a clear setup action; source app opens without requiring a terminal workaround.
- Queue path: adding a valid supported URL produces a card, finishes metadata or gives a specific actionable metadata error, and enables Download only when appropriate.
- Direct media path: a public direct `.mp4`/audio URL can become downloadable without being blocked solely by yt-dlp metadata inspection.
- Download path: choosing a save folder that is missing/unwritable fails visibly on the card and records useful history, not an unhandled worker crash.
- Completion path: completed card opens a folder or reports that the file is missing; History shows file state accurately.
- Failure path: failed downloads preserve the domain/native friendly error text after the worker finishes.
- Tests/gates when dependencies are available: compileall, rule check, AI-slop check, Ruff, pytest, and at least one real GUI/package smoke test on Windows.

## Quality Standards

- Prefer small fixes along current boundaries: page/worker signal handling in UI, download mechanics in domain, persistence in services/core.
- Keep tests close to the behavior: fake downloader for UI state, mocked requests/yt-dlp for deterministic domain cases, and one real runtime smoke when the environment is repaired.
- Preserve user's settings/history data; use backups/atomic writes as already designed.
- Avoid broad refactors until the basic user journey is verified.
- Treat previous successful unit tests as narrow evidence only; they do not prove physical Windows usability or packaged launch.

## Prior Attempt Analysis

- No executor attempt is recorded in this loop status yet.
- Prior project memory indicates successful/partial older work on multi-engine routing and yt-dlp reliability, but final packaged EXE launch was unverified. It also recorded legal/API boundaries around private cloud converter endpoints: passive endpoint discovery is not authorization, and native routing does not fix YouTube 403/page URL restrictions.
