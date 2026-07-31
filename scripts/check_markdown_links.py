#!/usr/bin/env python3
"""Check local Markdown links without following external URLs."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


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


def is_escaped(markdown: str, position: int) -> bool:
    backslashes = 0
    position -= 1
    while position >= 0 and markdown[position] == "\\":
        backslashes += 1
        position -= 1
    return backslashes % 2 == 1


def masked(markdown: str) -> str:
    return "".join(character if character in "\r\n" else " " for character in markdown)


def fence_delimiter(line: str) -> tuple[str, int, str] | None:
    position = 0
    while position < len(line) and position < 3 and line[position] == " ":
        position += 1
    if position >= len(line) or line[position] not in {"`", "~"}:
        return None

    marker = line[position]
    end = position
    while end < len(line) and line[end] == marker:
        end += 1
    if end - position < 3:
        return None
    return marker, end - position, line[end:]


def without_fenced_code(markdown: str) -> str:
    kept_lines: list[str] = []
    open_marker: str | None = None
    open_length = 0

    for line in markdown.splitlines(keepends=True):
        delimiter = fence_delimiter(line)
        if open_marker is None:
            if delimiter is None:
                kept_lines.append(line)
                continue
            open_marker, open_length, _ = delimiter
            kept_lines.append(masked(line))
            continue

        kept_lines.append(masked(line))
        if delimiter is None:
            continue
        marker, length, remainder = delimiter
        if marker == open_marker and length >= open_length and not remainder.strip():
            open_marker = None
            open_length = 0

    return "".join(kept_lines)


def closing_code_span(markdown: str, position: int, delimiter_length: int) -> int | None:
    while position < len(markdown):
        position = markdown.find("`", position)
        if position == -1:
            return None
        if is_escaped(markdown, position):
            position += 1
            continue

        end = position
        while end < len(markdown) and markdown[end] == "`":
            end += 1
        if end - position == delimiter_length:
            return position
        position = end
    return None


def without_inline_code(markdown: str) -> str:
    visible = list(markdown)
    position = 0

    while position < len(markdown):
        if markdown[position] != "`" or is_escaped(markdown, position):
            position += 1
            continue

        delimiter_end = position
        while delimiter_end < len(markdown) and markdown[delimiter_end] == "`":
            delimiter_end += 1
        delimiter_length = delimiter_end - position
        closing = closing_code_span(markdown, delimiter_end, delimiter_length)
        if closing is None:
            position = delimiter_end
            continue

        closing_end = closing + delimiter_length
        visible[position:closing_end] = masked(markdown[position:closing_end])
        position = closing_end

    return "".join(visible)


def closing_bracket(markdown: str, opening: int) -> int | None:
    depth = 1
    position = opening + 1
    while position < len(markdown):
        if markdown[position] == "\\":
            position += 2
            continue
        if markdown[position] == "[":
            depth += 1
        elif markdown[position] == "]":
            depth -= 1
            if depth == 0:
                return position
        position += 1
    return None


def skip_whitespace(markdown: str, position: int) -> int:
    while position < len(markdown) and markdown[position].isspace():
        position += 1
    return position


def closing_delimiter(markdown: str, position: int, delimiter: str) -> int | None:
    while position < len(markdown):
        if markdown[position] == delimiter and not is_escaped(markdown, position):
            return position
        position += 1
    return None


def link_closer_after_title(markdown: str, position: int) -> int | None:
    position = skip_whitespace(markdown, position)
    if position < len(markdown) and markdown[position] == ")":
        return position + 1
    if position >= len(markdown) or markdown[position] not in {'"', "'", "("}:
        return None

    title_closer = ")" if markdown[position] == "(" else markdown[position]
    title_end = closing_delimiter(markdown, position + 1, title_closer)
    if title_end is None:
        return None
    position = skip_whitespace(markdown, title_end + 1)
    if position >= len(markdown) or markdown[position] != ")":
        return None
    return position + 1


def angle_destination(markdown: str, position: int) -> tuple[str, int] | None:
    end = position + 1
    while end < len(markdown):
        if markdown[end] in "\r\n":
            return None
        if markdown[end] == ">" and not is_escaped(markdown, end):
            return markdown[position + 1 : end], end + 1
        end += 1
    return None


def inline_destination(markdown: str, opening: int) -> tuple[str, int] | None:
    position = skip_whitespace(markdown, opening + 1)
    if position >= len(markdown):
        return None

    if markdown[position] == "<":
        parsed_angle = angle_destination(markdown, position)
        if parsed_angle is None:
            return None
        destination, position = parsed_angle
        link_end = link_closer_after_title(markdown, position)
        return (destination, link_end) if link_end is not None else None

    destination_start = position
    parenthesis_depth = 0
    while position < len(markdown):
        character = markdown[position]
        if character == "\\":
            position += 2
            continue
        if character == "(":
            parenthesis_depth += 1
        elif character == ")":
            if parenthesis_depth == 0:
                return markdown[destination_start:position], position + 1
            parenthesis_depth -= 1
        elif character.isspace() and parenthesis_depth == 0:
            link_end = link_closer_after_title(markdown, position)
            if link_end is None:
                return None
            return markdown[destination_start:position], link_end
        position += 1
    return None


def reference_destination(line: str, position: int) -> str | None:
    position = skip_whitespace(line, position)
    if position >= len(line):
        return None
    if line[position] == "<":
        parsed_angle = angle_destination(line, position)
        return parsed_angle[0] if parsed_angle is not None else None

    end = position
    while end < len(line) and not line[end].isspace():
        end += 2 if line[end] == "\\" and end + 1 < len(line) else 1
    return line[position:end] or None


def normalized_reference(label: str) -> str:
    return " ".join(label.split()).casefold()


def reference_definitions(markdown: str) -> dict[str, str]:
    definitions: dict[str, str] = {}
    for line in markdown.splitlines():
        opening = len(line) - len(line.lstrip(" "))
        if opening > 3 or opening >= len(line) or line[opening] != "[":
            continue
        label_end = closing_bracket(line, opening)
        if label_end is None or label_end + 1 >= len(line) or line[label_end + 1] != ":":
            continue
        destination = reference_destination(line, label_end + 2)
        if destination is None:
            continue
        definitions.setdefault(normalized_reference(line[opening + 1 : label_end]), destination)
    return definitions


def markdown_destinations(markdown: str) -> list[str]:
    visible_markdown = without_inline_code(without_fenced_code(markdown))
    definitions = reference_definitions(visible_markdown)
    destinations: list[str] = []
    position = 0

    while position < len(visible_markdown):
        opening = visible_markdown.find("[", position)
        if opening == -1:
            break
        if is_escaped(visible_markdown, opening):
            position = opening + 1
            continue

        label_end = closing_bracket(visible_markdown, opening)
        if label_end is None:
            break
        after_label = label_end + 1
        if after_label < len(visible_markdown) and visible_markdown[after_label] == "(":
            parsed_destination = inline_destination(visible_markdown, after_label)
            if parsed_destination is not None:
                destination, position = parsed_destination
                destinations.append(destination)
                continue
        elif after_label < len(visible_markdown) and visible_markdown[after_label] == "[":
            reference_end = closing_bracket(visible_markdown, after_label)
            if reference_end is not None:
                reference = visible_markdown[after_label + 1 : reference_end]
                if not reference:
                    reference = visible_markdown[opening + 1 : label_end]
                destination = definitions.get(normalized_reference(reference))
                if destination is not None:
                    destinations.append(destination)
                position = reference_end + 1
                continue
        elif after_label >= len(visible_markdown) or visible_markdown[after_label] != ":":
            reference = visible_markdown[opening + 1 : label_end]
            destination = definitions.get(normalized_reference(reference))
            if destination is not None:
                destinations.append(destination)
                position = after_label
                continue
        position = label_end + 1

    return destinations


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
    for parsed_destination in markdown_destinations(markdown):
        destination = local_target(parsed_destination)
        if destination is None:
            continue
        link_count += 1
        target = (markdown_file.parent / destination).resolve()
        if not target.exists():
            missing.append(f"{markdown_file}: missing local target {parsed_destination.strip()}")
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
