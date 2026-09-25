# Research Log

## Context & Prior Work
- **Loop Directory**: `loop-stack/arch-rules-hardening/`
- **Prior Loop Achievements**:
  - `full-codebase-audit_DONE`: Comprehensive audit identified architectural boundary leaks, parameter limit violations, subprocess vulnerabilities, and missing supply-chain checks.
  - `remediate-audit-fixes_DONE`: Implemented and verified Phase 1 & 2 fixes (SEC-01 RCE extension validation, SEC-03/04 FFmpeg timeout and window suppression, ARCH-01 QImage background thumbnailing, DATA-01 lock-safe JsonStore, PERF-01 10Hz signal throttling, PERF-02 search debouncing and lazy disk I/O, STAB-01 instant cancellation during backoff, UX-01 dialog cancellation returning None, DEP-01/02 dependency version bumps).
- **Current Objectives (Phase 3 Architecture & Rule Alignment)**:
  1. Decouple Core layer inversions (`ARCH-V01`, `ARCH-V02`, `ARCH-V03`).
  2. Refactor method signatures exceeding 6 parameters (`RULE-01`) using dataclasses (`HistoryRecord`, `DownloadJobConfig`, `AttemptContext`, `WindowDependencies`).
  3. Harden AppleScript execution against command injection and hanging deadlocks (`SEC-02`).
  4. Verify `ffmpeg.exe` binary with SHA-256 in `.github/workflows/release.yml` (`SEC-05`).
  5. Add AST parameter limit verification ($\le 6$) to `Downloader/tools/check_rules.py` (`RULE-02`).

---

## External Knowledge & Resources

### 1. Architectural Guardrails & Quality Standards (`PROJECT_RULES.md`)
- **Layer Boundary Hierarchy**: `UI -> Services -> Domain -> Core`.
  - `Core` is foundational and must be 100% headless, GUI-agnostic, and have zero imports from `src.ui`, `src.domain`, or `src.services`.
  - `Domain` contains business logic and entities, decoupled from UI (`PyQt6` / `WorkerSignals`). Any fields representing Qt signals or worker dependencies must use `typing.Any` or generic objects.
  - `Services` coordinate domain operations and storage.
  - `UI` handles presentation, user interaction, and platform integration (tray icons, dialogs, appearances).
- **Strict Size Limits**:
  - Files: $\le 150$ lines.
  - Classes: $\le 120$ lines.
  - Functions / Methods: $\le 35$ lines.
  - Parameters: $\le 6$ (excluding receiver `self` or `cls`).
  - Zero `print()` statements, zero UI slop (gradients, shadows, emojis, inline style colors).

---

## Requirements & Constraints

### 1. Architecture Decoupling & AppleScript Hardening (ARCH-V01, ARCH-V02, ARCH-V03, SEC-02)

#### ARCH-V01: Remove UI Coupling from `Downloader/src/core/config.py`
- **Problem**: `Config._load_settings()` dynamically imported `src.ui.macos.appearance.is_system_dark_mode` inside Core layer.
- **Solution**:
  - Remove `is_system_dark_mode` call and theme synchronization from `src/core/config.py`. Keeps `config.py` well under 150 lines (from 147 down to ~139 lines).
  - Move first-run appearance sync into UI initialization in `Downloader/src/ui/window_setup.py`:
    ```python
    def _sync_first_run_appearance(window: Any) -> None:
        if sys.platform != "darwin":
            return
        if not window._cfg.get("firstRun", True):
            return
        try:
            from .macos.appearance import is_system_dark_mode
            theme = "dark" if is_system_dark_mode() else "light"
            window._cfg.set("theme", theme)
        except Exception:
            pass
    ```
    Call `_sync_first_run_appearance(window)` in `initialize()` before building widgets.

