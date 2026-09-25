# Loop Plan
## Mode
patch
## Goal
Remediate Phase 1 and Phase 2 security, thread safety, and performance audit findings
## Stop Condition
all tasks in loop-stack/remediate-audit-fixes/PLAN.md checked
## Budget
20 turns
## Git Integration
no
## Tasks
- [x] [G1] Remediate Security, Path Sanitization & Persistence: Patch Downloader/src/domain/native_paths.py (SEC-01 preset enforcement & DOS names), Downloader/src/services/platform_actions.py (BLOCKED_EXTENSIONS blacklist), Downloader/src/core/json_store.py (DATA-01 lock-safe retry vs JSONDecodeError), and requirements.txt (DEP-01/02).
- [x] [G1] Remediate Thread Safety, Concurrency & Signal Throttling: Patch Downloader/src/ui/workers/thumbnail_worker.py (ARCH-01 QImage), Downloader/src/ui/components/queue_card.py (QPixmap conversion on UI thread + unpolish guard), Downloader/src/domain/yt_download.py (STAB-01 cancel.wait during backoff), and Downloader/src/ui/workers/download_worker.py (PERF-01 10Hz throttling).
- [x] [G1] Remediate UI Responsiveness, Subprocess Hardening & Dialog Safety: Patch Downloader/src/ui/pages/history_page.py (PERF-02 250ms debounce & 50-card cap), Downloader/src/ui/components/history_card.py (remove sync is_file on init), Downloader/src/domain/native_downloader.py (SEC-03/04 -rw_timeout 15000000, timeout=300, CREATE_NO_WINDOW), and Downloader/src/ui/macos/dialogs.py, Downloader/src/ui/components/download_options.py, Downloader/src/ui/components/input_bar.py (UX-01 None on cancel).
- [x] [G2] Verify Full System Regressions, Static Rules Compliance & Compile Completion Report: Run compileall, check_rules.py (line/param limits), check_ai_slop.py, execute tests, and compile completion findings into loop-stack/remediate-audit-fixes/REPORT.md.
