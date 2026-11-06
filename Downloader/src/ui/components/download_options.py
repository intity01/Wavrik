"""Primary download controls shown directly on the Downloads page."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame

from src.domain.presets import PRESETS, getPreset
from src.ui.dialogs import get_save_directory
from src.ui.i18n import tr

from .download_options_view import build, set_language, short_label


class DownloadOptions(QFrame):
    presetChanged = pyqtSignal(str)
    engineChanged = pyqtSignal(str)
    pathChanged = pyqtSignal(str)
    downloadAllRequested = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._cfg = config
        self._lang = "en"
        self._last_count = 0
        self._last_can_download = False
        self.setObjectName("DownloadOptions")
        build(self)
        self._restore_default()

    def setLanguage(self, lang: str) -> None:
        self._lang = lang
        set_language(self, lang)
        self.setQueueState(self._last_count, self._last_can_download)

    def _restore_default(self) -> None:
        preset = getPreset(self._cfg.get("defaultPreset"))
        self.mediaCombo.blockSignals(True)
        idx = self.mediaCombo.findData(preset.media_type)
        self.mediaCombo.setCurrentIndex(max(0, idx))
        self.mediaCombo.blockSignals(False)
        self._populate_presets(preset.key, preset.media_type)
        index = self.engineCombo.findData(self._cfg.get("downloadEngine", "auto"))
        self.engineCombo.setCurrentIndex(max(0, index))

    def _media_changed(self, *_args) -> None:
        media_type = str(self.mediaCombo.currentData() or "audio")
        self._populate_presets(None, media_type)
        self._preset_changed()

    def _populate_presets(self, selected: str | None, media_type: str | None = None) -> None:
        media_type = media_type or str(self.mediaCombo.currentData() or "audio")
        self.presetCombo.blockSignals(True)
        self.presetCombo.clear()
        for preset in PRESETS:
            if preset.media_type == media_type:
                self.presetCombo.addItem(short_label(preset.label), preset.key)
        index = next(
            (i for i in range(self.presetCombo.count()) if self.presetCombo.itemData(i) == selected),
            0,
        )
        self.presetCombo.setCurrentIndex(index)
        self.presetCombo.blockSignals(False)

    def _preset_changed(self, _index: int = -1) -> None:
        key = self.currentPresetKey()
        if key:
            self._cfg.update(defaultPreset=key)
            self.presetChanged.emit(key)

    def _engine_changed(self, _index: int = -1) -> None:
        engine = self.currentEngine()
        self._cfg.update(downloadEngine=engine)
        self.engineChanged.emit(engine)

    def _browse(self) -> None:
        title = tr("dl.choose_folder_dialog", self._lang)
        selected = get_save_directory(self, title, self.pathInput.text())
        path = str(selected).strip() if selected else ""
        if not path or path == ".":
            return
        self.pathInput.setText(path)
        self.pathInput.setCursorPosition(0)
        self._cfg.update(downloadPath=path)
        self.pathChanged.emit(path)

    def currentPresetKey(self) -> str:
        return str(self.presetCombo.currentData() or "")

    def currentEngine(self) -> str:
        return str(self.engineCombo.currentData() or "auto")

    def setQueueState(self, count: int, can_download: bool) -> None:
        self._last_count = count
        self._last_can_download = can_download
        self.downloadAllButton.setVisible(count > 0)
        self.downloadAllButton.setEnabled(count > 0 and can_download)
        suffix = "" if count == 1 else "s"
        txt = tr("dl.download_all_count", self._lang).replace("{count}", str(count)) if count else tr("dl.download_all", self._lang)
        self.downloadAllButton.setText(txt)
        self.downloadAllButton.setAccessibleDescription(f"Download {count} queued item{suffix}")
