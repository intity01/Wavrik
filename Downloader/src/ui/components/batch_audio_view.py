"""UI layout and controls builder for BatchAudioDialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSpinBox,
    QVBoxLayout,
)

from src.ui.components.controls import ComboBox, LineEdit, PrimaryPushButton, PushButton, ToolButton


def build_batch_ui(dialog) -> None:
    root = QVBoxLayout(dialog)
    root.setContentsMargins(20, 18, 20, 18)
    root.setSpacing(10)
    root.addWidget(QLabel("Batch Audio Processing (Pitch & Tempo)", objectName="SectionTitle"))
    count_txt = f"Selected: {len(dialog._sources)} audio tracks"
    root.addWidget(QLabel(count_txt, objectName="MutedText"))
    _add_controls(dialog, root)
    _add_destination(dialog, root)
    _add_progress(dialog, root)


def _add_controls(dialog, root: QVBoxLayout) -> None:
    p_row = QHBoxLayout()
    dialog.semitoneSpin = QSpinBox(minimum=-12, maximum=12, value=0)
    p_row.addWidget(QLabel("Semitones (-12..+12):"))
    p_row.addWidget(dialog.semitoneSpin)
    for s in (-2, 0, 2):
        btn = ToolButton(f"{f'+{s}' if s > 0 else s} st")
        btn.clicked.connect(lambda _c=False, val=s: dialog.semitoneSpin.setValue(val))
        p_row.addWidget(btn)
    p_row.addStretch(1)
    root.addLayout(p_row)
    t_row = QHBoxLayout()
    dialog.tempoSpin = QDoubleSpinBox(minimum=0.5, maximum=2.0, value=1.0, singleStep=0.05, decimals=2)
    t_row.addWidget(QLabel("Tempo Stretch (0.5x–2.0x):"))
    t_row.addWidget(dialog.tempoSpin)
    for val in (0.9, 1.0, 1.1):
        btn = ToolButton(f"{val:.2f}x")
        btn.clicked.connect(lambda _c=False, v=val: dialog.tempoSpin.setValue(v))
        t_row.addWidget(btn)
    t_row.addStretch(1)
    root.addLayout(t_row)
    f_row = QHBoxLayout()
    dialog.fmtCombo = ComboBox()
    for label, k in (("WAV 24-bit", "wav"), ("FLAC Lossless", "flac"), ("MP3 320k", "mp3")):
        dialog.fmtCombo.addItem(label, k)
    f_row.addWidget(QLabel("Format:"))
    f_row.addWidget(dialog.fmtCombo, 1)
    root.addLayout(f_row)


def _add_destination(dialog, root: QVBoxLayout) -> None:
    d_row = QHBoxLayout()
    default_dir = dialog._cfg.getDownloadPath("audio")
    dialog.destInput = LineEdit(str(default_dir))
    dialog.browseBtn = PushButton("Change folder")
    dialog.browseBtn.clicked.connect(dialog._browse)
    d_row.addWidget(dialog.destInput, 1)
    d_row.addWidget(dialog.browseBtn)
    root.addWidget(QLabel("Save Location:"))
    root.addLayout(d_row)


def _add_progress(dialog, root: QVBoxLayout) -> None:
    dialog.pbar = QProgressBar()
    dialog.pbar.setRange(0, max(1, len(dialog._sources)))
    dialog.pbar.setValue(0)
    dialog.status = QLabel("Ready to process.", objectName="MutedText")
    b_row = QHBoxLayout()
    dialog.startBtn = PrimaryPushButton("Start Batch Processing")
    dialog.startBtn.clicked.connect(dialog._start_batch)
    dialog.closeBtn = PushButton("Close")
    dialog.closeBtn.clicked.connect(dialog._on_close_clicked)
    b_row.addStretch(1)
    b_row.addWidget(dialog.closeBtn)
    b_row.addWidget(dialog.startBtn)
    for w in (dialog.pbar, dialog.status):
        root.addWidget(w)
    root.addLayout(b_row)
