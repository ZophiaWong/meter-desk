#!/usr/bin/env python3
"""Check local Markdown links without following external URLs."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FENCE_PATTERN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
LINK_PATTERN = re.compile(r"\[[^]\n]*\]\(([^)\n]+)\)")


def tracked_markdown_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "README.md", "AGENTS.md", "docs"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode().strip() or "git ls-files failed"
        raise RuntimeError(message)

    files = []
    for relative_name in result.stdout.decode().split("\0"):
        if not relative_name.endswith(".md"):
            continue
        if relative_name.startswith("docs/archive/"):
            continue
        files.append(REPOSITORY_ROOT / relative_name)
    return files


def non_fenced_lines(markdown: str) -> str:
    kept_lines: list[str] = []
    fence_marker: str | None = None

    for line in markdown.splitlines(keepends=True):
        fence_match = FENCE_PATTERN.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence_marker is None:
                fence_marker = marker[0]
            elif marker[0] == fence_marker:
                fence_marker = None
            continue
        if fence_marker is None:
            kept_lines.append(line)

    return "".join(kept_lines)


def without_inline_code(markdown: str) -> str:
    kept_parts: list[str] = []
    position = 0

    while position < len(markdown):
        if markdown[position] != "`":
            kept_parts.append(markdown[position])
            position += 1
            continue

        delimiter_end = position
        while delimiter_end < len(markdown) and markdown[delimiter_end] == "`":
            delimiter_end += 1
        delimiter = markdown[position:delimiter_end]
        closing = markdown.find(delimiter, delimiter_end)
        if closing == -1:
            kept_parts.append(delimiter)
            position = delimiter_end
            continue

        position = closing + len(delimiter)

    return "".join(kept_parts)


def local_target(destination: str) -> str | None:
    destination = destination.strip()
    if destination.startswith("<") and destination.endswith(">"):
        destination = destination[1:-1].strip()
    if not destination or destination.startswith("#"):
        return None

    parts = urlsplit(destination)
    if parts.scheme.lower() in {"http", "https", "mailto"}:
        return None
    return unquote(parts.path)


def missing_targets(markdown_file: Path) -> tuple[int, list[str]]:
    try:
        markdown = markdown_file.read_text(encoding="utf-8")
    except OSError as error:
        return 0, [f"{markdown_file}: could not read Markdown file: {error}"]

    link_count = 0
    missing: list[str] = []
    visible_markdown = without_inline_code(non_fenced_lines(markdown))
    for match in LINK_PATTERN.finditer(visible_markdown):
        destination = local_target(match.group(1))
        if destination is None:
            continue
        link_count += 1
        target = (markdown_file.parent / destination).resolve()
        if not target.exists():
            missing.append(f"{markdown_file}: missing local target {match.group(1).strip()}")
    return link_count, missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local links in Markdown files.")
    parser.add_argument("markdown_files", nargs="*", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        markdown_files = args.markdown_files or tracked_markdown_files()
    except RuntimeError as error:
        print(f"Could not find tracked Markdown files: {error}", file=sys.stderr)
        return 2

    checked_links = 0
    missing: list[str] = []
    for markdown_file in markdown_files:
        link_count, file_missing = missing_targets(markdown_file)
        checked_links += link_count
        missing.extend(file_missing)

    if missing:
        print("\n".join(missing), file=sys.stderr)
        return 1

    print(f"Checked {len(markdown_files)} Markdown file(s), {checked_links} local link(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