#### ARCH-V02 & SEC-02: Relocate TrayIcon & Harden AppleScript Execution
- **Problem**: `Downloader/src/core/tray.py` contained PyQt6 `QSystemTrayIcon` (UI component in Core) and formatted unescaped title/message into `osascript -e` string without timeout (SEC-02).
- **Solution**:
  - Move tray implementation to `Downloader/src/ui/components/tray_icon.py`.
  - Harden AppleScript execution helper `run_applescript(script: str, timeout: float = 3.0)`:
    - Escape characters: `str(text).replace("\\", "\\\\").replace('"', '\\"').replace("\r", " ").replace("\n", " ")`.
    - Format safe AppleScript: `display notification "{safe_msg}" with title "{safe_title}"`.
    - Run subprocess with `timeout=3.0` to avoid deadlocks. Catch `TimeoutExpired` and handle gracefully.
  - Maintain backward compatibility shim in `Downloader/src/core/tray.py`:
    ```python
    """Backward-compatibility shim for TrayIcon."""
    from ..ui.components.tray_icon import SystemTrayIcon, TrayIcon, run_applescript

    __all__ = ["SystemTrayIcon", "TrayIcon", "run_applescript"]
    ```

#### ARCH-V03: Move Update Models to Core
- **Problem**: `Downloader/src/core/updater.py` imported dataclasses `ReleaseAsset` and `UpdateInfo` from `Downloader/src/domain/update_models.py` (Core importing Domain).
- **Solution**:
  - Relocate dataclasses to `Downloader/src/core/update_models.py`:
    ```python
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class ReleaseAsset:
        name: str
        download_url: str
        size: int
        content_type: str

    @dataclass(frozen=True)
    class UpdateInfo:
        version: str
        release_notes: str
        assets: list[ReleaseAsset]
        published_at: str
    ```
  - In `Downloader/src/core/updater.py`, change import to `from .update_models import ReleaseAsset, UpdateInfo`.
  - In `Downloader/src/domain/update_models.py`, maintain re-export for backward compatibility:
    ```python
    from ..core.update_models import ReleaseAsset, UpdateInfo

    __all__ = ["ReleaseAsset", "UpdateInfo"]
    ```

---

### 2. Parameter Limits & Dataclass Refactoring (RULE-01)

#### Dataclass Definitions in `Downloader/src/domain/models.py`
Add dataclasses in `Downloader/src/domain/models.py`:
```python
from typing import Any

@dataclass(frozen=True)
class HistoryRecord:
    url: str
    title: str = "Untitled"
    media_type: str = ""
    format: str = ""
    file_path: str = ""
    is_success: bool = True
    file_size: int = 0
    status: str | None = None
    error: str = ""
    thumbnail_path: str = ""


@dataclass(frozen=True)
class DownloadJobConfig:
    url: str
    downloader: Any
    preset: DownloadPreset
    output_dir: Path
    signals: Any
    history: Any = None
    title: str = ""
    engine: str = "yt-dlp"


@dataclass(frozen=True)
class AttemptContext:
    output_dir: Path
    preset: DownloadPreset
    options: dict[str, Any]
    started: float
    settings: Settings
```

#### Method Refactoring & Backward Compatibility Adapters

1. **`Downloader/src/services/history_manager.py`**:
   - Refactor `addEntry`:
     ```python
     def addEntry(self, record_or_url: HistoryRecord | str, *args: Any, **kwargs: Any) -> HistoryItem:
         if isinstance(record_or_url, HistoryRecord):
             rec = record_or_url
         else:
             # Backward-compatible unpacking for legacy 10 positional / keyword args
             rec = self._unpack_legacy_add_entry(record_or_url, args, kwargs)
         ...
     ```
   - Helper `_unpack_legacy_add_entry` handles legacy callers without exceeding 35 lines per method. Formal parameter count becomes $\le 3$.

