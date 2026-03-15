#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate traceability view from Obsidian frontmatter links.

Reads docs/**/*.md (excluding README/TEMPLATE), parses YAML frontmatter, and
builds a graph using:
  - up (parent)
  - down (child, derived from other docs' up)
  - related (cross)

Examples:
  python traceability.py --start RQ-FR-001 --depth 3 --mode tree --direction both --include-related
  python traceability.py --start RQ-FR-001 --mode csv --out reports/trace_edges.csv

Output is printed to stdout; optionally write to --out.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import yaml

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def extract_links(value: Any) -> List[str]:
    out: List[str] = []
    if value is None:
        return out
    if isinstance(value, list):
        for item in value:
            out.extend(extract_links(item))
        return out
    if isinstance(value, str):
        for m in LINK_RE.finditer(value):
            out.append(m.group(1).strip())
        return out
    return out


def normalize_link_id(doc_id: str) -> str:
    if "|" in doc_id:
        doc_id = doc_id.split("|", 1)[0]
    if "#" in doc_id:
        doc_id = doc_id.split("#", 1)[0]
    return doc_id.strip()


def split_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    if not text.startswith("---\n"):
        return ({}, text)
    end = text.find("\n---\n", 4)
    if end == -1:
        return ({}, text)
    fm_text = text[4:end]
    body = text[end + len("\n---\n") :]
    try:
        data = yaml.safe_load(fm_text) or {}
        if isinstance(data, dict):
            return (data, body)
    except Exception:
        pass
    return ({}, body)


def load_docs(docs_root: Path) -> Dict[str, Dict[str, Any]]:
    id_to = {}
    for p in docs_root.rglob("*.md"):
        if p.name in {"README.md", "TEMPLATE.md"}:
            continue
        fm, _ = split_frontmatter(p.read_text(encoding="utf-8"))
        doc_id = str(fm.get("id", "")).strip()
        if not doc_id:
            continue
        id_to[doc_id] = {
            "path": p,
            "fm": fm,
        }
    return id_to


def build_graph(id_to: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Set[str]]]:
    g: Dict[str, Dict[str, Set[str]]] = {}
    for doc_id, v in id_to.items():
        fm = v["fm"]
        up = {normalize_link_id(x) for x in extract_links(fm.get("up"))}
        related = {normalize_link_id(x) for x in extract_links(fm.get("related"))}
        g[doc_id] = {
            "up": {x for x in up if x},
            "down": set(),
            "related": {x for x in related if x},
        }

    # Derive down edges from reverse up links.
    for child_id, rels in g.items():
        for parent_id in rels["up"]:
            if parent_id in g:
                g[parent_id]["down"].add(child_id)

    return g


def tree_view(start: str, g: Dict[str, Dict[str, Set[str]]], depth: int, direction: str, include_related: bool) -> str:
    lines: List[str] = []
    lines.append(f"# Traceability: {start}")
    lines.append("")
    lines.append(f"- depth: {depth}")
    lines.append(f"- direction: {direction}")
    lines.append(f"- include_related: {include_related}")
    lines.append("")

    def neighbors(node: str) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        if node not in g:
            return out
        if direction in {"down", "both"}:
            out.extend([("down", x) for x in sorted(g[node]["down"])])
        if direction in {"up", "both"}:
            out.extend([("up", x) for x in sorted(g[node]["up"])])
        if include_related:
            out.extend([("related", x) for x in sorted(g[node]["related"])])
        return out

    visited: Set[str] = set([start])
    q = deque([(start, 0)])

    # Simple BFS tree (not a strict tree; we just indent by distance)
    while q:
        node, d = q.popleft()
        indent = "  " * d
        if d == 0:
            lines.append(f"- [[{node}]]")
        else:
            lines.append(f"{indent}- [[{node}]]")
        if d >= depth:
            continue
        for rel, nb in neighbors(node):
            if nb in visited:
                continue
            visited.add(nb)
            q.append((nb, d + 1))

    lines.append("")
    lines.append("## Edges (frontmatter)")
    lines.append("")
    for node in sorted(visited):
        if node not in g:
            continue
        for rel in ["up", "down", "related"]:
            if rel == "related" and not include_related:
                continue
            for t in sorted(g[node][rel]):
                if t in visited:
                    lines.append(f"- {node} --{rel}--> {t}")
    lines.append("")
    return "\n".join(lines)

def csv_edges(start: str, g: Dict[str, Dict[str, Set[str]]], depth: int, direction: str, include_related: bool) -> List[Tuple[str, str, str]]:
    # BFS to collect nodes
    def neighbors(node: str) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        if node not in g:
            return out
        if direction in {"down", "both"}:
            out.extend([("down", x) for x in g[node]["down"]])
        if direction in {"up", "both"}:
            out.extend([("up", x) for x in g[node]["up"]])
        if include_related:
            out.extend([("related", x) for x in g[node]["related"]])
        return out

    visited: Set[str] = set([start])
    q = deque([(start, 0)])
    edges: List[Tuple[str, str, str]] = []

    while q:
        node, d = q.popleft()
        if d >= depth:
            continue
        for rel, nb in neighbors(node):
            edges.append((node, rel, nb))
            if nb not in visited:
                visited.add(nb)
                q.append((nb, d + 1))
    return edges


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs-root", default="docs", help="docs root directory (default: docs)")
    ap.add_argument("--start", required=True, help="start doc ID (e.g., RQ-FR-001)")
    ap.add_argument("--depth", type=int, default=3, help="max hop depth (default: 3)")
    ap.add_argument("--direction", choices=["down", "up", "both"], default="both")
    ap.add_argument("--include-related", action="store_true")
    ap.add_argument("--mode", choices=["tree", "csv"], default="tree")
    ap.add_argument("--out", default="", help="write output to this path (optional)")
    args = ap.parse_args()

    root = Path(".").resolve()
    docs_root = (root / args.docs_root).resolve()
    id_to = load_docs(docs_root)
    g = build_graph(id_to)

    start = args.start.strip()
    if start not in g:
        raise SystemExit(f"ERROR: start id not found in docs: {start}")

    if args.mode == "tree":
        out_text = tree_view(start, g, args.depth, args.direction, args.include_related)
        if args.out:
            out_path = (root / args.out).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(out_text, encoding="utf-8")
        print(out_text)
        return 0

    edges = csv_edges(start, g, args.depth, args.direction, args.include_related)
    if args.out:
        out_path = (root / args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["from", "relation", "to"])
            w.writerows(edges)
    # stdout as CSV
    lines = ["from,relation,to"]
    lines.extend([f"{a},{r},{b}" for a, r, b in edges])
    text = "\n".join(lines)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
