"""Software update controls backed by GitHub Releases."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThreadPool, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFrame

from src.services.platform_actions import open_parent
from src.ui.workers.update_worker import (
    CheckUpdateWorker,
    DownloadUpdateWorker,
    UpdateSignals,
)

from . import update_card_view
from .controls import MessageBox


class UpdateCard(QFrame):
    updateAvailable = pyqtSignal(object)

    def __init__(self, manager, config, parent=None):
        super().__init__(parent)
        self._manager = manager
        self._cfg = config
        self._info = None
        self._busy = False
        self._downloadedPath: Path | None = None
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self.setObjectName("SettingsCard")
        update_card_view.build(self)

    def check(self, silent: bool = False) -> None:
        if self._busy:
            return
        self._busy = True
        if not silent:
            self.statusLabel.setText("Checking GitHub Releases…")
        self.checkButton.setEnabled(False)
        signals = UpdateSignals()
        signals.checked.connect(self._checked)
        signals.error.connect(self._failed)
        self._signals = signals
        self._pool.start(CheckUpdateWorker(self._manager, signals))

    def _checked(self, info) -> None:
        self._busy = False
        self.checkButton.setEnabled(True)
        self._info = info
        self.releaseButton.setVisible(bool(info))
        self.downloadButton.setVisible(bool(info and info.can_download_safely))
        if not info:
            self.statusLabel.setText("You are using the latest published version.")
            return
        self.statusLabel.setText(self._update_message(info))
        self.updateAvailable.emit(info)

    def _update_message(self, info) -> str:
        if info.can_download_safely:
            return f"Version {info.version} is available as an immutable, SHA-256 verified release."
        return f"Version {info.version} is available. Review and download it on GitHub."

    def _confirm_download(self) -> None:
        if not self._info or not self._info.can_download_safely:
            return
        dialog = MessageBox(
            "Download update package",
            "The package will be downloaded from GitHub and checked against its SHA-256 digest. "
            "The app will not run the installer automatically.",
            self,
            "Download package",
        )
        if dialog.exec():
            self._start_download()

    def _start_download(self) -> None:
        self._busy = True
        self.checkButton.setEnabled(False)
        self.progressBar.setValue(0)
        self.progressBar.show()
        self.downloadButton.setEnabled(False)
        self.statusLabel.setText("Downloading and verifying the update package…")
        signals = UpdateSignals()
        signals.progress.connect(self.progressBar.setValue)
        signals.downloaded.connect(self._downloaded)
        signals.error.connect(self._failed)
        self._signals = signals
        folder = Path(self._cfg.get("downloadPath")) / "Updates"
        self._pool.start(DownloadUpdateWorker(self._manager, self._info, folder, signals))

    def _downloaded(self, path: str) -> None:
        self._busy = False
        self.checkButton.setEnabled(True)
        self._downloadedPath = Path(path)
        self.progressBar.setValue(100)
        self.downloadButton.setEnabled(True)
        self.folderButton.show()
        self.statusLabel.setText("The package was downloaded and verified. Install it manually when ready.")

    def _failed(self, message: str) -> None:
        self._busy = False
        self.checkButton.setEnabled(True)
        self.downloadButton.setEnabled(True)
        self.progressBar.hide()
        self.statusLabel.setText(message)

    def _open_release(self) -> None:
        if self._info:
            QDesktopServices.openUrl(QUrl(self._info.release_url))

    def _open_folder(self) -> None:
        if self._downloadedPath:
            open_parent(self._downloadedPath)

    def _save_startup_preference(self, enabled: bool) -> None:
        self._cfg.update(checkUpdatesOnStartup=enabled)
