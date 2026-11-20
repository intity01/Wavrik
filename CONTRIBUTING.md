# Contributing to Wavrik

ขอบคุณที่สนใจร่วมพัฒนา Wavrik · Media Downloader PRO — Thanks for helping out! Issues and pull requests in Thai or English are both welcome.

## Before you start

- Read [`docs/PROJECT_RULES.md`](docs/PROJECT_RULES.md) (engineering, security and size limits) and [`docs/DESIGN.md`](docs/DESIGN.md) (UI system).
- For anything larger than a small fix, open an issue first so we can agree on the approach.
- Never add features that bypass DRM or access restrictions — such PRs will be closed.

## Development setup (Windows)

```powershell
git clone https://github.com/intity01/Wavrik.git
cd Wavrik
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r Downloader/requirements-dev.txt
```

Put `ffmpeg.exe` (and optionally `rubberband.exe` + `sndfile.dll`) in the repository root, then run the app with `RunApp.bat` or `cd Downloader; python main.py`.

## Quality gates

Every PR must pass the same checks as CI:

```powershell
cd Downloader
python -m compileall -q src main.py
python tools/check_rules.py     # 150 lines/file, 35 lines/function, 120 lines/class
python tools/check_ai_slop.py
ruff check src tests
pytest -q
```

## Pull requests

- Keep a PR focused on one change; add or update tests for behaviour changes.
- UI text goes through `src/ui/i18n_en.py` **and** `src/ui/i18n_th.py` — no mixed-language strings.
- `src/domain` and `src/services` must not import from `src/ui`.
- Add a line under `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md) for user-visible changes.
- By contributing you agree your work is licensed under [GPL-3.0-or-later](LICENSE).

## Releasing (maintainers)

1. Bump `VERSION` in `Downloader/src/core/config.py`, `Downloader/pyproject.toml`, the default in `installer.iss`, the README title, and add a `## [x.y.z]` section to `CHANGELOG.md`.
2. Merge to `main`, then `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. The **Build Windows release** workflow tests, builds the installer and portable zip, and publishes the GitHub release.
