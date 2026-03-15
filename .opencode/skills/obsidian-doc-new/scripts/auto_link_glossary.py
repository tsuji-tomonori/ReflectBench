#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]+`")


def list_markdown_files(root: Path) -> list[Path]:
    if root.is_file() and root.suffix == ".md":
        return [root]
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def load_glossary_terms(docs_root: Path) -> dict[str, str]:
    # convention: glossary docs are RQ-GL-*.md and title is the display term.
    terms: dict[str, str] = {}
    for path in docs_root.rglob("RQ-GL-*.md"):
        text = path.read_text(encoding="utf-8")
        doc_id = path.stem
        match = re.search(r"^title:\s*(.+)$", text, re.MULTILINE)
        if match:
            title = match.group(1).strip().strip("'").strip('"')
            if title:
                terms[title] = doc_id
    return dict(sorted(terms.items(), key=lambda x: len(x[0]), reverse=True))


def protect_segments(text: str) -> tuple[str, list[str]]:
    saved: list[str] = []

    def repl(m: re.Match[str]) -> str:
        saved.append(m.group(0))
        return f"__PROTECTED_{len(saved)-1}__"

    out = CODE_FENCE_RE.sub(repl, text)
    out = INLINE_CODE_RE.sub(repl, out)
    return out, saved


def unprotect_segments(text: str, saved: list[str]) -> str:
    for i, seg in enumerate(saved):
        text = text.replace(f"__PROTECTED_{i}__", seg)
    return text


def autolink_content(content: str, terms: dict[str, str]) -> str:
    fm_match = FRONTMATTER_RE.match(content)
    frontmatter = fm_match.group(0) if fm_match else ""
    body = content[len(frontmatter) :]

    protected, saved = protect_segments(body)
    for term, term_id in terms.items():
        # Normalize bare glossary links to ID-based links.
        protected = re.sub(
            rf"\[\[{re.escape(term)}\]\]",
            f"[[{term_id}|{term}]]",
            protected,
        )
        # Auto-link plain terms (skip already-linked terms).
        protected = re.sub(
            rf"(?<!\[\[){re.escape(term)}(?!\]\])",
            f"[[{term_id}|{term}]]",
            protected,
        )
    body_out = unprotect_segments(protected, saved)
    return frontmatter + body_out


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-link glossary terms in markdown files")
    parser.add_argument("paths", nargs="+", help="Docs path(s) or markdown file(s)")
    args = parser.parse_args()

    roots = [Path(p).resolve() for p in args.paths]
    docs_root = next((p for p in roots if p.name == "docs" and p.is_dir()), roots[0])
    terms = load_glossary_terms(docs_root)

    updated = 0
    for root in roots:
        for md in list_markdown_files(root):
            original = md.read_text(encoding="utf-8")
            changed = autolink_content(original, terms)
            if changed != original:
                md.write_text(changed, encoding="utf-8")
                updated += 1

    print(f"auto_link_glossary: updated={updated}, glossary_terms={len(terms)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
