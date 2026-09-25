# Research Log
## Context & Prior Work
- Candidate: `Downloader/` under the MediaDownloaderPRO v2.1 Windows source tree.
- Binding rules: `Downloader/PROJECT_RULES.md`; Python source limit 150 lines, methods 35 lines, classes 120 lines; no raw user errors, network/UI separation, atomic persistence, and the documented DoD gates.
- Existing work was dirty and not backed by a Git repository in this workspace. Changes were preserved in place; no reset or commit was performed.
## External Knowledge & Resources
- The requested Antigravity `loop-engineer` workflow was initialized under `loop-stack/make-downloader-usable/`.
- Resource-scout delegation was unavailable after bounded attempts because the host could not start the requested subagent model/usage was exhausted. Parent execution retained local evidence instead of treating the delegated status as proof.
## Requirements & Constraints
- Windows first: launch without a terminal, paste a public HTTP(S) URL, choose media/quality/folder, download or receive an actionable failure, open the result, and retain queue/history/settings/update behavior.
- Keep Explorer/normal Windows recovery behavior untouched; do not install/register shell integration or bypass DRM/access controls.
- Use a disposable `.qa-venv` for verification because the checked-in `.venv` points at a missing uv-managed Python 3.11 runtime.
## Task-Specific Research
- Baseline exposed 3 failing UI/preset regressions: retry backoff defaults, Download all state during metadata fetch, and save-folder permission failure escaping a Qt slot.
- Additional red tests reproduced malformed URL ports raising `ValueError` and native `.part` files surviving stream failures.
- Current verified gates: compileall passed; `check_rules.py` passed; `check_ai_slop.py` passed; Ruff passed; full pytest passed with 55 tests.
- Remaining evidence gap: a fresh physical Windows launch and real public-provider download have not yet been exercised in this turn.
