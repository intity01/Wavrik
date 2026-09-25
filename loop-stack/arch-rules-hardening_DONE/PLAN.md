# Loop Plan
## Mode
patch
## Goal
Decouple Core layer inversions, fix parameter limits with dataclasses, and harden AppleScript/CI workflows
## Stop Condition
all tasks in loop-stack/arch-rules-hardening/PLAN.md checked
## Budget
20 turns
## Git Integration
no
## Tasks
- [x] [G1] Remediate Core Layer Inversions & AppleScript Safety: Patch Downloader/src/core/config.py (remove UI theme import), Downloader/src/ui/window_setup.py (add first-run appearance sync), create Downloader/src/ui/components/tray_icon.py with escaped AppleScript and timeout, update Downloader/src/core/tray.py backward shim, create Downloader/src/core/update_models.py, update Downloader/src/domain/update_models.py and Downloader/src/core/updater.py.
- [x] [G1] Remediate Parameter Count Limits with Dataclasses: Add HistoryRecord, DownloadJobConfig, and AttemptContext to Downloader/src/domain/models.py; refactor HistoryManager.addEntry in Downloader/src/services/history_manager.py; refactor DownloadWorker in Downloader/src/ui/workers/download_worker.py and caller in Downloader/src/ui/pages/workspace_jobs.py; refactor _attempt in Downloader/src/domain/yt_download.py; refactor MediaDownloaderUI in Downloader/src/ui/main_window.py and caller in Downloader/main.py.
- [x] [G1] Harden Supply Chain & AST Rules Checking: Patch .github/workflows/release.yml (SHA-256 verification against approved hash 228D7A8556258DE907FDB55F36850078EBC7680B84EC30D84EA02E99BEC1D1EB) and Downloader/tools/check_rules.py (AST parameter count <= 6 check excluding self/cls).
- [x] [G2] Verify Regressions, Static Rules Compliance & Compile Completion Report: Run compileall, check_rules.py, check_ai_slop.py, pytest, and write REPORT.md.
