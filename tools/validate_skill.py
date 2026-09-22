#!/usr/bin/env python3
"""Validate a Claude Skill: frontmatter, budgets, links, scripts, hygiene.

Usage:
    python3 validate_skill.py <skill-dir>            # report
    python3 validate_skill.py <skill-dir> --strict   # warnings are fatal
    python3 validate_skill.py <skill-dir> --json     # machine-readable

Exit codes: 0 clean, 1 problems found, 2 bad invocation.
Stdlib only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TRIGGER_CUES = ("use this", "use when", "use it when", "whenever", "trigger", "also use")
BOUNDARY_CUES = ("not for", "do not use", "don't use", "instead", "rather than", "never use this")
MANDATE_RE = re.compile(r"\b(ALWAYS|NEVER|MUST|REQUIRED|MANDATORY)\b")
LINK_RE = re.compile(r"(?:`|\(|\s)((?:references|scripts|assets|schemas|evals|examples)/[\w\-./]+\.\w+)")
SECRET_RES = [
    (re.compile(r"sk-ant-[A-Za-z0-9\-_]{10,}"), "Anthropic API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key block"),
    (re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9\-_]{16,}['\"]"), "hardcoded credential"),
]

# Python 3.9 has no sys.stdlib_module_names; this covers what skills actually import.
STDLIB_FALLBACK = {
    "argparse", "ast", "base64", "collections", "csv", "datetime", "decimal", "difflib",
    "functools", "glob", "hashlib", "html", "io", "itertools", "json", "logging", "math",
    "os", "pathlib", "random", "re", "shutil", "smtplib", "sqlite3", "statistics", "string",
    "subprocess", "sys", "tempfile", "textwrap", "time", "typing", "unicodedata", "urllib",
    "uuid", "warnings", "xml", "zipfile", "zoneinfo", "dataclasses", "enum", "copy",
}

# Budgets
BODY_LINES_IDEAL = 250
BODY_LINES_HARD = 500
DESC_WORDS_IDEAL = 120
DESC_CHARS_MIN = 40
DESC_CHARS_WEAK = 200
DESC_CHARS_MAX = 1024
REF_TOC_LINES = 300
MANDATE_LIMIT = 8


class Report:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []  # level, where, message
        self.stats: dict = {}

    def add(self, level: str, where: str, message: str) -> None:
        self.items.append((level, where, message))

    def error(self, where: str, msg: str) -> None:
        self.add("ERROR", where, msg)

    def warn(self, where: str, msg: str) -> None:
        self.add("WARN", where, msg)

    def info(self, where: str, msg: str) -> None:
        self.add("INFO", where, msg)

    @property
    def errors(self) -> int:
        return sum(1 for lvl, _, _ in self.items if lvl == "ERROR")

    @property
    def warnings(self) -> int:
        return sum(1 for lvl, _, _ in self.items if lvl == "WARN")


def parse_frontmatter(text: str) -> tuple[dict, str, list[str]]:
    """Minimal YAML-subset frontmatter parser. Returns (data, body, problems).

    Supports: key: value, key: "value", folded (>) and literal (|) blocks,
    inline lists [a, b], and nested one-level mappings (ignored, kept raw).
    Deliberately dependency-free so the script runs anywhere.
    """
    problems: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, ["no YAML frontmatter: file must start with '---'"]
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text, ["frontmatter opened with '---' but never closed"]

    data: dict = {}
    i = 1
    while i < end:
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if raw[:1] in (" ", "\t"):
            i += 1  # continuation of something we already consumed
            continue
        if ":" not in raw:
            problems.append(f"frontmatter line {i + 1} is not 'key: value': {raw.strip()!r}")
            i += 1
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        if value in (">", ">-", "|", "|-"):
            block: list[str] = []
            i += 1
            while i < end and (not lines[i].strip() or lines[i][:1] in (" ", "\t")):
                block.append(lines[i].strip())
                i += 1
            joiner = "\n" if value.startswith("|") else " "
            data[key] = joiner.join(b for b in block if b)
            continue
        if value.startswith("[") and value.endswith("]"):
            data[key] = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        else:
            data[key] = value.strip("'\"")
        i += 1
    return data, "\n".join(lines[end + 1:]), problems


def est_tokens(text: str) -> int:
    """Rough English estimate: ~1.3 tokens per whitespace word."""
    return int(len(text.split()) * 1.3)


def check_description(desc: str, rep: Report) -> None:
    where = "description"
    n = len(desc)
    if n < DESC_CHARS_MIN:
        rep.error(where, f"{n} chars — far too short to trigger reliably")
        return
    if n < DESC_CHARS_WEAK:
        rep.warn(where, f"{n} chars — thin. Add trigger phrasings and concrete nouns (target 400-900).")
    if n > DESC_CHARS_MAX:
        rep.warn(where, f"{n} chars — over {DESC_CHARS_MAX}; trim to the phrasings that earn their place.")
    low = desc.lower()
    if not any(c in low for c in TRIGGER_CUES):
        rep.warn(where, "no 'use this when/whenever' framing — Claude under-triggers without it")
    if not any(c in low for c in BOUNDARY_CUES):
        rep.warn(where, "no boundary clause — add 'NOT for X, use Y instead' to buy precision")
    if '"' not in desc and "'" not in desc:
        rep.warn(where, "no quoted user phrasings — quote 3 things a real person would type")
    words = len(desc.split())
    if words > DESC_WORDS_IDEAL * 1.6:
        rep.info(where, f"{words} words — long, but fine if every phrasing is doing work")


def check_body(body: str, name: str, rep: Report) -> None:
    lines = body.strip().splitlines()
    n = len(lines)
    rep.stats["body_lines"] = n
    rep.stats["body_tokens"] = est_tokens(body)
    if n > BODY_LINES_HARD:
        rep.error("SKILL.md", f"body is {n} lines — over the {BODY_LINES_HARD} hard ceiling. Move sections to references/.")
    elif n > BODY_LINES_IDEAL:
        rep.warn("SKILL.md", f"body is {n} lines — over the {BODY_LINES_IDEAL} ideal. Candidates for references/?")

    h1 = next((l for l in lines if l.startswith("# ")), None)
    if not h1:
        rep.warn("SKILL.md", "no H1 heading in the body")
    else:
        slug = re.sub(r"[^a-z0-9]+", "-", h1[2:].strip().lower()).strip("-")
        if name and slug != name:
            rep.warn("SKILL.md", f"H1 {h1[2:].strip()!r} does not match name {name!r} — rename touches both")

    mandates = len(MANDATE_RE.findall(body))
    if mandates > MANDATE_LIMIT:
        rep.warn("SKILL.md", f"{mandates} ALWAYS/NEVER/MUST mandates — uniform emphasis is no emphasis. Convert most to rules with reasons.")


def check_links(body: str, root: Path, rep: Report) -> set[str]:
    referenced: set[str] = set()
    for match in LINK_RE.finditer(body):
        rel = match.group(1).rstrip(".,);:")
        referenced.add(rel)
        if not (root / rel).exists():
            rep.error("SKILL.md", f"points at {rel} which does not exist")
    return referenced


def check_orphans(root: Path, referenced: set[str], rep: Report) -> None:
    refdir = root / "references"
    if not refdir.is_dir():
        return
    for f in sorted(refdir.rglob("*.md")):
        rel = f.relative_to(root).as_posix()
        if rel not in referenced and f.name not in {r.split("/")[-1] for r in referenced}:
            rep.warn(rel, "never pointed at from SKILL.md — an unreferenced file is never loaded")
        text = f.read_text(encoding="utf-8", errors="replace")
        if len(text.splitlines()) > REF_TOC_LINES and "## Contents" not in text:
            rep.warn(rel, f">{REF_TOC_LINES} lines without a '## Contents' list — add one so a partial read is useful")


def check_scripts(root: Path, rep: Report) -> None:
    sdir = root / "scripts"
    if not sdir.is_dir():
        return
    stdlib = getattr(sys, "stdlib_module_names", STDLIB_FALLBACK)
    local = {p.stem for p in sdir.rglob("*.py")}
    for f in sorted(sdir.rglob("*.py")):
        rel = f.relative_to(root).as_posix()
        src = f.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            rep.error(rel, f"syntax error line {exc.lineno}: {exc.msg}")
            continue
        if not src.startswith("#!"):
            rep.info(rel, "no shebang — add '#!/usr/bin/env python3' if it is meant to run directly")
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module.split(".")[0])
        thirdparty = sorted(m for m in imported if m and m not in stdlib and m not in local)
        if thirdparty:
            rep.info(rel, f"third-party imports: {', '.join(thirdparty)} — name them in the README with install lines")


def check_secrets(root: Path, rep: Report) -> None:
    skip_dirs = {".git", "__pycache__", "node_modules", "dist", ".venv"}
    for f in root.rglob("*"):
        if not f.is_file() or any(p in skip_dirs for p in f.parts):
            continue
        if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".zip", ".skill", ".woff2", ".ttf", ".xlsx", ".pptx", ".docx"}:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern, label in SECRET_RES:
            if pattern.search(text):
                rep.error(f.relative_to(root).as_posix(), f"looks like a {label} — never publish this")


def validate(path: Path) -> Report:
    rep = Report()
    root = path if path.is_dir() else path.parent
    skill_md = path if path.is_file() else root / "SKILL.md"

    if not skill_md.exists():
        rep.error(str(path), "no SKILL.md found")
        return rep

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    data, body, problems = parse_frontmatter(text)
    for p in problems:
        rep.error("frontmatter", p)

    name = str(data.get("name", "")).strip()
    if not name:
        rep.error("frontmatter", "missing required field: name")
    else:
        if not NAME_RE.match(name):
            rep.error("frontmatter", f"name {name!r} must be kebab-case: lowercase letters, digits, single hyphens")
        if len(name) > 64:
            rep.error("frontmatter", f"name is {len(name)} chars — keep it under 64")
        if path.is_dir() and root.name != name:
            rep.error("frontmatter", f"name {name!r} does not match directory {root.name!r} — installs key off both")
        if re.search(r"[-_](v)?\d+(\.\d+)*$", name):
            rep.warn("frontmatter", f"name {name!r} carries a version — version in the CHANGELOG, not the name")

    desc = str(data.get("description", "")).strip()
    if not desc:
        rep.error("frontmatter", "missing required field: description — this is the entire triggering mechanism")
    else:
        check_description(desc, rep)
        rep.stats["description_chars"] = len(desc)
        rep.stats["description_tokens"] = est_tokens(desc)

    unknown = set(data) - {"name", "description", "license", "compatibility", "argument-hint", "allowed-tools", "version", "metadata", "model"}
    if unknown:
        rep.info("frontmatter", f"non-standard fields (harmless, but ignored by most loaders): {', '.join(sorted(unknown))}")

    check_body(body, name, rep)
    referenced = check_links(body, root, rep)
    check_orphans(root, referenced, rep)
    check_scripts(root, rep)
    check_secrets(root, rep)

    if not (root / "README.md").exists() and not (root.parent.parent / "README.md").exists():
        rep.info("repo", "no README.md — required if anyone but you will use this")
    if not any((root / d).exists() for d in ("evals", "tests")) :
        rep.info("repo", "no evals/ — add 3 task prompts and a 20-query trigger set before publishing")

    return rep


def render(rep: Report, path: Path, as_json: bool, strict: bool) -> int:
    failed = rep.errors > 0 or (strict and rep.warnings > 0)
    if as_json:
        print(json.dumps({
            "path": str(path),
            "ok": not failed,
            "errors": rep.errors,
            "warnings": rep.warnings,
            "stats": rep.stats,
            "items": [{"level": l, "where": w, "message": m} for l, w, m in rep.items],
        }, indent=2))
        return 1 if failed else 0

    icon = {"ERROR": "✗", "WARN": "!", "INFO": "·"}
    print(f"\n  {path}\n")
    if not rep.items:
        print("  clean — nothing to report")
    for level in ("ERROR", "WARN", "INFO"):
        for lvl, where, msg in rep.items:
            if lvl == level:
                print(f"  {icon[lvl]} {lvl:<5} {where:<28} {msg}")

    s = rep.stats
    if s:
        print("\n  budget")
        if "description_tokens" in s:
            print(f"    level 1  description   {s.get('description_chars', 0):>5} chars  ~{s.get('description_tokens', 0):>5} tokens   (paid every conversation)")
        print(f"    level 2  SKILL.md body {s.get('body_lines', 0):>5} lines  ~{s.get('body_tokens', 0):>5} tokens   (paid on every fire)")

    verdict = "FAIL" if failed else ("PASS with warnings" if rep.warnings else "PASS")
    print(f"\n  {verdict}: {rep.errors} error(s), {rep.warnings} warning(s)\n")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a Claude Skill.")
    ap.add_argument("path", help="skill directory (or a SKILL.md file)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    path = Path(args.path).expanduser().resolve()
    if not path.exists():
        print(f"no such path: {path}", file=sys.stderr)
        return 2
    return render(validate(path), path, args.json, args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
