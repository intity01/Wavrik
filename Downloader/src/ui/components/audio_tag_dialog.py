"""Modal dialog for editing and auto-detecting audio file metadata tags."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QVBoxLayout

from src.services.audio_acoustid import lookup_audio_file, parse_filename_heuristic
from src.services.audio_tagger import AudioMetadata, apply_audio_metadata, read_audio_metadata
from src.ui.components.controls import LineEdit, PrimaryPushButton, PushButton, ToolButton


class AudioTagDialog(QDialog):
    def __init__(self, audio_path: str | Path, parent=None):
        super().__init__(parent)
        self._path = Path(audio_path).resolve()
        self.setWindowTitle("Edit Audio Tags")
        self.setMinimumWidth(480)
        self._build_ui()
        self._load_existing()

    def _build_form(self) -> QFormLayout:
        form = QFormLayout()
        self.titleEdit, self.artistEdit = LineEdit(), LineEdit()
        self.albumEdit, self.dateEdit = LineEdit(), LineEdit()
        self.trackEdit, self.genreEdit = LineEdit(), LineEdit()
        self.coverEdit = LineEdit()
        self.browseCoverBtn = ToolButton("Browse...")
        self.browseCoverBtn.clicked.connect(self._browse_cover)
        cov_row = QHBoxLayout()
        cov_row.addWidget(self.coverEdit, 1)
        cov_row.addWidget(self.browseCoverBtn)
        for lbl, w in (
            ("Title:", self.titleEdit), ("Artist:", self.artistEdit),
            ("Album:", self.albumEdit), ("Year/Date:", self.dateEdit),
            ("Track #:", self.trackEdit), ("Genre:", self.genreEdit),
        ):
            form.addRow(QLabel(lbl), w)
        form.addRow(QLabel("Cover Art:"), cov_row)
        return form

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)
        root.addWidget(QLabel(f"Tag Metadata: {self._path.name}", objectName="SectionTitle"))
        root.addLayout(self._build_form())
        self.statusLabel = QLabel("Ready.", objectName="MutedText")
        root.addWidget(self.statusLabel)
        btn_row = QHBoxLayout()
        self.detectBtn, self.cancelBtn = PushButton("Auto-Detect (AcoustID)"), PushButton("Cancel")
        self.applyBtn = PrimaryPushButton("Apply Tags")
        self.detectBtn.clicked.connect(self._auto_detect)
        self.cancelBtn.clicked.connect(self.reject)
        self.applyBtn.clicked.connect(self._apply_tags)
        for w in (self.detectBtn, None, self.cancelBtn, self.applyBtn):
            btn_row.addStretch(1) if w is None else btn_row.addWidget(w)
        root.addLayout(btn_row)

    def _load_existing(self) -> None:
        meta = read_audio_metadata(self._path)
        self.titleEdit.setText(meta.title)
        self.artistEdit.setText(meta.artist)
        self.albumEdit.setText(meta.album)
        self.dateEdit.setText(meta.date)
        self.trackEdit.setText(meta.track)
        self.genreEdit.setText(meta.genre)

    def _browse_cover(self) -> None:
        filt = "Image files (*.jpg *.jpeg *.png);;All files (*.*)"
        sel, _ = QFileDialog.getOpenFileName(self, "Choose Cover Image", str(self._path.parent), filt)
        if sel:
            self.coverEdit.setText(sel)

    def _auto_detect(self) -> None:
        self.statusLabel.setText("Querying AcoustID & MusicBrainz...")
        res = lookup_audio_file(self._path)
        title, artist = res.get("title", ""), res.get("artist", "")
        album, date, track, genre = res.get("album", ""), res.get("date", ""), res.get("track", ""), res.get("genre", "")
        if not (title or artist):
            h = parse_filename_heuristic(self._path.name)
            title, artist, album, track = h.get("title", ""), h.get("artist", ""), h.get("album", ""), h.get("track", "")
            src_desc = "parsed from filename"
        else:
            score = res.get("score", 0.0)
            src_desc = f"matched via AcoustID (score {score:.2f})"
        for edit, val in ((self.titleEdit, title), (self.artistEdit, artist), (self.albumEdit, album), (self.dateEdit, date), (self.trackEdit, track), (self.genreEdit, genre)):
            val and edit.setText(val)
        self.statusLabel.setText(f"Auto-detection applied ({src_desc}).")

    def _apply_tags(self) -> None:
        meta = AudioMetadata(
            title=self.titleEdit.text().strip(),
            artist=self.artistEdit.text().strip(),
            album=self.albumEdit.text().strip(),
            date=self.dateEdit.text().strip(),
            track=self.trackEdit.text().strip(),
            genre=self.genreEdit.text().strip(),
            cover_path=self.coverEdit.text().strip(),
        )
        try:
            apply_audio_metadata(self._path, meta)
            self.statusLabel.setText("Tags saved successfully.")
            self.accept()
        except Exception as err:
            self.statusLabel.setText(f"Error saving tags: {err}")
