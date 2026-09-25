"""Static project rules that do not require third-party linters."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
BANNED_TEXT = ("qlineargradient", "linear-gradient", ".gemini/antigravity", "QGraphicsDropShadowEffect")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF]")
HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def main() -> int:
    errors: list[str] = []
    py_files = [ROOT / "main.py", *sorted(SOURCE.rglob("*.py"))]
    for path in py_files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        relative = path.relative_to(ROOT)
        if len(lines) > 150:
            errors.append(f"{relative}: {len(lines)} lines (max 150)")
        lower = text.lower()
        for term in BANNED_TEXT:
            if term.lower() in lower:
                errors.append(f"{relative}: banned pattern {term}")
        if "print(" in text:
            errors.append(f"{relative}: print() is banned in production")
        if EMOJI.search(text):
            errors.append(f"{relative}: emoji found in production UI/source")
        if path.parent.name in {"components", "pages", "workers"} and "setStyleSheet" in text:
            errors.append(f"{relative}: inline stylesheet found")
        if path.parent.name in {"components", "pages", "workers"} and HEX.search(text):
            if path.name != "settings_page.py":
                errors.append(f"{relative}: hardcoded hex color outside theme tokens")
        errors.extend(_ast_errors(path, text))
    if errors:
        print("Rule check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Rule check passed.")
    return 0


def _param_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    args = node.args
    params: list[str] = [a.arg for a in getattr(args, "posonlyargs", [])]
    params.extend(a.arg for a in args.args)
    if params and params[0] in ("self", "cls"):
        params.pop(0)
    count = len(params) + len(args.kwonlyargs)
    if args.vararg is not None:
        count += 1
    if args.kwarg is not None:
        count += 1
    return count


def _ast_errors(path: Path, text: str) -> list[str]:
    relative = path.relative_to(ROOT)
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [f"{relative}: syntax error at line {exc.lineno}"]
    errors: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > 35:
                errors.append(f"{relative}:{node.lineno} function {node.name} is {length} lines (max 35)")
            count = _param_count(node)
            if count > 6:
                errors.append(f"{relative}:{node.lineno} function {node.name} has {count} parameters (max 6)")
        elif isinstance(node, ast.ClassDef):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > 120:
                errors.append(f"{relative}:{node.lineno} class {node.name} is {length} lines (max 120)")
    return errors


if __name__ == "__main__":
    raise SystemExit(main())
