# Research Log

## Context & Prior Work
- **Loop Directory**: `loop-stack/cross-platform-hardening/`
- **Prior Loops Completed**:
  - `full-codebase-audit_DONE`: Cataloged 11 security, threading, and architectural issues.
  - `remediate-audit-fixes_DONE`: Fixed Phase 1 & 2 issues (SEC-01 RCE extension validation, SEC-03/04 FFmpeg timeout/window suppression, ARCH-01 QImage thumbnailing, DATA-01 lock-safe JsonStore, PERF-01 10Hz signal throttling, PERF-02 search debouncing and lazy disk I/O, STAB-01 cancel.wait backoff, UX-01 dialog cancellation returning None, DEP-01/02 dependency version bumps).
  - `arch-rules-hardening_DONE`: Fixed Phase 3 issues (ARCH-V01 config theme decoupling, ARCH-V02 tray icon relocation to UI, ARCH-V03 update models move to Core, SEC-02 AppleScript injection/timeout hardening, RULE-01 parameter dataclasses, SEC-05 release.yml SHA-256 verification, RULE-02 AST parameter limit check <= 6).
- **Current Goals (Phase 4 Cross-Platform Hardening & Packaging Readiness)**:
  1. Fix `SEC-07`: Platform-aware binary naming (`ffmpeg.exe` on win32 vs `ffmpeg` on POSIX) in `Downloader/src/domain/native_downloader.py` and `Downloader/src/core/runtime.py`.
  2. Fix `ARCH-V05`: Headless/windowed GUI execution (`sys.stdout is None`) in `Downloader/src/core/logger.py`.
  3. Packaging & Distribution Hardening:
     - Add missing `LICENSE` file at repository root required by `.github/workflows/release.yml`.
     - Harden `MediaDownloaderPRO.spec` Deno resolution to search both Python directory and `Scripts/` or `shutil.which`.
     - Harden `Downloader/src/core/runtime.py` to check PyInstaller 6 `_internal` and `sys._MEIPASS` directories for bundled binaries and assets.
     - Expand `Downloader/src/services/platform_actions.py` `BLOCKED_EXTENSIONS` with POSIX executables (`.sh`, `.command`, `.app`, `.bin`, `.desktop`, `.run`).
     - Update test assertions in `tests/test_presets.py` and `tests/test_media_downloader.py` to accept POSIX `deno` alongside `deno.exe`.
  4. Comprehensive Test Suite Expansion:
     - Add `Downloader/tests/test_phase3_phase4_hardening.py` providing unit tests for AST parameter rules, AppleScript escaping/timeouts, headless logger stdout handling, cross-platform ffmpeg resolution, and update models identity/immutability.

---

## External Knowledge & Resources

### 1. PyInstaller 6 Asset Directory Layout
- In PyInstaller 6.0+, onedir distributions locate collected files under `_internal`.
- `application_root()` must check `_internal` candidates or `sys._MEIPASS` when frozen:
  `candidates = [application_root() / exe_name, application_root() / "_internal" / exe_name, resource_root() / exe_name]`

### 2. Python Windowed GUI Execution (`pythonw` / `noconsole`)
- When packaged without a console window or executed with `pythonw.exe`, `sys.stdout` and `sys.stderr` are `None`.
- Calling `logging.StreamHandler(sys.stdout)` attempts to write to `None`, raising `AttributeError`. Guard with `if sys.stdout is not None:`.

### 3. Strict Size Limits (`PROJECT_RULES.md`)
- Python files: <= 150 lines.
- Classes: <= 120 lines.
- Functions / methods: <= 35 lines.
- Method parameters: <= 6 (excluding receiver `self` or `cls`).
- Zero `print()` statements, zero UI slop.

---

## Requirements & Constraints

### Task 1: Cross-Platform Runtime & Packaging Hardening (SEC-07, ARCH-V05, Packaging)
1. **`Downloader/src/domain/native_downloader.py`**:
   - Update `_ffmpeg_executable()` to select `"ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"`.
   - File length <= 150 lines (currently 119 -> ~121 lines).
2. **`Downloader/src/core/logger.py`**:
   - In `_add_handlers()`, guard `stream_handler` with `if sys.stdout is not None:`.
   - File length <= 150 lines (currently 55 -> ~58 lines).
3. **`Downloader/src/core/runtime.py`**:
   - Add `resource_root()` helper checking `sys._MEIPASS` or `Path(__file__).resolve().parents[2]`.
   - In `find_ffmpeg()` and `find_deno()`, add candidates for `application_root() / "_internal" / exe_name`.
   - Keep file <= 150 lines (currently 57 lines).
4. **`Downloader/src/services/platform_actions.py`**:
   - Add `.sh`, `.command`, `.app`, `.bin`, `.desktop`, `.run` to `BLOCKED_EXTENSIONS`.
   - Keep file <= 150 lines (currently 37 lines).
5. **`MediaDownloaderPRO.spec`**:
   - Search for Deno in `sys.executable.parent / "Scripts" / "deno.exe"` and `shutil.which("deno")` in addition to `with_name("deno.exe")`.
6. **`LICENSE`**:
   - Create MIT `LICENSE` file at repository root.
7. **Cross-Platform Test Updates**:
   - In `tests/test_presets.py` and `tests/test_media_downloader.py`, assert `.endswith(("deno.exe", "deno"))`.

### Task 2: Comprehensive Test Suite Expansion
1. **`Downloader/tests/test_phase3_phase4_hardening.py`**:
   - 14 tests across the 5 focus areas:
     - AST parameter counter validation (`_param_count`, `_ast_errors`).
     - AppleScript character escaping & timeout error handling.
     - Logger headless execution when `sys.stdout` and `sys.stderr` are `None`.
     - Cross-platform FFmpeg executable resolution.
     - Update models identity, immutability, and safety shims.
   - Strictly <= 150 lines, all test functions <= 35 lines.

### Task 3: Regression Testing, Rule Validation & Completion Report
1. Run `compileall`, `check_rules.py`, `check_ai_slop.py`, `pytest` (expecting ~79/79 passing tests).
2. Generate comprehensive `REPORT.md`.

---

## Verification Criteria
1. **Compilation**: `..\.venv\Scripts\python.exe -m compileall -q src main.py tools tests` exits with 0.
2. **Static Rules**: `tools/check_rules.py` passes with 0 violations.
3. **Anti-Slop**: `tools/check_ai_slop.py` passes with 0 violations.
4. **Pytest Suite**: All tests pass cleanly with 100% success rate.
5. **No Regressions**: Existing 65 tests + 14 new tests = 79 passing tests.
