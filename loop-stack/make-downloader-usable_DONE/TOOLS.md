# Discovered Tools
## Status
CONFIRMED LOCAL — manual fallback after resource-scout subagent was unavailable

See `loop-stack/.global/TOOLS.md` for the complete environment inventory and exact invocation syntax.

## Loop-specific blockers
- The project `.venv` launcher is stale and points to a missing uv-managed Python 3.11 runtime.
- The usable host interpreter is Python 3.14.6, but it lacks PyQt6, pytest, and Ruff.
- Compile and AI-slop checks run; the rule check currently reports five size violations.
