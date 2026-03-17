#!/usr/bin/env python3
"""Interactive terminal client for the PenguinAI chat endpoint.

Usage:
    python scripts/chat_client.py                   # default: http://localhost:8000
    python scripts/chat_client.py --url http://host:port
"""

import argparse
import os
import re
import sys
import textwrap

try:
    import httpx
except ImportError:
    sys.exit("httpx is required.  Install it with:  pip install httpx")

# ── Config ───────────────────────────────────────────────────────────────

CHAT_ENDPOINT = "/api/v1/chat"
WRAP_WIDTH = 88

# ── ANSI colours (minimal) ──────────────────────────────────────────────

BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[2m"
RESET = "\033[0m"

# ── Text cleaning (deterministic – no LLM calls) ────────────────────────

_MD_INLINE: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\*\*\*(.+?)\*\*\*"), r"\1"),       # bold-italic
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),            # bold
    (re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"), r"\1"),  # italic
    (re.compile(r"__(.+?)__"), r"\1"),                # bold alt
    (re.compile(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)"), r"\1"),  # italic alt
    (re.compile(r"`(.+?)`"), r"\1"),                  # inline code
]

_RE_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_RE_BULLET_STAR = re.compile(r"^[*+]\s+", re.MULTILINE)
_RE_HR = re.compile(r"^-{3,}$", re.MULTILINE)
_RE_STRAY_STAR = re.compile(r"(?<=\s)\*(?=\s)")
_RE_BLANK_RUNS = re.compile(r"\n{3,}")

# Markdown table detection
_RE_TABLE_SEP = re.compile(r"^\|?[\s:]*-{2,}[\s:]*(?:\|[\s:]*-{2,}[\s:]*)+\|?$")
_RE_TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")


def _parse_md_table(text: str) -> str | None:
    """If *text* is a markdown table block, return a plain-text version."""
    lines = [l.rstrip() for l in text.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return None

    sep_idx: int | None = None
    for i, l in enumerate(lines):
        if _RE_TABLE_SEP.match(l.strip()):
            sep_idx = i
            break
    if sep_idx is None:
        return None

    def _cells(row: str) -> list[str]:
        m = _RE_TABLE_ROW.match(row.strip())
        raw = m.group(1) if m else row
        return [c.strip() for c in raw.split("|")]

    headers = _cells(lines[sep_idx - 1]) if sep_idx > 0 else []
    data_lines = lines[sep_idx + 1:]
    if not data_lines:
        return None

    out: list[str] = []
    if headers:
        out.append("  ".join(headers))
        out.append("")
    for dl in data_lines:
        cells = _cells(dl)
        if headers and len(cells) == len(headers):
            parts = [f"{h}: {v}" for h, v in zip(headers, cells) if v]
            out.append(", ".join(parts))
        else:
            out.append("  ".join(cells))
    return "\n".join(out)


def _convert_comparison(text: str) -> str:
    """Detect markdown table blocks and convert inline."""
    result_parts: list[str] = []
    table_buf: list[str] = []
    in_table = False

    for line in text.splitlines():
        stripped = line.strip()
        is_table_line = (
            _RE_TABLE_ROW.match(stripped)
            or _RE_TABLE_SEP.match(stripped)
            or (in_table and stripped.startswith("|"))
        )

        if is_table_line:
            if not in_table:
                in_table = True
            table_buf.append(line)
        else:
            if in_table:
                converted = _parse_md_table("\n".join(table_buf))
                result_parts.append(converted if converted else "\n".join(table_buf))
                table_buf.clear()
                in_table = False
            result_parts.append(line)

    if table_buf:
        converted = _parse_md_table("\n".join(table_buf))
        result_parts.append(converted if converted else "\n".join(table_buf))

    return "\n".join(result_parts)


def _section_headings(text: str) -> str:
    """Convert 'Title: long paragraph...' to 'Title:\n  paragraph' for readability."""
    def _repl(m: re.Match) -> str:
        title = m.group(1).strip()
        body = m.group(2).strip()
        if len(body) > 100:
            return f"{title}:\n{body}"
        return m.group(0)
    return re.sub(r"^([A-Z][A-Za-z ]{2,30}):\s+(.{80,})", _repl, text, flags=re.MULTILINE)


def _clean_text(text: str) -> str:
    """Full markdown strip + whitespace normalisation."""
    # Tables first (before we strip pipes)
    text = _convert_comparison(text)

    # Headings
    text = _RE_HEADING.sub("", text)

    # Inline formatting
    for pat, repl in _MD_INLINE:
        text = pat.sub(repl, text)

    # Bullets / HRs / stray stars
    text = _RE_BULLET_STAR.sub("- ", text)
    text = _RE_HR.sub("", text)
    text = _RE_STRAY_STAR.sub("", text)

    # Section-heading tightening
    text = _section_headings(text)

    # Whitespace
    text = _RE_BLANK_RUNS.sub("\n\n", text)
    return text.strip()


def _wrap(text: str, width: int = WRAP_WIDTH) -> str:
    """Wrap paragraphs while preserving bullet lists and short lines."""
    out: list[str] = []
    for para in text.split("\n\n"):
        lines = para.strip().splitlines()
        # Keep bullet blocks as-is
        if all(l.strip().startswith("- ") or l.strip().startswith("  ") for l in lines if l.strip()):
            out.append("\n".join(l.rstrip() for l in lines))
        # Keep numbered lists as-is
        elif all(re.match(r"^\d+[.)]", l.strip()) for l in lines if l.strip()):
            out.append("\n".join(l.rstrip() for l in lines))
        else:
            joined = " ".join(l.strip() for l in lines)
            out.append(textwrap.fill(joined, width=width))
    return "\n\n".join(out)


# ── Output ───────────────────────────────────────────────────────────────


def _print_response(data: dict) -> None:
    """Format and print a ChatResponse dict."""
    answer = data.get("answer", "")
    sources = data.get("sources", [])
    confidence = data.get("confidence", 0.0)
    notes = data.get("notes", "")
    query_type = data.get("query_type", "")

    print()

    if query_type:
        print(f"{DIM}Query Type: {query_type}{RESET}")
        print()

    # Answer
    clean = _clean_text(answer) if answer else "No relevant data found."
    print(f"{CYAN}Answer:{RESET}")
    print(_wrap(clean))
    print()

    # Sources
    print(f"{GREEN}Sources:{RESET}")
    if sources:
        for s in sources:
            title = s.get("title", "?")
            rid = s.get("record_id", "?")
            print(f"  - {title} {DIM}({rid}){RESET}")
    else:
        print(f"  {DIM}None{RESET}")
    print()

    # Confidence
    print(f"{YELLOW}Confidence: {confidence:.2f}{RESET}")

    # Notes
    if notes:
        clean_notes = _clean_text(notes)
        print(f"\n{DIM}Notes:\n{clean_notes}{RESET}")

    print()


# ── Commands ─────────────────────────────────────────────────────────────

HELP_TEXT = f"""{BOLD}Commands{RESET}
  /help   Show this message
  /clear  Clear the terminal
  /exit   Quit  (or type: exit)
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="PenguinAI terminal chat client")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the PenguinAI backend (default: http://localhost:8000)",
    )
    args = parser.parse_args()
    base_url = args.url.rstrip("/")
    endpoint = f"{base_url}{CHAT_ENDPOINT}"

    print(f"\n{BOLD}PenguinAI Chat{RESET}")
    print(f"{DIM}{endpoint}{RESET}")
    print(f"Type {BOLD}/help{RESET} for commands.\n")

    client = httpx.Client(timeout=120.0)

    while True:
        try:
            query = input(f"{BOLD}> {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not query:
            continue

        # Built-in commands
        lower = query.lower()
        if lower in ("/exit", "exit", "/quit", "quit"):
            print("Bye!")
            break
        if lower == "/clear":
            os.system("cls" if os.name == "nt" else "clear")
            continue
        if lower == "/help":
            print(HELP_TEXT)
            continue

        # Send query
        print(f"{DIM}Thinking...{RESET}", end="", flush=True)
        try:
            resp = client.post(endpoint, json={"query": query})
            print(f"\r{' ' * 14}\r", end="")
            resp.raise_for_status()
            _print_response(resp.json())
        except (httpx.HTTPStatusError, httpx.ConnectError, Exception):
            print(f"\r{' ' * 14}\r", end="")
            print(f"{YELLOW}Error: Unable to get response.{RESET}\n")


if __name__ == "__main__":
    main()
