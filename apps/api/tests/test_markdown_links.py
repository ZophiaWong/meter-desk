from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CHECKER = REPOSITORY_ROOT / "scripts" / "check_markdown_links.py"


def run_checker(*markdown_files: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), *(str(markdown_file) for markdown_file in markdown_files)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_accepts_existing_local_targets_and_ignores_fenced_code(tmp_path: Path) -> None:
    guide = tmp_path / "guide"
    guide.mkdir()
    (guide / "target file.md").write_text("# Target\n", encoding="utf-8")
    source = tmp_path / "source.md"
    source.write_text(
        "[target](guide/target%20file.md?source=runbook#section)\n"
        "```markdown\n"
        "[example only](missing-in-code.md)\n"
        "```\n",
        encoding="utf-8",
    )

    result = run_checker(source)

    assert result.returncode == 0, result.stderr
    assert "Checked 1 Markdown file(s), 1 local link(s)." in result.stdout


def test_ignores_links_inside_inline_code(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("Use `[example](missing-in-code.md)` as syntax.\n", encoding="utf-8")

    result = run_checker(source)

    assert result.returncode == 0, result.stderr
    assert "Checked 1 Markdown file(s), 0 local link(s)." in result.stdout


def test_accepts_balanced_parentheses_in_inline_destination(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a_(b).md").write_text("# Target\n", encoding="utf-8")
    source = tmp_path / "source.md"
    source.write_text("[x](docs/a_(b).md)\n", encoding="utf-8")

    result = run_checker(source)

    assert result.returncode == 0, result.stderr
    assert "Checked 1 Markdown file(s), 1 local link(s)." in result.stdout


def test_accepts_angle_bracket_destination_with_parentheses(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a_(b).md").write_text("# Target\n", encoding="utf-8")
    source = tmp_path / "source.md"
    source.write_text("[x](<docs/a_(b).md>)\n", encoding="utf-8")

    result = run_checker(source)

    assert result.returncode == 0, result.stderr
    assert "Checked 1 Markdown file(s), 1 local link(s)." in result.stdout


def test_accepts_reference_style_link_to_existing_target(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "target.md").write_text("# Target\n", encoding="utf-8")
    source = tmp_path / "source.md"
    source.write_text("[x][ref]\n\n[ref]: docs/target.md\n", encoding="utf-8")

    result = run_checker(source)

    assert result.returncode == 0, result.stderr
    assert "Checked 1 Markdown file(s), 1 local link(s)." in result.stdout


def test_escaped_backticks_do_not_hide_a_broken_link(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text(r"\`[broken](missing.md)\`" "\n", encoding="utf-8")

    result = run_checker(source)

    assert result.returncode == 1
    assert f"{source}: missing local target missing.md" in result.stderr


def test_reports_missing_local_targets(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("[missing](missing.md)\n", encoding="utf-8")

    result = run_checker(source)

    assert result.returncode == 1
    assert f"{source}: missing local target missing.md" in result.stderr
