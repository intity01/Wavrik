"""Presentation and stem-separation workflow helpers for Audio Tools UI."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel

from src.services.audio_analysis import camelot_code, enharmonic_key, mirex_key_score, transpose_key
from src.services.audio_stems import STEM_MODES
from src.ui.components.controls import ComboBox, PushButton, ToolButton
from src.ui.theme.key_colors import apply_key_property
from src.ui.workers.stem_worker import StemSeparationWorker, StemSignals


def build_stem_rack(page) -> QFrame:
    card = QFrame(objectName="AudioToolsCard")
    row = QHBoxLayout(card)
    row.setContentsMargins(12, 8, 12, 8)
    page.stemModeCombo = ComboBox()
    for label, key in STEM_MODES:
        page.stemModeCombo.addItem(label, key)
    page.separateStemsBtn = PushButton("Separate Stems")
    page.loadVocalsBtn, page.loadInstBtn = ToolButton("Use Vocals"), ToolButton("Use Instrumental")
    page.loadVocalsBtn.setEnabled(False)
    page.loadInstBtn.setEnabled(False)
    page.separateStemsBtn.clicked.connect(page._separate_stems)
    page.loadVocalsBtn.clicked.connect(page._load_vocals_stem)
    page.loadInstBtn.clicked.connect(page._load_inst_stem)
    for w, st in ((QLabel("STEM SEPARATOR", objectName="FieldLabel"), 0), (page.stemModeCombo, 1), (page.separateStemsBtn, 0), (page.loadVocalsBtn, 0), (page.loadInstBtn, 0)):
        row.addWidget(w, st)
    return card


def update_preview_labels(page) -> None:
    base_key, semitones = page.detectedKeyCombo.currentText() or "C major", page.semitoneSpin.value()
    shifted_key, enh, ratio = transpose_key(base_key, semitones), enharmonic_key(base_key), page._tempo_ratio()
    page.camelotLabel.setText(f"Camelot: {camelot_code(base_key)}" + (f" ({enh})" if enh != base_key else ""))
    apply_key_property(page.camelotLabel, camelot_code(base_key))
    page.waveformWidget.setKeyCamelot(camelot_code(base_key))
    page.resultingKeyLabel.setText(f"Resulting key: {shifted_key} ({camelot_code(shifted_key)}) · {f'+{semitones}' if semitones > 0 else semitones} st")
    apply_key_property(page.resultingKeyLabel, camelot_code(shifted_key))
    page.tempoRatioLabel.setText(f"Stretch: {ratio:.2f}x ({ratio * 100:.0f}%)")
    if page._source:
        page.outputPreviewLabel.setText(f"Safe export copy: {page._export_name(str(page.formatCombo.currentData() or 'wav'))} (original untouched)")


def populate_candidate_buttons(buttons: list, candidates: list[dict], top_key: str) -> None:
    for idx, btn in enumerate(buttons):
        ck = str(candidates[idx]["key"]) if idx < len(candidates) else ""
        btn.setText(f"#{idx + 1} {ck} ({camelot_code(ck)} · {mirex_key_score(ck, top_key)[1] if idx > 0 else 'Top'})" if ck else f"#{idx + 1} --")


def populate_harmonic_buttons(buttons: list, neighbors: list[dict]) -> None:
    for idx, btn in enumerate(buttons):
        if idx < len(neighbors):
            nb = neighbors[idx]
            sign = f"+{nb['semitones']}" if nb["semitones"] > 0 else f"{nb['semitones']}"
            btn.setText(f"{nb['code']} {nb['label']} ({sign}st)")
            btn.setToolTip(f"{nb['key']} · {nb['desc']}")
        else:
            btn.setText("--")


def format_analysis_status(key: str, bpm: float, result: dict) -> str:
    enh, conf = enharmonic_key(key), result.get("confidence", "")
    return f"Estimated {f'{key} / {enh}' if enh != key else key} ({camelot_code(key)}){f' [{conf}%]' if conf else ''} · {bpm:.1f} BPM"


def start_stem_separation(page) -> None:
    if not page._source or page._busy:
        return
    page._busy, page._stemSignals = True, StemSignals()
    mode = str(page.stemModeCombo.currentData() or "roformer_ensemble")
    page.statusLabel.setText("Separating Vocals & Instrumental (Phase-Locked)…")
    page.separateStemsBtn.setEnabled(False)
    page._stemSignals.separated.connect(lambda v, i, m: on_stems_ready(page, v, i, m))
    page._stemSignals.error.connect(page._on_error)
    page._pool.start(StemSeparationWorker(page._source, page._cfg.getDownloadPath("audio"), mode, page._stemSignals))


def on_stems_ready(page, vocals_str: str, inst_str: str, mode_used: str) -> None:
    page._busy = False
    voc, inst = Path(vocals_str), Path(inst_str)
    page._vocalsStem, page._instStem = voc, inst
    page.separateStemsBtn.setEnabled(True)
    page.loadVocalsBtn.setEnabled(voc.is_file())
    page.loadInstBtn.setEnabled(inst.is_file())
    for stem_path in (voc, inst):
        if page._hist and stem_path.is_file():
            page._hist.addEntry("", stem_path.stem, "audio", "WAV", str(stem_path), True, stem_path.stat().st_size, status="completed")
        if stem_path.is_file():
            page.fileExported.emit(str(stem_path))
    page._lastExport = voc if voc.is_file() else inst
    page.openFolderBtn.show()
    page.statusLabel.setText(f"Stems ready ({mode_used}): {voc.name} + {inst.name}")
