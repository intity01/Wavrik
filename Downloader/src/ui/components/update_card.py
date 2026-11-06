"""Software update controls backed by GitHub Releases."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThreadPool, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFrame

from src.services.platform_actions import open_parent
from src.ui.i18n import tr
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
        self._lang = "en"
        self._downloadedPath: Path | None = None
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self.setObjectName("SettingsCard")
        update_card_view.build(self)

    def setLanguage(self, lang: str) -> None:
        self._lang = lang
        update_card_view.set_language(self, lang)

    def check(self, silent: bool = False) -> None:
        if self._busy:
            return
        self._busy = True
        if not silent:
            self.statusLabel.setText(tr("set.checking_updates", self._lang))
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
            self.statusLabel.setText(tr("set.latest_version", self._lang))
            return
        self.statusLabel.setText(self._update_message(info))
        self.updateAvailable.emit(info)

    def _update_message(self, info) -> str:
        k = "set.update_available_safe" if info.can_download_safely else "set.update_available_generic"
        return tr(k, self._lang).replace("{version}", str(info.version))

    def _confirm_download(self) -> None:
        if not self._info or not self._info.can_download_safely:
            return
        dialog = MessageBox(
            tr("set.download_dialog_title", self._lang),
            tr("set.download_dialog_msg", self._lang),
            self,
            tr("set.download_dialog_btn", self._lang),
        )
        if dialog.exec():
            self._start_download()

    def _start_download(self) -> None:
        self._busy = True
        self.checkButton.setEnabled(False)
        self.progressBar.setValue(0)
        self.progressBar.show()
        self.downloadButton.setEnabled(False)
        self.statusLabel.setText(tr("set.downloading_update", self._lang))
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
        self.statusLabel.setText(tr("set.download_complete", self._lang))

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
