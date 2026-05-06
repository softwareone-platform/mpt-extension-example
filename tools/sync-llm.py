#!/usr/bin/env python3
"""Mirror the canonical agent-instructions body from LLM.md into per-tool target files.

Each target carries its own per-tool header plus a `<!-- CONTENT -->...<!-- /CONTENT -->`
block whose content is overwritten by LLM.md. Markers must be on their own lines (the
regex is line-anchored) so references to the marker strings inside body text — e.g.
within backticks — do not confuse the parser.

Run after editing LLM.md. Exits 1 if any target was rewritten, 0 if already in sync,
so the script can double as a CI guard.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "LLM.md"
TARGETS = (
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / ".github" / "copilot-instructions.md",
)

MARKER_RE = re.compile(
    r"^<!-- CONTENT -->$.*?^<!-- /CONTENT -->$",
    re.DOTALL | re.MULTILINE,
)


def sync(target: Path, body: str) -> bool:
    text = target.read_text(encoding="utf-8")
    if len(MARKER_RE.findall(text)) != 1:
        sys.exit(
            f"{target.relative_to(REPO_ROOT)}: expected exactly one "
            f"<!-- CONTENT -->...<!-- /CONTENT --> block"
        )
    new_block = f"<!-- CONTENT -->\n{body}\n<!-- /CONTENT -->"
    new_text = MARKER_RE.sub(lambda _: new_block, text, count=1)
    if new_text == text:
        return False
    target.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    body = SOURCE.read_text(encoding="utf-8").strip("\n")
    changed = [t for t in TARGETS if sync(t, body)]
    for t in changed:
        print(f"updated: {t.relative_to(REPO_ROOT)}", file=sys.stderr)
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
