"""Modal dialog for editing and auto-detecting audio file metadata tags."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QVBoxLayout

from src.services.audio_acoustid import lookup_audio_file
from src.services.audio_tagger import AudioMetadata, apply_audio_metadata, read_audio_metadata
from src.ui.components.audio_tag_fields import TAG_KEYS, build_tag_form, resolve_detection
from src.ui.components.controls import PrimaryPushButton, PushButton
from src.ui.workers.audio_tag_worker import OP_APPLY, OP_DETECT, OP_LOAD, AudioTagSignals, AudioTagWorker


class AudioTagDialog(QDialog):
    def __init__(self, audio_path: str | Path, parent=None):
        super().__init__(parent)
        self._path = Path(audio_path).resolve()
        self._worker: AudioTagWorker | None = None
        self._applying = False
        self._signals = AudioTagSignals()
        self._signals.succeeded.connect(self._on_succeeded)
        self._signals.failed.connect(self._on_failed)
        self.setWindowTitle("Edit Audio Tags")
        self.setMinimumWidth(480)
        self._build_ui()
        self._start(OP_LOAD, partial(read_audio_metadata, self._path), "Reading existing tags...")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)
        root.addWidget(QLabel(f"Tag Metadata: {self._path.name}", objectName="SectionTitle"))
        root.addLayout(build_tag_form(self, self._browse_cover))
        self.statusLabel = QLabel("Ready.", objectName="MutedText")
        root.addWidget(self.statusLabel)
        btn_row = QHBoxLayout()
        self.detectBtn, self.cancelBtn = PushButton("Auto-Detect (AcoustID)"), PushButton("Cancel")
        self.applyBtn = PrimaryPushButton("Apply Tags")
        self.detectBtn.clicked.connect(self._auto_detect)
        self.cancelBtn.clicked.connect(self.reject)
        self.applyBtn.clicked.connect(self._apply_tags)
        btn_row.addWidget(self.detectBtn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.cancelBtn)
        btn_row.addWidget(self.applyBtn)
        root.addLayout(btn_row)

    def _browse_cover(self) -> None:
        filt = "Image files (*.jpg *.jpeg *.png);;All files (*.*)"
        sel, _ = QFileDialog.getOpenFileName(self, "Choose Cover Image", str(self._path.parent), filt)
        if sel:
            self.coverEdit.setText(sel)

    def _edits(self) -> dict[str, Any]:
        return {k: getattr(self, f"{k}Edit") for k in TAG_KEYS}

    def _start(self, operation: str, task, message: str) -> None:
        worker = AudioTagWorker(operation, task, self._signals)
        self._worker = worker
        self._applying = operation == OP_APPLY
        self._set_busy(True)
        self.statusLabel.setText(message)
        QThreadPool.globalInstance().start(worker)

    def _set_busy(self, busy: bool) -> None:
        self.detectBtn.setEnabled(not busy)
        self.applyBtn.setEnabled(not busy)
        self.cancelBtn.setEnabled(not (busy and self._applying))

    def _finish(self) -> None:
        self._worker = None
        self._applying = False
        self._set_busy(False)

    def _on_succeeded(self, operation: str, result: Any) -> None:
        self._finish()
        if operation == OP_LOAD:
            self._fill_missing(result)
            self.statusLabel.setText("Ready.")
        elif operation == OP_DETECT:
            self._apply_detection(result)
        elif operation == OP_APPLY:
            self.statusLabel.setText("Tags saved successfully.")
            self.accept()

    def _on_failed(self, operation: str, message: str) -> None:
        self._finish()
        self.statusLabel.setText(message)

    def _fill_missing(self, meta: AudioMetadata) -> None:
        for key, edit in self._edits().items():
            if not edit.text():
                edit.setText(getattr(meta, key))

    def _apply_detection(self, res: dict[str, Any]) -> None:
        values, src_desc = resolve_detection(res, self._path.name)
        for key, edit in self._edits().items():
            if values.get(key):
                edit.setText(values[key])
        self.statusLabel.setText(f"Auto-detection applied ({src_desc}).")

    def _auto_detect(self) -> None:
        if self._worker is None:
            self._start(OP_DETECT, partial(lookup_audio_file, self._path), "Querying AcoustID & MusicBrainz...")

    def _apply_tags(self) -> None:
        if self._worker is not None:
            return
        meta = AudioMetadata(
            **{k: e.text().strip() for k, e in self._edits().items()},
            cover_path=self.coverEdit.text().strip(),
        )
        self._start(OP_APPLY, partial(apply_audio_metadata, self._path, meta), "Saving tags...")

    def reject(self) -> None:
        if not self._applying:
            super().reject()

    def done(self, result: int) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._worker = None
        self._signals.blockSignals(True)
        super().done(result)
