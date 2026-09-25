"""Heuristics for common AI-generated product UI anti-patterns."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
DECORATIVE_PATTERNS = (
    "qlineargradient",
    "linear-gradient",
    "radial-gradient",
    "background-clip: text",
    "backdrop-filter",
    "box-shadow",
    "drop-shadow",
    "qgraphicsdropshadoweffect",
    "glassmorphism",
    "accent glow",
)
MARKETING_FILLER = (
    "revolutionary",
    "next-generation",
    "game-changing",
    "supercharge",
    "unlock your",
    "effortlessly",
    "seamless experience",
    "powered by ai",
    "magic experience",
    "all-in-one solution",
)
GENERIC_ACTIONS = ("get started", "learn more", "discover", "explore now", "try it now")
RADIUS = re.compile(r"border-radius:\s*(\d+)px", re.IGNORECASE)
SIDE_STRIPE = re.compile(r"border-(?:left|right):\s*(\d+)px", re.IGNORECASE)
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF]")


def collect_errors() -> list[str]:
    errors: list[str] = []
    py_files = [ROOT / "main.py", *sorted(SOURCE.rglob("*.py"))]
    for path in py_files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        relative = path.relative_to(ROOT)
        for pattern in DECORATIVE_PATTERNS:
            if pattern in lower:
                errors.append(f"{relative}: decorative AI-default pattern '{pattern}'")
        if _is_ui(path):
            errors.extend(_copy_errors(relative, lower))
            if EMOJI.search(text):
                errors.append(f"{relative}: emoji used in product UI")
        for value in RADIUS.findall(text):
            if int(value) > 12:
                errors.append(f"{relative}: border radius {value}px exceeds the 12px product limit")
        for value in SIDE_STRIPE.findall(text):
            if int(value) > 1:
                errors.append(f"{relative}: decorative side stripe border is not allowed")
    return errors


def _copy_errors(relative: Path, lower: str) -> list[str]:
    errors: list[str] = []
    for phrase in MARKETING_FILLER:
        if phrase in lower:
            errors.append(f"{relative}: generic marketing phrase '{phrase}'")
    for phrase in GENERIC_ACTIONS:
        if re.search(rf"[\"']{re.escape(phrase)}[\"']", lower):
            errors.append(f"{relative}: vague action label '{phrase}'")
    if "lorem ipsum" in lower or "placeholder text" in lower:
        errors.append(f"{relative}: placeholder copy found")
    return errors


def _is_ui(path: Path) -> bool:
    return any(part in {"ui", "components", "pages"} for part in path.parts)


def main() -> int:
    errors = collect_errors()
    if errors:
        print("AI-slop check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("AI-slop check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