2. **`Downloader/src/ui/workers/download_worker.py`**:
   - Refactor `__init__`:
     ```python
     def __init__(self, config_or_url: DownloadJobConfig | str, *args: Any, **kwargs: Any) -> None:
         super().__init__()
         if isinstance(config_or_url, DownloadJobConfig):
             cfg = config_or_url
         else:
             cfg = self._unpack_legacy_config(config_or_url, args, kwargs)
         ...
     ```
   - Formal parameter count becomes $\le 3$.
   - Update caller in `Downloader/src/ui/pages/workspace_jobs.py` to instantiate `DownloadJobConfig`.

3. **`Downloader/src/domain/yt_download.py`**:
   - Refactor `_attempt`:
     ```python
     def _attempt(self, url: str, attempt: int, max_attempts: int, ctx: AttemptContext) -> DownloadResult:
     ```
   - Formal parameter count reduced from 7 to 4.
   - In `download(...)`, construct `AttemptContext(output_dir=output_dir, preset=preset, options=opts, started=started, settings=settings)` and pass `ctx` to `_attempt`.

4. **`Downloader/src/ui/main_window.py` & `main.py`**:
   - `WindowDependencies` is already defined in `Downloader/src/ui/window_setup.py`:
     ```python
     @dataclass
     class WindowDependencies:
         settings: Any
         engine: Any
         history: Any
         downloads: Any
     ```
   - Refactor `MediaDownloaderUI.__init__`:
     ```python
     def __init__(self, deps_or_settings: WindowDependencies | Any = None, *args: Any, **kwargs: Any) -> None:
         super().__init__()
         if isinstance(deps_or_settings, WindowDependencies):
             self.deps = deps_or_settings
         else:
             self.deps = self._unpack_legacy_deps(deps_or_settings, args, kwargs)
         ...
     ```
   - Formal parameter count reduced from 7 to $\le 3$.
   - Update `Downloader/main.py` to pass `WindowDependencies(...)`.

---

### 3. Supply Chain Hardening & Rule Verification (SEC-05, RULE-02)

#### SEC-05: FFmpeg Binary SHA-256 Verification in CI (`.github/workflows/release.yml`)
- **Approved SHA-256 Hash**: `228D7A8556258DE907FDB55F36850078EBC7680B84EC30D84EA02E99BEC1D1EB`.
- **Workflow Step**:
  ```yaml
      - name: Verify FFmpeg input
        shell: pwsh
        run: |
          if (-not (Test-Path "ffmpeg.exe")) {
            throw "Place the approved ffmpeg.exe at the repository root before creating a release."
          }
          $expectedHash = "228D7A8556258DE907FDB55F36850078EBC7680B84EC30D84EA02E99BEC1D1EB"
          $actualHash = (Get-FileHash -Path "ffmpeg.exe" -Algorithm SHA256).Hash
          if ($actualHash -ne $expectedHash) {
            throw "ffmpeg.exe SHA-256 mismatch! Expected $expectedHash but got $actualHash"
          }
  ```

#### RULE-02: AST Parameter Limit ($\le 6$) Check in `Downloader/tools/check_rules.py`
- Add helper `_param_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int`:
  - Collect `posonlyargs`, `args`, `kwonlyargs`, `vararg`, `kwarg`.
  - If leading parameter is `"self"` or `"cls"`, exclude it.
  - Return count.
- In `_ast_errors(path: Path, text: str) -> list[str]`:
  - Check `count = _param_count(node)`:
  - If `count > 6`, append `f"{relative}:{node.lineno} function {node.name} has {count} parameters (max 6)"`.
- Keep file $\le 150$ lines, functions $\le 35$ lines.

---

## Verification Criteria
1. **Compilation**: `python -m compileall -q src main.py tools` succeeds with exit code 0.
2. **Rule Enforcement**: `python tools/check_rules.py` passes with 0 violations across all files.
3. **Anti-Slop Linter**: `python tools/check_ai_slop.py` passes with 0 violations.
4. **Line Budgets**: Every modified file strictly $\le 150$ lines, classes $\le 120$ lines, functions $\le 35$ lines.
5. **No Regressions**: All domain models and services maintain full backward-compatible interfaces.
