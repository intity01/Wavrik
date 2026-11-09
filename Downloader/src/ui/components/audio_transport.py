"""In-app studio audio transport controller with dual-deck playback and crossfading."""
from __future__ import annotations
from pathlib import Path
from PyQt6.QtCore import QObject, QUrl, pyqtSignal
try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError:  # pragma: no cover
    QAudioOutput, QMediaPlayer = None, None
from src.services.audio_crossfader import calculate_effective_volume, crossfader_gains

def _call(obj, fn: str, *args): return getattr(obj, fn)(*args) if (obj and hasattr(obj, fn)) else None
def _is_loaded(p) -> bool: return bool(p and (ms := getattr(QMediaPlayer, "MediaStatus", None)) and _call(p, "mediaStatus") in (ms.LoadedMedia, ms.BufferedMedia))
def _is_playing(p) -> bool: return bool(p and (ps := getattr(QMediaPlayer, "PlaybackState", None)) and _call(p, "playbackState") == ps.PlayingState)
def _init_deck(ctrl: AudioTransportController, d: str):
    if not QMediaPlayer or not QAudioOutput:
        return None, None
    p, o, a = QMediaPlayer(ctrl), QAudioOutput(ctrl), (d == "A")
    p.setAudioOutput(o)
    p.playbackStateChanged.connect(ctrl._on_playback_state if a else ctrl._on_playback_b_state)
    p.mediaStatusChanged.connect(ctrl._on_media_status if a else ctrl._on_media_b_status)
    p.positionChanged.connect(ctrl._on_position_changed if a else ctrl._on_position_b_changed)
    return p, o

def _play_track(ctrl: AudioTransportController, d: str, target: Path | None, sec: float | None) -> bool:
    if not target or not target.is_file():
        return False
    is_b, p = (d == "B"), (ctrl._player_b if d == "B" else ctrl._player)
    src, pos = (ctrl._source_b if is_b else ctrl._current_source), (max(0, int(sec * 1000)) if (sec is not None and sec >= 0) else None)
    if p and src == target:
        pos is not None and _call(p, "setPosition", pos)
        _is_playing(p) or _call(p, "play")
    else:
        _call(p, "stop")
        _call(p, "setSource", QUrl.fromLocalFile(str(target)))
        attr = "_pending_seek_b_ms" if is_b else "_pending_seek_ms"
        npos = getattr(ctrl, attr) if pos is None else pos
        if npos is not None and _is_loaded(p):
            npos = _call(p, "setPosition", npos)
        setattr(ctrl, attr, npos)
        setattr(ctrl, "_source_b" if is_b else "_current_source", target)
        _call(p, "play")
    ctrl._playing = True
    ctrl.stateChanged.emit(True, "B" if is_b else ctrl._active_slot)
    return True

def _seek(ctrl: AudioTransportController, d: str, sec: float) -> None:
    pos, is_b = max(0, int(sec * 1000)), (d == "B")
    p, src = (ctrl._player_b, ctrl._source_b) if is_b else (ctrl._player, ctrl._current_source)
    if src and _is_loaded(p):
        _call(p, "setPosition", pos)
    else:
        setattr(ctrl, "_pending_seek_b_ms" if is_b else "_pending_seek_ms", pos)
def _on_status(ctrl: AudioTransportController, d: str, st) -> None:
    attr, ms = ("_pending_seek_b_ms" if d == "B" else "_pending_seek_ms"), getattr(QMediaPlayer, "MediaStatus", None)
    if getattr(ctrl, attr) is not None and ms and st in (ms.LoadedMedia, ms.BufferedMedia):
        _call(ctrl._player_b if d == "B" else ctrl._player, "setPosition", getattr(ctrl, attr))
        setattr(ctrl, attr, None)
def _on_playback(ctrl: AudioTransportController, d: str, st) -> None:
    ps = getattr(QMediaPlayer, "PlaybackState", None)
    if ps and st == ps.StoppedState:
        ctrl._playing = ctrl.isDeckPlaying("B" if d == "A" else "A")
        ctrl.stateChanged.emit(False, ctrl._active_slot if d == "A" else "B")
