#!/usr/bin/env python3
"""Clause-level redline between two versions of a document.

Usage:
    python3 redline.py theirs.md ours.md --out redline.md
    python3 redline.py v1.md v2.md --summary-only

Matches clauses by number first and by heading second, so a renumbered clause is
reported as moved rather than as a deletion plus an insertion. Flags changes
that touch money, liability, termination, IP or disputes as material, because a
redline where every change looks equal gets skimmed.

Exit codes: 0 no differences, 1 differences found, 2 bad invocation.
Stdlib only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

CLAUSE_HEAD_RE = re.compile(r"^\s*(?:#{1,6}\s*)?(\d+(?:\.\d+)*)[.)]?\s+(\S.*)$")

MATERIAL_CUES = {
    "money": ("fee", "payment", "invoice", "price", "rate", "retention", "interest", "deposit", "escalat"),
    "liability": ("liabilit", "indemnif", "indemnity", "cap", "consequential", "insurance"),
    "exit": ("terminat", "notice period", "renewal", "lock-in", "cure", "surviv"),
    "ownership": ("intellectual property", "assign", "licence", "license", "confidential", "data"),
    "disputes": ("arbitrat", "jurisdiction", "governing law", "seat"),
    "scope": ("scope", "deliverable", "acceptance", "exclusion", "change order", "dependenc"),
}


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()



def _heading_mode(text: str) -> bool:
    """True when the document numbers its clauses as markdown headings.

    In that case list items like "1." inside a clause are not clause heads, and
    treating them as such silently merges or overwrites real clauses.
    """
    return bool(re.search(r"^#{1,6}\s*\d", text, re.M))


def parse(text: str) -> dict:
    """Return {clause_number: (heading, body)} plus a preamble under key ''."""
    out, current, preamble = {}, None, []
    headings_only = _heading_mode(text)
    for line in text.splitlines():
        m = CLAUSE_HEAD_RE.match(line)
        if headings_only and not line.lstrip().startswith("#"):
            m = None
        if m and len(m.group(1)) <= 9:
            if current:
                out[current[0]] = (current[1], "\n".join(current[2]).strip())
            current = [m.group(1), m.group(2).strip(), []]
        elif current:
            current[2].append(line)
        else:
            preamble.append(line)
    if current:
        out[current[0]] = (current[1], "\n".join(current[2]).strip())
    pre = "\n".join(preamble).strip()
    if pre:
        out[""] = ("Preamble", pre)
    return out


def materiality(text: str) -> list:
    low = text.lower()
    return [cat for cat, cues in MATERIAL_CUES.items() if any(c in low for c in cues)]


def inline_diff(old: str, new: str) -> str:
    """Word-level markdown redline: ~~removed~~ **added**."""
    a, b = old.split(), new.split()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            out.append(" ".join(a[i1:i2]))
        elif tag == "delete":
            out.append("~~" + " ".join(a[i1:i2]) + "~~")
        elif tag == "insert":
            out.append("**" + " ".join(b[j1:j2]) + "**")
        else:
            out.append("~~" + " ".join(a[i1:i2]) + "~~ **" + " ".join(b[j1:j2]) + "**")
    return " ".join(x for x in out if x)


def match_moved(old: dict, new: dict) -> dict:
    """Map old-only numbers to new-only numbers where headings match."""
    old_only = [k for k in old if k not in new]
    new_only = [k for k in new if k not in old]
    moved = {}
    for ok in old_only:
        oh = normalise(old[ok][0]).lower()
        for nk in new_only:
            if nk in moved.values():
                continue
            if normalise(new[nk][0]).lower() == oh:
                moved[ok] = nk
                break
    return moved


def build(old_path: Path, new_path: Path) -> tuple:
    old = parse(old_path.read_text(encoding="utf-8", errors="replace"))
    new = parse(new_path.read_text(encoding="utf-8", errors="replace"))
    moved = match_moved(old, new)

    changes = []  # (kind, key, heading, detail, cats)
    for key in sorted(old, key=lambda k: [int(x) for x in k.split(".")] if k else [-1]):
        target = moved.get(key, key)
        if target not in new:
            changes.append(("deleted", key, old[key][0], "", materiality(old[key][0] + old[key][1])))
            continue
        o_head, o_body = old[key]
        n_head, n_body = new[target]
        if normalise(o_body) == normalise(n_body) and normalise(o_head) == normalise(n_head):
            if key != target:
                changes.append(("moved", f"{key} → {target}", n_head, "", materiality(n_head)))
            continue
        detail = inline_diff(normalise(o_head + " " + o_body), normalise(n_head + " " + n_body))
        label = key if key == target else f"{key} → {target}"
        changes.append(("amended", label, n_head, detail, materiality(o_body + n_body + o_head)))
    for key in new:
        if key not in old and key not in moved.values():
            changes.append(("inserted", key, new[key][0], normalise(new[key][1])[:1200],
                            materiality(new[key][0] + new[key][1])))
    return changes, len(old), len(new)


def render(changes: list, old_n: int, new_n: int, old_name: str, new_name: str, summary_only: bool) -> str:
    material = [c for c in changes if c[4]]
    lines = [
        f"# Redline: {old_name} → {new_name}",
        "",
        f"{old_n} clauses in, {new_n} clauses out. {len(changes)} change(s), "
        f"{len(material)} touching money, liability, exit, ownership or disputes.",
        "",
        "## Change summary",
        "",
        "| # | Clause | Change | Touches |",
        "|---|---|---|---|",
    ]
    for kind, key, head, _, cats in changes:
        lines.append(f"| {key} | {head[:60]} | {kind} | {', '.join(cats) if cats else '—'} |")
    if summary_only:
        return "\n".join(lines) + "\n"

    lines += ["", "## Clause detail", ""]
    for kind, key, head, detail, cats in changes:
        flag = "  *(material)*" if cats else ""
        lines.append(f"### {key} — {head}{flag}")
        lines.append("")
        lines.append(f"*{kind}*")
        lines.append("")
        if detail:
            lines.append(detail)
            lines.append("")
    lines += [
        "## Cover note",
        "",
        "1. Changes marked material alter money, risk allocation or the ability to exit.",
        "2. Everything else is drafting and can be accepted in one pass.",
        "3. Reply with acceptance or a counter on the material items only.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Clause-level redline between two documents.")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--out", help="write markdown here instead of stdout")
    ap.add_argument("--summary-only", action="store_true")
    args = ap.parse_args()

    old_path, new_path = Path(args.old).expanduser(), Path(args.new).expanduser()
    for p in (old_path, new_path):
        if not p.exists():
            print(f"no such file: {p}", file=sys.stderr)
            return 2

    changes, old_n, new_n = build(old_path, new_path)
    text = render(changes, old_n, new_n, old_path.name, new_path.name, args.summary_only)
    if args.out:
        Path(args.out).expanduser().write_text(text, encoding="utf-8")
        print(f"wrote {args.out} — {len(changes)} change(s)")
    else:
        print(text)
    return 1 if changes else 0


if __name__ == "__main__":
    raise SystemExit(main())
