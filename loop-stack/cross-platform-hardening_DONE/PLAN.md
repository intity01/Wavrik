# Loop Plan
## Mode
patch
## Goal
Cross-platform hardening, packaging readiness, and comprehensive test suite expansion
## Stop Condition
all tasks in loop-stack/cross-platform-hardening/PLAN.md checked
## Budget
20 turns
## Git Integration
no
## Tasks
- [x] [G1] Remediate Cross-Platform Binary & Headless Runtime Issues: Patch Downloader/src/domain/native_downloader.py (SEC-07 platform binary naming "ffmpeg.exe" vs "ffmpeg"), Downloader/src/core/logger.py (ARCH-V05 sys.stdout guard in _add_handlers), Downloader/src/core/runtime.py (PyInstaller 6 _internal candidate paths & resource_root), and Downloader/src/services/platform_actions.py (POSIX executable extension blocking).
- [x] [G1] Harden Packaging Config & Repository Distribution Files: Create LICENSE file at project root (MIT License), patch MediaDownloaderPRO.spec to discover Deno in Scripts/ and PATH, and update cross-platform test assertions in tests/test_presets.py and tests/test_media_downloader.py to accept POSIX deno.
- [x] [G2] Implement Comprehensive Phase 3/4 Hardening Test Suite: Create Downloader/tests/test_phase3_phase4_hardening.py with 14 unit tests covering AST parameter rules, AppleScript escaping/timeouts, logger headless execution, cross-platform ffmpeg resolution, and update models identity/immutability.
- [x] [G2] Verify Regressions, Static Rules Compliance & Compile Completion Report: Run compileall, check_rules.py, check_ai_slop.py, pytest (79/79 passing), and write REPORT.md.
