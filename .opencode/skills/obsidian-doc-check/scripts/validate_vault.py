#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


RE_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[^\]]*)\]\]")
RE_FM = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
RE_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
RE_INLINE_CODE = re.compile(r"`[^`]+`")

REQUIRED_FRONTMATTER = {
    "id",
    "title",
    "doc_type",
    "phase",
    "version",
    "status",
    "owner",
    "created",
    "updated",
    "up",
    "related",
    "tags",
}


@dataclass
class Issue:
    path: Path
    message: str


def parse_frontmatter_keys(text: str) -> set[str]:
    m = RE_FM.match(text)
    if not m:
        return set()
    block = m.group(1)
    keys = set()
    for line in block.splitlines():
        if not line.strip() or line.strip().startswith("-"):
            continue
        if ":" in line:
            k = line.split(":", 1)[0].strip()
            if k:
                keys.add(k)
    return keys


def parse_frontmatter_id(text: str) -> str | None:
    m = re.search(r"^id:\s*(.+)$", text, re.MULTILINE)
    if not m:
        return None
    return m.group(1).strip().strip("'").strip('"')


def collect_doc_ids(files: list[Path]) -> set[str]:
    ids: set[str] = {"index"}
    for f in files:
        doc_id = f.stem
        ids.add(doc_id)
    return ids


def validate(files: list[Path], known_ids: set[str]) -> list[Issue]:
    issues: list[Issue] = []

    for f in files:
        text = f.read_text(encoding="utf-8")
        keys = parse_frontmatter_keys(text)
        missing = sorted(REQUIRED_FRONTMATTER - keys)
        if missing:
            issues.append(Issue(f, f"missing_frontmatter_keys={','.join(missing)}"))

        fm_id = parse_frontmatter_id(text)
        if fm_id and fm_id != f.stem:
            issues.append(Issue(f, f"filename_id_mismatch: id={fm_id}, filename={f.stem}"))

        scan_text = RE_CODE_FENCE.sub("", text)
        scan_text = RE_INLINE_CODE.sub("", scan_text)
        for target in RE_WIKILINK.findall(scan_text):
            if target == "ID":
                continue
            if target not in known_ids:
                issues.append(Issue(f, f"broken_wikilink={target}"))

    return issues


def write_report(report: Path, issues: list[Issue], checked: int) -> None:
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# doc_check", "", f"- checked_files: {checked}", f"- issues: {len(issues)}", ""]
    if issues:
        lines.append("## issues")
        for i in issues:
            lines.append(f"- {i.path}: {i.message}")
    else:
        lines.append("## result")
        lines.append("- OK")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Obsidian docs vault")
    parser.add_argument("--docs-root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--targets", nargs="*")
    args = parser.parse_args()

    docs_root = Path(args.docs_root).resolve()
    all_docs = sorted(p for p in docs_root.rglob("*.md") if p.is_file())
    if args.targets:
        files = [Path(t).resolve() for t in args.targets if Path(t).suffix == ".md"]
    else:
        files = list(all_docs)

    issues = validate(files, collect_doc_ids(all_docs))
    write_report(Path(args.report).resolve(), issues, len(files))

    if issues:
        for i in issues[:50]:
            print(f"ERROR {i.path}: {i.message}")
        return 1
    print(f"validate_vault: checked={len(files)}, issues=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
