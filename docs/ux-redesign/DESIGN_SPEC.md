# UX/UI Redesign Spec — Media Downloader PRO + Audio Tools

Prototype: [ux_prototype.html](file:///C:/Users/Intity01/.gemini/antigravity/brain/00de4d26-842c-4cd0-b91f-40a175da1618/ux_prototype.html) (interactive, TH/EN, mock only — no download or audio processing).
Design source: owner decisions in `.hermes/discovery/` (Q01–Q57, R01–R25, F01–F20). Nothing here invents a new product decision; where a decision is missing it is listed under **Open decisions**.

## 1. Problem with the current UI

| Today | Why it fails the owner's goal |
|---|---|
| 3 pages: Downloads / History / Settings. No place for key, BPM, pitch, A/B. | The real workflow (download → key/BPM → shift → listen → export WAV) leaves the app. |
| History and a future file list would be two separate lists. | Q30 asks for **one** searchable library for downloaded and local files. |
| Theme tokens are navy (`#0B0F16` bg, `#2563EB` accent) with a light theme toggle. | Q21/Q22/Q31: dark only, neutral black/gray, **one teal accent**. |
| `checkUpdatesOnStartup = True` in [config.py](file:///c:/Users/Intity01/Desktop/MediaDownloaderPRO_v2.1_Windows_Source_Ready/MediaDownloaderPRO_v2.1/Downloader/src/core/config.py#L12-L32). | Q49: explicit "Check for updates" only; no silent checking. |

## 2. Information architecture

```
Sidebar (icons + text labels, Q29)         Bottom
  Downloads   Library   Audio Tools         Settings
```

- **Downloads** — paste link / open file, queue, per-item actions.
- **Library** — replaces History. Search by title, both sources (Downloaded / Local file), `Open in Audio Tools`, `Show in folder`. Index only; never copies media (Q30).
- **Audio Tools** — the workbench. Reached only by an explicit button (Q27: no automatic page switch).
- **Settings** — app-level only. Restore last page on start (Q26).

Legacy video/playlist features stay in code, hidden from the primary UI (Q41).

## 3. Screens

### 3.1 Downloads
- One row: link field, `Add link`, `Open audio file` (Q26: both obvious when empty).
- One panel: save folder + `Change folder`; output summary "WAV, 24-bit. A WAV file does not add quality the source does not have." (Q42 + quality disclosure). Format list lives in **Advanced** (MP3/FLAC).
- Queue rows: title, plain-text state badge (never color-only), progress, actions. Completed row's primary action is `Open in Audio Tools`.
- `Download all (N)` is disabled when N = 0 (existing rule in PROJECT_RULES).
- Empty state teaches the flow in two sentences; no hero art, no metrics.
- Error row: red is used only here and for destructive actions (PROJECT_RULES).

### 3.2 Library
Search field + `Open audio file`. Row = title, format · duration, source badge, `Open in Audio Tools` (primary), `Show in folder`. Empty search → one line of text.

### 3.3 Audio Tools (Workbench, R01–R10)
Layout: waveform + controls on the left, track/export inspector on the right (312 px). Below 900 px the inspector stacks under the stage.

```
[ file name · format badge ]                         [Change file]
[ waveform with 15 s draggable section ]
[ Preview section: 10 s | 15 s | 30 s   0:30 – 0:45 ]
┌ dock ───────────────────────────────────────────────────────┐
│ PITCH    [−]  −2 semitones  [+]  [Reset]  ☐ extended ±12     │
│ COMPARE  [Build preview] [Original|Adjusted] [Play]          │
│ status line (aria-live)                                       │
└──────────────────────────────────────────────────────────────┘
Inspector: Track (key, BPM, derived target key, tempo helper)
           Export (file name, Export WAV, Advanced)
```

State rules (all verified in the prototype):

| Rule | Source | Behaviour |
|---|---|---|
| Range | R07 | ±5 default; ±12 only after ticking the checkbox, with a quality warning. Unticking while beyond ±5 clamps. |
| Stale preview | R08 | Changing pitch, section start or length stops Adjusted playback, returns to Original, re-locks Adjusted, shows "build a new preview". |
| Build done | R09 | Only unlocks Adjusted. Never plays or switches source. |
| Export gate | R10 | No current, heard preview → dialog: `Back to preview` / `Export anyway`. Not shown at 0 shift (nothing to export). |
| Key/BPM honesty | D10, Q18 | Badge says **Estimate** or **Corrected by you**; line "Analysis is not certain…" is always visible until corrected; alternatives and Half/Double are one click. |
| Target key | Q13 | Always labelled "derived from {key} and {shift}"; never presented as a fresh analysis. |
| Heavy jobs | Q40 | One audio job at a time (stated in Settings). |

### 3.4 Settings
Language (Thai/English, remembered, Q25) · downloads at once (1–5) · clipboard watch (text On/Off, not color) · `Check for updates` (explicit) · `Clear history and per-file settings` (confirm dialog; states songs and exports are never deleted, Q45). No theme control: dark is the only theme.

## 4. Visual system

Neutral solids, 1 px separators, radius 6/8/10, no gradient, glow, blur or shadow (PROJECT_RULES). Accent only on: current nav item border, primary button, active segment, selection. Body 14 px, min target 38 px, focus ring 2 px.

| Token | Current ([tokens.py](file:///c:/Users/Intity01/Desktop/MediaDownloaderPRO_v2.1_Windows_Source_Ready/MediaDownloaderPRO_v2.1/Downloader/src/ui/theme/tokens.py)) | Proposed |
|---|---|---|
| bg | `#0B0F16` | `#0F1113` |
| panel | `#101722` | `#15181B` |
| surface | `#151E2B` | `#1A1E22` |
| surface_hover | `#1A2636` | `#23282D` |
| border / strong | `#263449` / `#3A4B63` | `#2A3036` / `#454E56` |
| text / muted | `#F3F6FA` / `#9AA8BA` | `#ECEFF1` / `#A3ADB5` |
| accent (new token) | user-selectable, default `#2563EB` | `#2BC3B0`, text on accent `#06201C` |
| warning / danger | `#F59E0B` / `#EF4444` | `#F0B64E` / `#FF9A8B` (text-safe on dark) |

Contrast is **not yet measured** with a tool; verify ≥ 4.5:1 for every text/background pair before shipping. The "choose accent color" setting becomes unnecessary (single accent) — removing it needs your OK.

## 5. Implementation mapping (PyQt6, ≤150 lines per file)

| New / changed | Responsibility |
|---|---|
| `ui/theme/tokens.py`, `qss_*` | Swap palette, add `accent`; drop LIGHT. |
| `ui/main_window.py` | Add `Library` + `Audio Tools` pages (use a helper; file is near the limit). |
| `ui/pages/library_page.py` (+ `library_card.py`) | Replaces `history_page`/`history_card`; same `HistoryManager` data. |
| `ui/pages/audio_page.py`, `ui/components/waveform.py`, `pitch_strip.py`, `track_panel.py`, `export_panel.py` | Workbench, split by responsibility. |
| `domain/audio_models.py`, `audio_render.py`, `audio_analysis.py` | No Qt imports; FFmpeg render per spike 004 (single pass, cancellable, `.part` → `os.replace`). |
| `ui/workers/audio_worker.py` | One job at a time, cancel token, cleanup in `window_lifecycle.py`. |
| `core/runtime.py` | Add `find_ffmpeg_exe()` — current `find_ffmpeg()` returns the **folder**. |

Order: tokens → Library (rename, low risk) → Audio page shell with render only → analysis (key/BPM) last, because it is the weakest-evidenced part.

## 6. What the prototype does not prove

- Not native: Qt widgets, DPI scaling, keyboard-only and screen-reader behaviour are untested.
- No audio is analysed or played; key/BPM/waveform are fake. Sound quality evidence lives only in spikes 001–004.
- Thai strings are working translations, not reviewed by a Thai reader.
- Waveform section is click/arrow-key only (no drag yet).

## 7. Open decisions (need you)

1. **Product name** — none approved (Keylane rejected; Wavrik/Tonlo/Lunto uncleared). Prototype shows the current name.
2. **History → Library** merge (new page replaces the old one).
3. **Remove light theme and accent picker** (conflicts with dark-only/one-accent decisions).
4. **Vocal separation slot** — owner wants it only if it beats Cubase (F19); spike 005 has no result. Not drawn in the UI; reserve a collapsed "Separate vocals" section in the Audio page later.
5. **Startup update check** — change default to off.
6. **macOS code** — kept for now; Q48 says Windows first, not Windows only.
