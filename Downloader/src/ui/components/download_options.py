"""Primary download controls shown directly on the Downloads page."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame

from src.domain.presets import PRESETS, getPreset
from src.ui.dialogs import get_save_directory

from .download_options_view import build, short_label


class DownloadOptions(QFrame):
    presetChanged = pyqtSignal(str)
    engineChanged = pyqtSignal(str)
    pathChanged = pyqtSignal(str)
    downloadAllRequested = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._cfg = config
        self.setObjectName("DownloadOptions")
        build(self)
        self._restore_default()

    def _restore_default(self) -> None:
        preset = getPreset(self._cfg.get("defaultPreset"))
        self.mediaCombo.blockSignals(True)
        self.mediaCombo.setCurrentText(preset.media_type.title())
        self.mediaCombo.blockSignals(False)
        self._populate_presets(preset.key)
        index = self.engineCombo.findData(self._cfg.get("downloadEngine", "auto"))
        self.engineCombo.setCurrentIndex(max(0, index))

    def _media_changed(self, media_type: str) -> None:
        self._populate_presets(None, media_type.lower())
        self._preset_changed()

    def _populate_presets(self, selected: str | None, media_type: str | None = None) -> None:
        media_type = media_type or self.mediaCombo.currentText().lower()
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
        selected = get_save_directory(self, "Choose download folder", self.pathInput.text())
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
        self.downloadAllButton.setVisible(count > 0)
        self.downloadAllButton.setEnabled(count > 0 and can_download)
        suffix = "" if count == 1 else "s"
        self.downloadAllButton.setText(f"Download all ({count})" if count else "Download all")
        self.downloadAllButton.setAccessibleDescription(f"Download {count} queued item{suffix}")
