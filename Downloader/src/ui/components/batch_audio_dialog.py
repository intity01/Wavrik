"""Modal dialog for batch audio pitch shifting and tempo stretching."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QDialog, QFileDialog

from src.services.audio_batch import BatchJobConfig
from src.ui.workers.batch_worker import BatchAudioSignals, BatchAudioWorker

from .batch_audio_view import build_batch_ui


class BatchAudioDialog(QDialog):
    def __init__(self, sources: list[Path], config, parent=None, cached_keys: dict[str, str] | None = None):
        super().__init__(parent)
        self._sources, self._cfg = [Path(p) for p in sources if Path(p).is_file()], config
        self._cached_keys = cached_keys or {}
        self._pool = QThreadPool(self)
        self._worker: BatchAudioWorker | None = None
        self._signals: BatchAudioSignals | None = None
        self.setWindowTitle("Batch Audio Processing")
        self.setMinimumWidth(520)
        build_batch_ui(self)

    def _browse(self) -> None:
        sel = QFileDialog.getExistingDirectory(self, "Choose destination folder", self.destInput.text())
        if sel:
            self.destInput.setText(sel)

    def _start_batch(self) -> None:
        self.startBtn.setEnabled(False)
        self.closeBtn.setText("Cancel")
        self.pbar.setValue(0)
        self.status.setText(f"Processing 1 of {len(self._sources)}…")
        cfg = BatchJobConfig(
            semitones=self.semitoneSpin.value(), tempo_ratio=self.tempoSpin.value(),
            engine="r3_finer", fmt=str(self.fmtCombo.currentData() or "wav"),
            output_dir=Path(self.destInput.text()),
        )
        self._signals = BatchAudioSignals()
        self._signals.itemProcessed.connect(self._on_item)
        self._signals.finished.connect(self._on_finished)
        self._worker = BatchAudioWorker(self._sources, cfg, self._signals, self._cached_keys)
        self._pool.start(self._worker)

    def _on_item(self, cur: int, total: int, name: str) -> None:
        self.pbar.setValue(cur)
        self.status.setText(f"Completed {cur}/{total}: {name}")

    def _on_finished(self, succ: int, fail: int) -> None:
        self._worker = None
        self.startBtn.setEnabled(True)
        self.closeBtn.setText("Close")
        self.status.setText(f"Batch completed: {succ} succeeded, {fail} failed.")

    def _cancel_and_wait(self) -> None:
        if self._worker:
            self._worker.cancel()
        if self._signals:
            try:
                self._signals.itemProcessed.disconnect()
                self._signals.finished.disconnect()
            except (TypeError, RuntimeError):
                pass
        self._pool.clear()
        self._pool.waitForDone(2000)
        self._worker = None

    def _on_close_clicked(self) -> None:
        self._cancel_and_wait()
        self.accept()

    def closeEvent(self, event) -> None:
        self._cancel_and_wait()
        event.accept()

    def reject(self) -> None:
        self._cancel_and_wait()
        super().reject()
