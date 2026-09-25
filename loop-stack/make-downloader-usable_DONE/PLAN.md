# Loop Plan
## Mode
patch
## Goal
Make MediaDownloaderPRO usable end-to-end on Windows: launch without terminal, paste a supported URL, select media/quality/save location, download or fail clearly, open the result, and keep queue/history/settings/update flows reliable. Preserve security and existing project rules; fix code, docs, and tests as needed.
## Stop Condition
all tasks in loop-stack/make-downloader-usable/PLAN.md checked
## Budget
20 turns
## Git Integration
no
## Tasks
- [x] [G1] Establish the Windows candidate, binding rules, available runtime, and a reproducible QA environment.
- [x] [G1] Repair queue/download option state, folder-access failures, worker error propagation, and launcher interpreter detection.
- [x] [G2] Add regression coverage for malformed ports, native partial-file cleanup, direct-media metadata, and actionable UI failures.
- [x] [G2] Refactor oversized domain/UI/macOS modules without changing the tested workflow.
- [x] [G3] Run compile, project-rule, anti-slop, Ruff, and full regression gates.
- [x] [G3] Exercise the entry point offscreen and inspect launcher prerequisites; attempt physical Windows UI verification and record the unavailable CUA surface.
- [x] [G3] Perform the final audit, update implementation documentation, and separate verified from unverified scope.
