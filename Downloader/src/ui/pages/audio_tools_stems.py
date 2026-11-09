"""4-Stem separation rack, background execution dispatch, auditioning, and stem loading."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from src.services.audio_stems import is_separator_available
from src.services.audio_stems_4stem import synthesize_instrumental
from src.ui.components.controls import ComboBox, PushButton, ToolButton
from src.ui.i18n import tr
from src.ui.workers.stem_worker import Stem4SeparationWorker, Stem4Signals, StemSeparationWorker, StemSignals

STEM_ALL_MODES = (
    ("HT-Demucs 4-Stem (Studio Quality)", "htdemucs"), ("Instant Studio DSP 4-Stem (Zero-Download)", "dsp_4stem"),
    ("Ensemble RoFormer (2-Stem Best SDR)", "roformer_ensemble"), ("Mel-Band RoFormer Fast (2-Stem)", "roformer_fast"),
    ("Instant Studio DSP (2-Stem)", "dsp_2stem"),
)
_STEMS = (("vocals", "Vocals"), ("drums", "Drums"), ("bass", "Bass"), ("other", "Other"), ("inst", "Instrumental"))


def _stem_btn_row(page, prefix: str, title: str, on_click) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(QLabel(title, objectName="MutedText"))
    for stem, text in _STEMS:
        lbl = f"Preview {text}" if prefix == "preview" else f"Use {text}"
        btn = ToolButton(lbl.replace("Instrumental", "Inst") if prefix == "preview" else lbl)
        setattr(page, f"{prefix}{stem.capitalize()}Btn", btn)
        btn.clicked.connect(lambda _c=False, s=stem: on_click(s))
        btn.setEnabled(False)
        row.addWidget(btn)
    row.addStretch(1)
    return row


def build_stem_rack(page) -> QFrame:
    card, layout = QFrame(objectName="AudioToolsCard"), QVBoxLayout()
    card.setLayout(layout)
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setSpacing(6)
    r0, page.lblStem, page.stemModeCombo = QHBoxLayout(), QLabel("STEM SEPARATOR", objectName="FieldLabel"), ComboBox()
    for label, key in STEM_ALL_MODES:
        page.stemModeCombo.addItem(label, key)
    if not is_separator_available():
        page.stemModeCombo.setCurrentIndex(1)
    page.separateStemsBtn = PushButton("Separate Stems")
    page.separateStemsBtn.clicked.connect(page._separate_stems)
    for w, st in ((page.lblStem, 0), (page.stemModeCombo, 1), (page.separateStemsBtn, 0)):
        r0.addWidget(w, st)
    r_aud, r_load = _stem_btn_row(page, "preview", "Audition (B):", page._audition_stem), _stem_btn_row(page, "load", "Load Stem:", page._load_stem)
    page.previewStemBtn = page.previewVocalsBtn
    page.stemNoticeLabel = QLabel("", objectName="MutedText", wordWrap=True)
    page.stemNoticeLabel.hide()
    for item in (r0, r_aud, r_load, page.stemNoticeLabel):
        layout.addLayout(item) if isinstance(item, QHBoxLayout) else layout.addWidget(item)
    from .audio_tools_presenter import update_stem_guidance
    page.stemModeCombo.currentIndexChanged.connect(lambda: update_stem_guidance(page))
    return card


def dispatch_stem_separation(page, mode: str) -> None:
    page._busy, out_dir = True, page._cfg.getDownloadPath("audio")
    page.separateStemsBtn.setEnabled(False)
    is_4 = mode in {"htdemucs", "htdemucs_ft", "dsp_4stem"}
    page.statusLabel.setText(tr("at.separating_4stem" if is_4 else "at.separating", getattr(page, "_lang", "en")))
    sig = Stem4Signals() if is_4 else StemSignals()
    setattr(page, "_stem4Signals" if is_4 else "_stemSignals", sig)
    sig.separated.connect(lambda *args: (handle_4stems_ready if is_4 else handle_2stems_ready)(page, *args))
    sig.error.connect(page._on_error)
    worker = Stem4SeparationWorker(page._source, out_dir, mode, sig) if is_4 else StemSeparationWorker(page._source, out_dir, mode, sig)
    page._activeWorker = worker
    page._pool.start(worker)


def handle_4stems_ready(page, vocals: str, drums: str, bass: str, other: str, mode: str) -> None:
    page._busy, page._vocalsStem, page._drumsStem = False, Path(vocals), Path(drums)
    page._bassStem, page._otherStem = Path(bass), Path(other)
    page.separateStemsBtn.setEnabled(True)
    inst = synthesize_instrumental(page._source, page._vocalsStem) if page._source else None
    page._instStem = inst if (inst and inst.is_file()) else page._otherStem
    _update_stem_buttons(page, True, True)
    for p in (page._vocalsStem, page._drumsStem, page._bassStem, page._otherStem, page._instStem):
        _log_stem_export(page, p)
    page._lastExport = page._vocalsStem
    page.openFolderBtn.show()
    fmt = tr("at.stems_ready_4stem", getattr(page, "_lang", "en"))
    page.statusLabel.setText(fmt.format(mode=mode) if "{mode}" in fmt else f"4 Stems ready ({mode}): Vocals, Drums, Bass, Other")


def handle_2stems_ready(page, vocals: str, inst: str, mode: str) -> None:
    page._busy, page._vocalsStem, page._instStem = False, Path(vocals), Path(inst)
    page.separateStemsBtn.setEnabled(True)
    _update_stem_buttons(page, True, False)
    for p in (page._vocalsStem, page._instStem):
        _log_stem_export(page, p)
    page._lastExport = page._vocalsStem if page._vocalsStem.is_file() else page._instStem
    page.openFolderBtn.show()
    page.statusLabel.setText(f"Stems ready ({mode}): {page._vocalsStem.name} + {page._instStem.name}")


def _log_stem_export(page, path: Path | None) -> None:
    if path and path.is_file():
        if page._hist:
            page._hist.addEntry("", path.stem, "audio", "WAV", str(path), True, path.stat().st_size, status="completed")
        page.fileExported.emit(str(path))


def _update_stem_buttons(page, has_voc_inst: bool, has_all_4: bool) -> None:
    for btn in (page.loadVocalsBtn, page.loadInstBtn, page.previewVocalsBtn, page.previewInstBtn):
        btn.setEnabled(has_voc_inst)
    for btn in (page.loadDrumsBtn, page.loadBassBtn, page.loadOtherBtn, page.previewDrumsBtn, page.previewBassBtn, page.previewOtherBtn):
        btn.setEnabled(has_all_4)


def reset_stem_controls(page) -> None:
    _update_stem_buttons(page, False, False)


def _stem_dict(p) -> dict[str, tuple[Path | None, str]]:
    return {
        "vocals": (getattr(p, "_vocalsStem", None), "Vocals"), "drums": (getattr(p, "_drumsStem", None), "Drums"),
        "bass": (getattr(p, "_bassStem", None), "Bass"), "other": (getattr(p, "_otherStem", None), "Other"),
        "inst": (getattr(p, "_instStem", None), "Instrumental"),
    }


def audition_stem(page, s: str) -> None:
    path, name = _stem_dict(page).get(s, (None, ""))
    if path and path.is_file():
        page.transport.setStemPreview(path, name, auto_play=True)
        page.transport.playSlot("B", page.waveformWidget.seekPosition())
        tpl = tr("at.audition_active", getattr(page, "_lang", "en"))
        page.statusLabel.setText(tpl.format(stem=name) if "{stem}" in tpl else f"Auditioning {name} (Slot B)")


def load_stem(page, s: str) -> None:
    path, _ = _stem_dict(page).get(s, (None, ""))
    if path and path.is_file():
        page.loadFile(path)
