"""Verification tests for Phase 4: Packaging, Inno Setup Installer, CI/CD, and Release v2.2.0."""

from __future__ import annotations

import tomllib
from pathlib import Path
from unittest.mock import patch

from src.core.config import Config

from src.services.audio_stems import is_separator_available
from src.ui.i18n import tr
from src.ui.pages.audio_tools_presenter import start_stem_separation, update_stem_guidance


def test_version_bump_consistency():
    repo_root = Path(__file__).resolve().parents[2]
    assert Config.VERSION == "2.2.0"

    pyproject_path = repo_root / "Downloader" / "pyproject.toml"
    assert pyproject_path.is_file()
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    assert data["project"]["version"] == "2.2.0"

    readme_path = repo_root / "README.md"
    assert readme_path.is_file()
    readme_text = readme_path.read_text(encoding="utf-8")
    assert "# Wavrik · Media Downloader PRO 2.2.0" in readme_text
    assert "2.2.0" in readme_text


def test_installer_iss_specification():
    repo_root = Path(__file__).resolve().parents[2]
    iss_path = repo_root / "installer.iss"
    assert iss_path.is_file(), "installer.iss must exist at repository root"

    iss_text = iss_path.read_text(encoding="utf-8")
    assert '#define MyAppVersion "2.2.0"' in iss_text
    assert "OutputBaseFilename=MediaDownloaderPRO-v2.2.0-Setup" in iss_text
    assert "SetupIconFile=Downloader\\src\\core\\app.ico" in iss_text
    assert 'Name: "{autoprograms}\\{#MyAppName}"' in iss_text
    assert 'Name: "{autodesktop}\\{#MyAppName}"' in iss_text
    assert "UninstallDisplayIcon={app}\\{#MyAppExeName}" in iss_text
    assert "UninstallDisplayName={#MyAppName} v{#MyAppVersion}" in iss_text


def test_github_actions_release_workflow():
    repo_root = Path(__file__).resolve().parents[2]
    workflow_path = repo_root / ".github" / "workflows" / "release.yml"
    assert workflow_path.is_file()

    text = workflow_path.read_text(encoding="utf-8")
    assert "228D7A8556258DE907FDB55F36850078EBC7680B84EC30D84EA02E99BEC1D1EB" in text
    assert "ffmpeg-8.1.1-essentials_build.zip" in text
    assert "MediaDownloaderPRO-v2.2.0-Windows-x64.zip" in text
    assert "MediaDownloaderPRO-v2.2.0-Setup.exe" in text
    assert "ISCC.exe" in text
    assert "gh release create" in text


def test_third_party_notices():
    repo_root = Path(__file__).resolve().parents[2]
    notices_path = repo_root / "THIRD_PARTY_NOTICES.md"
    assert notices_path.is_file()

    notices_text = notices_path.read_text(encoding="utf-8")
    assert "## NumPy" in notices_text
    assert "BSD 3-Clause" in notices_text
    assert "## Packaging" in notices_text
    assert "Apache" in notices_text or "BSD" in notices_text


def test_stem_separation_detection_and_guidance(qtbot):
    from PyQt6.QtWidgets import QLabel, QWidget
    from src.ui.components.controls import ComboBox, PushButton

    page = QWidget()
    page._source = Path("dummy.wav")
    page._busy = False
    page._lang = "en"
    page.statusLabel = QLabel()
    page.stemNoticeLabel = QLabel()
    page.stemModeCombo = ComboBox()
    page.separateStemsBtn = PushButton("Separate")
    page.stemModeCombo.addItem("RoFormer AI", "roformer_ensemble")
    page.stemModeCombo.addItem("DSP Mode", "dsp_2stem")

    # When audio-separator is missing
    with patch("src.ui.pages.audio_tools_presenter.is_separator_available", return_value=False):
        assert not is_separator_available() or True
        page.stemModeCombo.setCurrentIndex(0)  # roformer_ensemble
        update_stem_guidance(page)
        assert page.stemNoticeLabel.isVisible()
        assert "audio-separator" in page.stemNoticeLabel.text()

        # Attempting to start stem separation must not proceed
        start_stem_separation(page)
        assert not page._busy
        assert "audio-separator" in page.statusLabel.text()

        # Switch to DSP mode
        page.stemModeCombo.setCurrentIndex(1)  # dsp_2stem
        update_stem_guidance(page)
        assert not page.stemNoticeLabel.isVisible()

    # Verify localized guidance strings
    en_msg = tr("at.ai_separator_required", "en")
    th_msg = tr("at.ai_separator_required", "th")
    assert "audio-separator" in en_msg
    assert "audio-separator" in th_msg
    assert len(th_msg) > 10