class AudioTransportController(QObject):
    stateChanged, auditionChanged, positionChanged = pyqtSignal(bool, str), pyqtSignal(str), pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slot_a = self._slot_b = self._current_source = self._source_b = None
        self._pending_seek_ms = self._pending_seek_b_ms = None
        self._active_slot, self._stem_name, self._audition_label, self._playing = "A", "", "", False
        self._master_vol, (self._player_a, self._output_a) = 0.9, _init_deck(self, "A")
        self._player_b, self._output_b = _init_deck(self, "B")
        self._player, self._output = self._player_a, self._output_a
        self.setCrossfade(0.5, "equal_power")
    def _p(self, d: str = "A"): return self._player_b if (d or "A").strip().upper() == "B" else (self._player or self._player_a)
    def setCrossfade(self, pos: float, curve: str = "equal_power") -> None:
        self._crossfade_pos, self._curve = max(0.0, min(1.0, float(pos))), curve
        ga, gb = crossfader_gains(self._crossfade_pos, self._curve)
        _call(self._output_a, "setVolume", calculate_effective_volume(self._master_vol, 1.0, 1.0, ga))
        _call(self._output_b, "setVolume", calculate_effective_volume(self._master_vol, 1.0, 1.0, gb))
    def setPlaybackRate(self, deck: str, rate: float) -> None: _call(self._p(deck), "setPlaybackRate", max(0.5, min(2.0, float(rate))))
    def setSlotA(self, path: str | Path | None) -> None:
        self._slot_a, self._slot_b = (Path(path) if path else None), None
        self._current_source = self._source_b = self._pending_seek_ms = self._pending_seek_b_ms = None
        self._stem_name, self._audition_label, self._active_slot = "", "", "A"
        self.stop()
        self.auditionChanged.emit("")
    def setSlotB(self, path: str | Path | None) -> None:
        old_b, self._slot_b = self._slot_b, (Path(path) if path else None)
        if path is None:
            self._stem_name, self._audition_label, self._source_b = "", "", None
            _call(self._player_b, "stop")
            self.auditionChanged.emit("")
            if self._current_source == old_b:
                self._current_source, self._active_slot = None, "A"
                self.stop()
    def setStemPreview(self, path: str | Path | None, stem_name: str = "", auto_play: bool = False) -> None:
        self.setSlotB(path)
        name = str(stem_name).strip() if stem_name else (Path(path).stem if path else "")
        self._stem_name, self._audition_label = (name if path else ""), (f"Auditioning {name} (B)" if (name and path) else "")
        self.auditionChanged.emit(self._stem_name)
        if path and (auto_play or (self._playing and self._active_slot == "B")):
            self.playSlot("B", self.positionSec() if self._playing else None)
    def playSlot(self, slot: str = "A", start_sec: float | None = None) -> bool:
        self._active_slot = "B" if slot == "B" else "A"
        return _play_track(self, "A", self._slot_b if slot == "B" else self._slot_a, start_sec)
    def playDeck(self, deck: str = "A", start_sec: float | None = None) -> bool:
        return self.playSlot("A", start_sec) if (deck or "A").strip().upper() == "A" else _play_track(self, "B", self._slot_b, start_sec)
    def stopDeck(self, deck: str = "A") -> None:
        _call(self._p(deck), "stop")
        self._playing = self.isDeckPlaying("A") or self.isDeckPlaying("B")
        self.stateChanged.emit(False, (deck or "A").strip().upper())
    def seekDeck(self, deck: str = "A", sec: float = 0.0) -> None: _seek(self, "B" if (deck or "A").strip().upper() == "B" else "A", sec)
    def seek(self, sec: float) -> None: _seek(self, "A", sec)
    def deckPositionSec(self, deck: str = "A") -> float: return (p.position() / 1000.0) if ((p := self._p(deck)) and hasattr(p, "position") and p.position() > 0) else 0.0
    def isDeckPlaying(self, deck: str = "A") -> bool: return _is_playing(self._p(deck))
    def toggleAB(self, start_sec: float = 0.0) -> str:
        nxt = "B" if (self._active_slot == "A" and self._slot_b and self._slot_b.is_file()) else "A"
        pos = (_call(self._player, "position") or 0) / 1000.0
        self.playSlot(nxt, pos if (start_sec <= 0.0 and pos > 0) else start_sec)
        return self._active_slot
    def stop(self) -> None:
        _call(self._player, "stop")
        _call(self._player_b, "stop")
        self._pending_seek_ms = self._pending_seek_b_ms = None
        self._playing = False
        self.stateChanged.emit(False, self._active_slot)
    def isPlaying(self) -> bool: return self._playing
    def activeSlot(self) -> str: return self._active_slot
    def activeStem(self) -> str: return self._stem_name
    def auditionLabel(self) -> str: return self._audition_label
    def isAuditioning(self) -> bool: return bool(self._playing and self._active_slot == "B" and self._stem_name)
    def positionSec(self) -> float: return self.deckPositionSec("A")
    def _is_loaded(self) -> bool: return _is_loaded(self._player)
    def _on_position_changed(self, ms: int) -> None: self.positionChanged.emit(max(0.0, ms / 1000.0))
    def _on_position_b_changed(self, ms: int) -> None: self.positionChanged.emit(max(0.0, ms / 1000.0)) if (self._active_slot == "B" or not self.isDeckPlaying("A")) else None
    def _on_media_status(self, st) -> None: _on_status(self, "A", st)
    def _on_media_b_status(self, st) -> None: _on_status(self, "B", st)
    def _on_playback_state(self, st) -> None: _on_playback(self, "A", st)
    def _on_playback_b_state(self, st) -> None: _on_playback(self, "B", st)
