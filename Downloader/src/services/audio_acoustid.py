"""AcoustID and MusicBrainz metadata lookup services."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

import requests

_ACOUSTID_URL = "https://api.acoustid.org/v2/lookup"
_MB_URL = "https://musicbrainz.org/ws/2/recording/{mbid}?fmt=json&inc=artists+releases+genres"
_USER_AGENT = "Wavrik/2.1 ( contact@wavrik.local )"
_last_mb_request = 0.0
_MB_CACHE: dict[str, dict[str, Any]] = {}


def _rate_limit_mb(interval: float = 1.05) -> None:
    global _last_mb_request
    wait = interval - (time.monotonic() - _last_mb_request)
    if wait > 0:
        time.sleep(wait)
    _last_mb_request = time.monotonic()


def _parse_acoustid_response(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("status") != "ok":
        err = data.get("error", "Unknown error")
        return {"status": "error", "error": err.get("message", "Unknown error") if isinstance(err, dict) else str(err)}
    results = data.get("results", [])
    if not results:
        return {"status": "not_found", "title": "", "artist": "", "album": "", "mbid": ""}
    best_res = max(results, key=lambda r: float(r.get("score", 0.0)))
    recordings = best_res.get("recordings", [])
    if not recordings:
        return {"status": "not_found", "title": "", "artist": "", "album": "", "mbid": ""}
    rec = recordings[0]
    artist = ", ".join(a.get("name", "") for a in rec.get("artists", []) if isinstance(a, dict) and a.get("name"))
    rgroups = rec.get("releasegroups", []) or rec.get("releases", [])
    album = rgroups[0].get("title", "") if rgroups and isinstance(rgroups[0], dict) else ""
    return {
        "status": "ok",
        "title": rec.get("title", ""),
        "artist": artist,
        "album": album,
        "mbid": rec.get("id", ""),
        "score": float(best_res.get("score", 0.0)),
    }


def lookup_acoustid(duration: int, fingerprint: str, api_key: str = "8XaBELgH", request_fn=None) -> dict[str, Any]:
    payload = {"client": api_key, "duration": str(duration), "fingerprint": fingerprint, "meta": "recordings+releasegroups"}
    try:
        if request_fn is not None:
            try:
                resp = request_fn(_ACOUSTID_URL, data=payload, timeout=10.0)
            except TypeError:
                resp = request_fn(_ACOUSTID_URL, params=payload)
        else:
            resp = requests.post(_ACOUSTID_URL, data=payload, timeout=10.0)
        return _parse_acoustid_response(resp if isinstance(resp, dict) else resp.json())
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _parse_musicbrainz_response(data: dict[str, Any], mbid: str) -> dict[str, Any]:
    artist = "".join(c.get("name", "") + c.get("joinphrase", "") for c in data.get("artist-credit", []) if isinstance(c, dict)).strip()
    releases = data.get("releases", [])
    album, date, track = "", "", ""
    if releases and isinstance(releases[0], dict):
        rel = releases[0]
        album, date = rel.get("title", ""), rel.get("date", "")
        media = rel.get("media", [])
        if media and isinstance(media[0], dict):
            tracks = media[0].get("track", [])
            track = str(tracks[0].get("number", "")) if tracks and isinstance(tracks[0], dict) else ""
    genres = data.get("genres", [])
    genre = genres[0].get("name", "").capitalize() if genres and isinstance(genres[0], dict) else ""
    return {"status": "ok", "title": data.get("title", ""), "artist": artist, "album": album, "date": date, "track": track, "genre": genre, "mbid": mbid}


def lookup_musicbrainz_recording(mbid: str, request_fn=None) -> dict[str, Any]:
    if not mbid:
        return {"status": "error", "error": "Missing MBID"}
    if mbid in _MB_CACHE:
        return dict(_MB_CACHE[mbid])
    url, headers = _MB_URL.format(mbid=mbid), {"User-Agent": _USER_AGENT}
    try:
        if request_fn is not None:
            try:
                resp = request_fn(url, headers=headers, timeout=10.0)
            except TypeError:
                resp = request_fn(url)
        else:
            _rate_limit_mb()
            resp = requests.get(url, headers=headers, timeout=10.0)
        result = _parse_musicbrainz_response(resp if isinstance(resp, dict) else resp.json(), mbid)
        if result.get("status") == "ok":
            _MB_CACHE[mbid] = result
        return result
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def lookup_audio_file(file_path: str | Path, api_key: str = "8XaBELgH", request_fn=None) -> dict[str, Any]:
    from src.services.audio_fingerprint import fingerprint_audio_file
    dur, fp = fingerprint_audio_file(Path(file_path))
    if not fp:
        return {"status": "error", "error": "Could not fingerprint audio"}
    res = lookup_acoustid(dur, fp, api_key=api_key, request_fn=request_fn)
    if res.get("status") == "ok" and res.get("mbid"):
        mb = lookup_musicbrainz_recording(res["mbid"], request_fn=request_fn)
        if mb.get("status") == "ok":
            res.update({k: v for k, v in mb.items() if v and k != "status"})
    return res


def parse_filename_heuristic(path_or_name: str) -> dict[str, str]:
    stem = Path(path_or_name).stem
    cleaned = re.sub(r"\[[^\]]*\]|\((?:official|audio|video|lyrics|hd)[^\)]*\)", "", stem, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned.replace("_", " ")).strip()
    title, artist, album, track = cleaned, "", "", ""
    parts = [p.strip() for p in cleaned.split(" - ") if p.strip()]
    if len(parts) >= 4 and parts[2].isdigit():
        artist, album, track, title = parts[0], parts[1], parts[2], " - ".join(parts[3:])
    elif len(parts) >= 3:
        track, artist, album, title = (parts[0], parts[1], "", " - ".join(parts[2:])) if parts[0].isdigit() else ("", parts[0], parts[1], " - ".join(parts[2:]))
    elif len(parts) == 2:
        track, artist, title = (parts[0], "", parts[1]) if parts[0].isdigit() else ("", parts[0], parts[1])
    elif len(parts) == 1:
        m = re.match(r"^(\d+)[\.\s]+(.*)$", cleaned)
        if m:
            track, title = m.group(1), m.group(2).strip()
    return {"title": title, "artist": artist, "album": album, "date": "", "track": track, "genre": ""}
