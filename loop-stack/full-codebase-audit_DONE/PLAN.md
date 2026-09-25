# Loop Plan
## Mode
audit
## Goal
Full codebase audit: evaluate code quality, error handling, security, and UI/backend stability of MediaDownloaderPRO
## Stop Condition
all tasks in loop-stack/full-codebase-audit/PLAN.md checked
## Budget
20 turns
## Git Integration
no
## Tasks
- [x] [G1] Audit Core Architecture, Data Persistence & Rule Limits: evaluate src/core (config, json_store, logger, runtime, parser, update_manager, tray), services (history_manager), check atomic persistence and corruption fallback in JsonStore, and verify PROJECT_RULES compliance (150 line/file, 35 line/func, 120 line/class limits, parameter count <= 6 using check_rules.py and check_ai_slop.py) in Downloader/
- [x] [G1] Audit Security, Subprocess & Network Integrity: evaluate yt-dlp options/policies, FFmpeg CLI subprocess invocation (CREATE_NO_WINDOW, timeouts), native HTTP/HLS streaming (native_downloader, native_file, native_paths), URL validation (Parser), update manager release verification (SHA-256), path sanitization against arbitrary execution (SEC-01 Content-Disposition / os.startfile, DOS device names), and dependency CVE bounds (yt-dlp, requests)
- [x] [G1] Audit UI Threading, Worker Safety & Stability: evaluate PyQt6 concurrency in src/ui/workers (DownloadWorker, MetaWorker, ThumbnailWorker), verify thread safety (QPixmap vs QImage in background worker ARCH-01), cancellation responsiveness during backoff (yt_download), progress signal emission throttling, history search debouncing/virtualization limits, and macOS dialog edge cases
- [x] [G2] Consolidate Full Codebase Audit Matrix & Risk Prioritization Report: synthesize findings from [G1] core architecture, security/subprocess integrity, and UI threading audits into REPORT.md in loop-stack/full-codebase-audit/ with severity classifications (Critical, High, Medium, Low), concrete file/line evidence, and recommended remediation roadmap
