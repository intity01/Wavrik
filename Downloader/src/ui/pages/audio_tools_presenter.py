"""Presentation and stem-separation workflow helpers for Audio Tools UI."""

from __future__ import annotations

from pathlib import Path

from src.services.audio_analysis import camelot_code, enharmonic_key, mirex_key_score, transpose_key
from src.services.audio_camelot import get_harmonic_neighbors
from src.services.audio_pitch import build_export_filename
from src.services.audio_stems import is_separator_available
from src.services.platform_actions import open_parent
from src.ui.i18n import tr
from src.ui.theme.key_colors import apply_key_property


def update_stem_guidance(page) -> None:
    if not hasattr(page, "stemNoticeLabel"):
        return
    mode = str(page.stemModeCombo.currentData() or "htdemucs")
    needed = mode in {"htdemucs", "htdemucs_ft", "roformer_ensemble", "roformer_fast"} and not is_separator_available()
    page.stemNoticeLabel.setText(tr("at.ai_separator_required", getattr(page, "_lang", "en"))) if needed else None
    page.stemNoticeLabel.setVisible(needed)


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


def apply_analysis_result(page, result: dict) -> None:
    key, bpm = str(result.get("key") or "C major"), float(result.get("bpm") or 120.0)
    page._candidates, page._harmonic_cands = list(result.get("key_candidates") or []), get_harmonic_neighbors(key)
    page.detectedKeyCombo.setCurrentText(key)
    page.bpmSpin.blockSignals(True)
    page.bpmSpin.setValue(bpm)
    page.bpmSpin.blockSignals(False)
    page.targetBpmSpin.setValue(bpm)
    page.badgeLabel.setText(str(result.get("badge") or "Experimental / Estimate"))
    page.sectionKeyLabel.setText(f"Section Key: {result.get('section_summary', '--')}")
    page.waveformWidget.setPeaks(result.get("peaks", []), result.get("duration_sec", 0.0), result.get("section_summary", ""))
    page.waveformWidget.setBpm(bpm)
    if result.get("spectrogram") is not None:
        page.waveformWidget.setSpectrogram(result["spectrogram"])
    populate_candidate_buttons(page.candButtons, page._candidates, key)
    populate_harmonic_buttons(page.camelotButtons, page._harmonic_cands)
    update_preview_labels(page)
    page.statusLabel.setText(format_analysis_status(key, bpm, result))


def start_stem_separation(page) -> None:
    if not page._source or page._busy:
        return
    mode = str(page.stemModeCombo.currentData() or "htdemucs")
    if mode in {"htdemucs", "htdemucs_ft", "roformer_ensemble", "roformer_fast"} and not is_separator_available():
        msg = tr("at.ai_separator_required", getattr(page, "_lang", "en"))
        page.statusLabel.setText(msg)
        hasattr(page, "stemNoticeLabel") and (page.stemNoticeLabel.setText(msg) or page.stemNoticeLabel.show())
        return
    from .audio_tools_stems import dispatch_stem_separation
    dispatch_stem_separation(page, mode)


def on_stems_ready(page, vocals_str: str, inst_str: str, mode_used: str) -> None:
    from .audio_tools_stems import handle_2stems_ready
    handle_2stems_ready(page, vocals_str, inst_str, mode_used)


def start_pitch_render(page, target: Path, fmt: str, is_preview: bool) -> None:
    from src.ui.workers.audio_worker import AudioToolSignals, PitchJob, RenderPitchWorker
    page._busy, page._signals = True, AudioToolSignals()
    page.statusLabel.setText(tr("at.rendering", getattr(page, "_lang", "en"))) or page.exportBtn.setEnabled(False)
    page._signals.rendered.connect(page._on_rendered)
    page._signals.error.connect(page._on_error)
    job = PitchJob(page._source, target, page.semitoneSpin.value(), str(page.engineCombo.currentData() or "r3_finer"), fmt, is_preview, page._tempo_ratio(), page.waveformWidget.seekPosition())
    page._activeWorker = RenderPitchWorker(job, page._signals)
    page._pool.start(page._activeWorker)


def handle_pitch_rendered(page, path_str: str, is_preview: bool) -> None:
    page._busy, out = False, Path(path_str)
    page.exportBtn.setEnabled(True)
    if is_preview:
        page.transport.setSlotB(out) or page.transport.playSlot("B")
        page.statusLabel.setText(f"Playing Shifted Preview (B): {out.name}")
        return
    page._lastExport = out
    page.openFolderBtn.show() or page.statusLabel.setText(f"Exported: {out.name}")
    page._hist and out.is_file() and page._hist.addEntry("", out.stem, "audio", out.suffix.lstrip(".").upper(), str(out), True, out.stat().st_size, status="completed")
    page.fileExported.emit(str(out))


def set_controls_enabled(page, enabled: bool) -> None:
    for w in (page.reanalyzeBtn, page.separateStemsBtn, page.previewOrigBtn, page.previewShiftedBtn, page.stopAudioBtn, page.exportBtn, *page.candButtons, *page.camelotButtons):
        w.setEnabled(enabled)


def compute_tempo_ratio(page) -> float:
    return max(0.5, min(2.0, page.targetBpmSpin.value() / max(30.0, page.bpmSpin.value())))


def build_export_name(page, fmt: str) -> str:
    tb = page.targetBpmSpin.value() if abs(compute_tempo_ratio(page) - 1.0) >= 0.005 else 0.0
    key_str = transpose_key(page.detectedKeyCombo.currentText() or "C major", page.semitoneSpin.value())
    return build_export_filename(page._source, page.semitoneSpin.value(), key_str, fmt, tb)


def open_export_folder(page) -> None:
    page._lastExport and page._lastExport.exists() and open_parent(page._lastExport)
