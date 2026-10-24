"""Modal dialog for batch audio pitch shifting and tempo stretching."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QDialog, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QProgressBar, QSpinBox, QVBoxLayout

from src.services.audio_batch import BatchJobConfig
from src.ui.components.controls import ComboBox, LineEdit, PrimaryPushButton, PushButton, ToolButton
from src.ui.workers.batch_worker import BatchAudioSignals, BatchAudioWorker


class BatchAudioDialog(QDialog):
    def __init__(self, sources: list[Path], config, parent=None, cached_keys: dict[str, str] | None = None):
        super().__init__(parent)
        self._sources, self._cfg = [Path(p) for p in sources if Path(p).is_file()], config
        self._cached_keys = cached_keys or {}
        self._pool = QThreadPool(self)
        self.setWindowTitle("Batch Audio Processing")
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)
        root.addWidget(QLabel("Batch Audio Processing (Pitch & Tempo)", objectName="SectionTitle"))
        count_txt = f"Selected: {len(self._sources)} audio tracks"
        root.addWidget(QLabel(count_txt, objectName="MutedText"))
        self._add_controls(root)
        self._add_destination(root)
        self._add_progress(root)

    def _add_controls(self, root: QVBoxLayout) -> None:
        p_row = QHBoxLayout()
        self.semitoneSpin = QSpinBox(minimum=-12, maximum=12, value=0)
        p_row.addWidget(QLabel("Semitones (-12..+12):"))
        p_row.addWidget(self.semitoneSpin)
        for s in (-2, 0, 2):
            btn = ToolButton(f"{f'+{s}' if s > 0 else s} st")
            btn.clicked.connect(lambda _c=False, val=s: self.semitoneSpin.setValue(val))
            p_row.addWidget(btn)
        p_row.addStretch(1)
        root.addLayout(p_row)
        t_row = QHBoxLayout()
        self.tempoSpin = QDoubleSpinBox(minimum=0.5, maximum=2.0, value=1.0, singleStep=0.05, decimals=2)
        t_row.addWidget(QLabel("Tempo Stretch (0.5x–2.0x):"))
        t_row.addWidget(self.tempoSpin)
        for val in (0.9, 1.0, 1.1):
            btn = ToolButton(f"{val:.2f}x")
            btn.clicked.connect(lambda _c=False, v=val: self.tempoSpin.setValue(v))
            t_row.addWidget(btn)
        t_row.addStretch(1)
        root.addLayout(t_row)
        f_row = QHBoxLayout()
        self.fmtCombo = ComboBox()
        for label, k in (("WAV 24-bit", "wav"), ("FLAC Lossless", "flac"), ("MP3 320k", "mp3")):
            self.fmtCombo.addItem(label, k)
        f_row.addWidget(QLabel("Format:"))
        f_row.addWidget(self.fmtCombo, 1)
        root.addLayout(f_row)

    def _add_destination(self, root: QVBoxLayout) -> None:
        d_row = QHBoxLayout()
        default_dir = self._cfg.getDownloadPath("audio")
        self.destInput = LineEdit(str(default_dir))
        self.browseBtn = PushButton("Change folder")
        self.browseBtn.clicked.connect(self._browse)
        d_row.addWidget(self.destInput, 1)
        d_row.addWidget(self.browseBtn)
        root.addWidget(QLabel("Save Location:"))
        root.addLayout(d_row)

    def _add_progress(self, root: QVBoxLayout) -> None:
        self.pbar = QProgressBar()
        self.pbar.setRange(0, max(1, len(self._sources)))
        self.pbar.setValue(0)
        self.status = QLabel("Ready to process.", objectName="MutedText")
        b_row = QHBoxLayout()
        self.startBtn = PrimaryPushButton("Start Batch Processing")
        self.startBtn.clicked.connect(self._start_batch)
        self.closeBtn = PushButton("Close")
        self.closeBtn.clicked.connect(self.accept)
        b_row.addStretch(1)
        b_row.addWidget(self.closeBtn)
        b_row.addWidget(self.startBtn)
        for w in (self.pbar, self.status):
            root.addWidget(w)
        root.addLayout(b_row)

    def _browse(self) -> None:
        sel = QFileDialog.getExistingDirectory(self, "Choose destination folder", self.destInput.text())
        if sel:
            self.destInput.setText(sel)

    def _start_batch(self) -> None:
        self.startBtn.setEnabled(False)
        self.pbar.setValue(0)
        self.status.setText(f"Processing 1 of {len(self._sources)}…")
        cfg = BatchJobConfig(
            semitones=self.semitoneSpin.value(), tempo_ratio=self.tempoSpin.value(),
            engine="r3_finer", fmt=str(self.fmtCombo.currentData() or "wav"),
            output_dir=Path(self.destInput.text()),
        )
        signals = BatchAudioSignals()
        signals.itemProcessed.connect(self._on_item)
        signals.finished.connect(self._on_finished)
        self._pool.start(BatchAudioWorker(self._sources, cfg, signals, self._cached_keys))

    def _on_item(self, cur: int, total: int, name: str) -> None:
        self.pbar.setValue(cur)
        self.status.setText(f"Completed {cur}/{total}: {name}")

    def _on_finished(self, succ: int, fail: int) -> None:
        self.startBtn.setEnabled(True)
        self.status.setText(f"Batch completed: {succ} succeeded, {fail} failed.")
