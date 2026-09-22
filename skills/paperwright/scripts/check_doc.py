#!/usr/bin/env python3
"""Lint a contract draft before it leaves the room.

Usage:
    python3 check_doc.py draft.md --type sow
    python3 check_doc.py contract.md --terms
    python3 check_doc.py draft.md --type msa --json

Catches what survives a careful read: unfilled placeholders, a mandatory clause
that was never written, a defined term used but never defined, a party name that
drifts, milestone percentages that do not sum to 100, a cure period longer than
the termination notice, and schedules referenced but not attached.

Exit codes: 0 clean, 1 findings, 2 bad invocation.
Stdlib only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# --- clause sets per instrument -------------------------------------------
# Each entry: label -> tuple of lowercase keywords, any one of which counts as
# the clause being present. Heuristic by design: a false positive costs a
# glance, a false negative costs a clause.
CLAUSE_SETS = {
    "sow": {
        "scope of services": ("scope of services", "scope of work", "services to be"),
        "exclusions": ("exclusion", "out of scope", "not included"),
        "deliverables": ("deliverable",),
        "acceptance": ("acceptance", "accepted",),
        "client dependencies": ("dependenc", "client shall provide", "customer shall provide"),
        "fees": ("fee", "charges", "consideration"),
        "payment terms": ("payment term", "payable within", "invoice"),
        "change order": ("change order", "change request", "variation"),
        "term and termination": ("terminat",),
        "intellectual property": ("intellectual property", "ownership of",),
        "signature block": ("signature", "signed for and on behalf", "for and on behalf"),
    },
    "msa": {
        "definitions": ("definition", "in this agreement",),
        "order of precedence": ("precedence", "conflict between", "inconsistency"),
        "fees": ("fee", "charges"),
        "taxes": ("tax", "gst", "withhold"),
        "confidentiality": ("confidential",),
        "intellectual property": ("intellectual property",),
        "warranties": ("warrant",),
        "limitation of liability": ("limitation of liability", "aggregate liability", "liability of"),
        "indemnity": ("indemnif", "indemnity"),
        "termination": ("terminat",),
        "survival": ("surviv",),
        "force majeure": ("force majeure",),
        "assignment": ("assign",),
        "notices": ("notice",),
        "governing law": ("governing law", "governed by the laws"),
        "dispute resolution": ("arbitrat", "dispute resolution", "jurisdiction"),
        "entire agreement": ("entire agreement",),
    },
    "nda": {
        "definition of confidential information": ("confidential information means", "definition of confidential"),
        "exclusions": ("shall not include", "exclusion", "already in the public"),
        "permitted purpose": ("purpose",),
        "permitted recipients": ("representative", "recipient", "employees and advis"),
        "compelled disclosure": ("required by law", "compelled", "court order"),
        "term": ("term of this",),
        "survival": ("surviv",),
        "return or destruction": ("return or destroy", "destruction", "return all"),
        "no licence": ("no licen", "no right", "not grant"),
        "remedies": ("injunct", "equitable relief", "remed"),
        "governing law": ("governing law", "governed by"),
    },
    "contractor": {
        "not employment": ("not constitute employment", "independent contractor", "no employment relationship"),
        "services": ("services",),
        "fees": ("fee", "rate"),
        "taxes": ("tax", "own account", "statutory"),
        "term and termination": ("terminat",),
        "ip assignment": ("assign", "intellectual property"),
        "confidentiality": ("confidential",),
        "no authority to bind": ("no authority", "not bind", "shall not represent"),
        "non-solicitation": ("solicit",),
        "governing law": ("governing law", "governed by"),
    },
    "offer": {
        "position": ("position", "designation", "role of"),
        "start date": ("date of joining", "start date", "commencement"),
        "compensation": ("compensation", "salary", "remuneration"),
        "variable pay basis": ("variable", "bonus", "incentive"),
        "probation": ("probation",),
        "notice period": ("notice period", "notice of"),
        "conditions of offer": ("subject to", "contingent upon", "background"),
        "confidentiality": ("confidential",),
        "ip assignment": ("intellectual property", "assign"),
        "governing law": ("governing law", "governed by", "jurisdiction"),
        "acceptance": ("accept", "sign and return"),
    },
    "lease": {
        "premises": ("premises", "demised"),
        "area basis": ("carpet", "built-up", "built up", "super built"),
        "term": ("term of", "period of"),
        "lock-in": ("lock-in", "lock in"),
        "rent": ("rent", "licence fee", "license fee"),
        "escalation": ("escalat", "increase of", "% per annum"),
        "security deposit": ("security deposit", "deposit"),
        "permitted use": ("permitted use", "shall be used for"),
        "maintenance": ("maintenance", "repair"),
        "taxes": ("property tax", "gst", "tax"),
        "termination": ("terminat",),
        "governing law": ("governing law", "jurisdiction"),
    },
    "notice": {
        "contract reference": ("agreement dated", "contract dated", "work order dated"),
        "clause relied on": ("clause", "in terms of"),
        "facts": ("on or about", "as on", "dated"),
        "defect schedule": ("schedule", "annexure", "list of"),
        "cure period": ("within", "cure", "rectif"),
        "consequence": ("failing which", "shall be entitled", "consequence"),
        "reservation of rights": ("reserv", "without prejudice"),
        "delivery": ("by email", "registered post", "courier", "speed post"),
    },
    "mou": {
        "parties": ("between",),
        "objective": ("objective", "purpose", "intent"),
        "contributions": ("shall endeavour", "intends to", "contribution"),
        "non-binding clause": ("non-binding", "not binding", "no legally binding"),
        "binding clauses named": ("binding", "shall be binding"),
        "confidentiality": ("confidential",),
        "costs": ("own costs", "bear its own"),
        "lapse date": ("expire", "lapse", "valid until"),
    },
    "amendment": {
        "original agreement reference": ("agreement dated", "original agreement"),
        "the change": ("deleted and replaced", "amended to read", "substituted"),
        "price impact": ("revised", "additional", "amount"),
        "time impact": ("date", "extend", "revised timeline"),
        "no other change": ("remain unchanged", "full force and effect"),
        "effective date": ("effective from", "effective date", "with effect from"),
    },
    "settlement": {
        "recitals": ("whereas",),
        "settlement amount": ("settlement amount", "full and final", "sum of"),
        "release": ("release", "discharge"),
        "carve-outs": ("except", "save for", "other than"),
        "no admission": ("no admission", "without admitting"),
        "confidentiality": ("confidential",),
        "withdrawal of proceedings": ("withdraw", "proceedings", "claim"),
        "governing law": ("governing law", "jurisdiction"),
    },
}

RISKY = [
    (r"\bbest efforts?\b", "\"best efforts\" is an uncapped standard; prefer \"reasonable endeavours\""),
    (r"\bsole discretion\b", "one-sided discretion — check whether it is symmetrical"),
    (r"\bincluding but not limited to\b", "open-ended in a scope clause; fine in exclusions, dangerous in obligations"),
    (r"\bfrom time to time\b", "undefined variability — tie to a written notice or a schedule"),
    (r"\bas may be required\b", "obligation without a boundary"),
    (r"\bmutually agreed\b", "an agreement to agree is generally unenforceable; state a mechanism"),
    (r"\bto the satisfaction of\b", "subjective acceptance standard with no objective test"),
    (r"\bunlimited\b", "check this is not attached to liability or indemnity"),
    (r"\bin perpetuity\b", "perpetual obligations are often unadministrable; scope by subject matter"),
    (r"\bTBD\b|\bTBC\b|\bXXX\b|\bLorem\b", "unfinished text left in the draft"),
    (r"\bshall use its best endeavou?rs to ensure\b", "an absolute obligation wearing a soft label"),
    (r"\berror[- ]free\b", "not achievable; do not warrant it"),
]

PLACEHOLDER_RE = re.compile(r"\*\*\[[^\]]+\]\*\*|\[[A-Z][^\]]{2,}\]|\{\{[^}]+\}\}|<[a-z_]+>")
DEFINED_RE = re.compile(r"[\(\"“']\s*(?:the\s+)?[\"“']?([A-Z][A-Za-z ]{2,40}?)[\"”']?\s*[\)]|"
                        r"[\"“]([A-Z][A-Za-z ]{2,40}?)[\"”]\s+(?:means|shall mean)")
CLAUSE_HEAD_RE = re.compile(r"^\s*(?:#{1,6}\s*)?(\d+(?:\.\d+)*)[.)]?\s+(\S.*)$")
XREF_RE = re.compile(r"\b[Cc]lause\s+(\d+(?:\.\d+)*)")
SCHEDULE_REF_RE = re.compile(r"\b(?:Schedule|Annexure|Exhibit|Appendix)\s+([A-Z0-9]+)\b")
MONEY_RE = re.compile(r"(?:₹|\bRs\.?|\bINR\b|\$|\bUSD\b|€|£)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:lakh|lakhs|crore|crores|million|mn|bn))?", re.I)
PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s?%")
DAYS_RE = re.compile(r"(\d+)\s+(business days|days|day|months|month|years|year)", re.I)


class Finding:
    def __init__(self, level: str, where: str, message: str) -> None:
        self.level, self.where, self.message = level, where, message

    def as_dict(self) -> dict:
        return {"level": self.level, "where": self.where, "message": self.message}



def _heading_mode(text: str) -> bool:
    """True when the document numbers its clauses as markdown headings.

    In that case list items like "1." inside a clause are not clause heads, and
    treating them as such silently merges or overwrites real clauses.
    """
    return bool(re.search(r"^#{1,6}\s*\d", text, re.M))


def split_clauses(text: str) -> list:
    """Return [(number, heading, body)] for numbered clauses."""
    out, current = [], None
    headings_only = _heading_mode(text)
    for line in text.splitlines():
        m = CLAUSE_HEAD_RE.match(line)
        if headings_only and not line.lstrip().startswith("#"):
            m = None
        if m and len(m.group(1)) <= 9:
            if current:
                out.append(current)
            current = [m.group(1), m.group(2).strip(), []]
        elif current:
            current[2].append(line)
    if current:
        out.append(current)
    return [(n, h, "\n".join(b)) for n, h, b in out]


def check_placeholders(text: str, f: list) -> None:
    hits = sorted({m.group(0) for m in PLACEHOLDER_RE.finditer(text)})
    for h in hits:
        f.append(Finding("BLOCKING", "placeholder", f"unfilled: {h}"))


def check_clause_set(text: str, doc_type: str, f: list) -> None:
    spec = CLAUSE_SETS.get(doc_type)
    if not spec:
        return
    low = text.lower()
    for label, cues in spec.items():
        if not any(c in low for c in cues):
            f.append(Finding("MATERIAL", "clause set", f"no clause found for: {label}"))


def check_defined_terms(text: str, f: list) -> None:
    defined = set()
    for m in DEFINED_RE.finditer(text):
        term = (m.group(1) or m.group(2) or "").strip()
        if term:
            defined.add(term)
    if not defined:
        return
    # Capitalised multi-word phrases used in the body but never defined.
    used = set(re.findall(r"\b(?:[A-Z][a-z]+ ){1,3}(?:Agreement|Services|Deliverables|Fees|Party|Parties|Information|Period|Date|Works|Premises)\b", text))
    stop = ("this ", "the ", "these ", "such ", "any ", "each ", "its ", "our ", "master ", "services agreement")
    for term in sorted(used):
        t = term.strip()
        if t.lower().startswith(stop) or t.lower() in stop:
            continue
        if text.count(t) < 2:
            continue
        if t not in defined and not any(t in d or d in t for d in defined):
            f.append(Finding("HOUSEKEEPING", "definitions", f"capitalised term used but not defined: {t}"))


def check_xrefs(text: str, clauses: list, f: list) -> None:
    numbers = {n for n, _, _ in clauses}
    if not numbers:
        return
    for m in XREF_RE.finditer(text):
        ref = m.group(1)
        if ref not in numbers and not any(n.startswith(ref + ".") for n in numbers):
            f.append(Finding("HOUSEKEEPING", "cross-reference", f"clause {ref} is referenced but does not exist"))


def check_schedules(text: str, f: list) -> None:
    refs = {m.group(0) for m in SCHEDULE_REF_RE.finditer(text)}
    for ref in sorted(refs):
        # An attached schedule appears as a heading somewhere in the document.
        if not re.search(r"^\s*(?:#{1,6}\s*)?" + re.escape(ref) + r"\b", text, re.M):
            f.append(Finding("MATERIAL", "schedules", f"{ref} is referenced but no heading for it exists"))


def check_arithmetic(text: str, f: list) -> None:
    pcts = [float(p) for p in PCT_RE.findall(text)]
    payment_block = re.search(r"(?is)(payment|milestone|invoic)(.{0,1200})", text)
    if payment_block:
        block = payment_block.group(2)
        block_pcts = []
        for m in PCT_RE.finditer(block):
            window = block[max(0, m.start() - 45):m.end() + 45].lower()
            # Interest and escalation rates are not milestone shares.
            if any(w in window for w in ("interest", "per month", "per annum", "escalat", "overdue", "p.a.")):
                continue
            block_pcts.append(float(m.group(1)))
        if len(block_pcts) >= 2:
            total = sum(block_pcts)
            if 90 <= total <= 110 and abs(total - 100) > 0.01:
                f.append(Finding("BLOCKING", "arithmetic",
                                 f"milestone percentages sum to {total:g}%, not 100%"))
    cure = re.search(r"(?is)cure.{0,120}?(\d+)\s+days", text) or re.search(r"(?is)(\d+)\s+days.{0,60}?to cure", text)
    notice = re.search(r"(?is)terminat.{0,200}?(\d+)\s+days", text)
    if cure and notice:
        c, n = int(cure.group(1)), int(notice.group(1))
        if c >= n:
            f.append(Finding("MATERIAL", "arithmetic",
                             f"cure period ({c}d) is not shorter than the termination notice ({n}d) — cure cannot complete before termination bites"))
    if not pcts and not MONEY_RE.search(text):
        f.append(Finding("HOUSEKEEPING", "arithmetic", "no monetary amount found anywhere in the document"))


def check_party_drift(text: str, f: list) -> None:
    labels = re.findall(r"[\(\"“']\s*(?:the\s+)?[\"“']?(Client|Customer|Supplier|Vendor|Contractor|Consultant|Company|Employer|Licensor|Licensee|Lessor|Lessee|Landlord|Tenant|Disclosing Party|Receiving Party)[\"”']?\s*[\)]", text)
    declared = set(labels)
    if not declared:
        return
    family = {"Client", "Customer"}, {"Supplier", "Vendor", "Contractor", "Consultant"}, {"Lessor", "Landlord"}, {"Lessee", "Tenant"}
    for group in family:
        used = {g for g in group if re.search(r"\bthe " + g + r"\b", text)}
        if len(used & set(declared)) and len(used) > 1:
            f.append(Finding("MATERIAL", "parties",
                             f"party label drifts between {', '.join(sorted(used))} — use one throughout"))


def check_risky(text: str, f: list) -> None:
    for pattern, note in RISKY:
        if re.search(pattern, text, re.I):
            f.append(Finding("HOUSEKEEPING", "language", note))


def extract_terms(text: str) -> dict:
    return {
        "amounts": sorted({m.group(0).strip() for m in MONEY_RE.finditer(text)})[:25],
        "percentages": sorted({p + "%" for p in PCT_RE.findall(text)})[:25],
        "periods": sorted({f"{n} {u.lower()}" for n, u in DAYS_RE.findall(text)})[:25],
        "dates": sorted(set(re.findall(r"\b\d{1,2}[ /-](?:\d{1,2}|[A-Z][a-z]{2,8})[ /-]\d{2,4}\b", text)))[:25],
        "governing_law": (re.search(r"(?i)governed by the laws? of ([A-Za-z ,]+)", text) or [None, None])[1],
        "seat": (re.search(r"(?i)seat of (?:the )?arbitration shall be ([A-Za-z ,]+)", text) or [None, None])[1],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint a contract draft.")
    ap.add_argument("path")
    ap.add_argument("--type", choices=sorted(CLAUSE_SETS), help="instrument type, for the mandatory clause check")
    ap.add_argument("--terms", action="store_true", help="extract the commercial terms instead of linting")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    p = Path(args.path).expanduser()
    if not p.exists():
        print(f"no such file: {p}", file=sys.stderr)
        return 2
    text = p.read_text(encoding="utf-8", errors="replace")

    if args.terms:
        terms = extract_terms(text.replace("**", ""))
        if args.json:
            print(json.dumps(terms, indent=2))
        else:
            print(f"\n  commercial terms — {p.name}\n")
            for k, v in terms.items():
                if isinstance(v, list):
                    print(f"  {k:<14} {', '.join(v) if v else '—'}")
                else:
                    print(f"  {k:<14} {v or '—'}")
            print()
        return 0

    findings: list = []
    clauses = split_clauses(text)
    check_placeholders(text, findings)
    if args.type:
        check_clause_set(text, args.type, findings)
    check_defined_terms(text, findings)
    check_xrefs(text, clauses, findings)
    check_schedules(text, findings)
    check_arithmetic(text, findings)
    check_party_drift(text, findings)
    check_risky(text, findings)

    if args.json:
        print(json.dumps({
            "path": str(p),
            "clauses": len(clauses),
            "findings": [f.as_dict() for f in findings],
        }, indent=2))
        return 1 if findings else 0

    icon = {"BLOCKING": "x", "MATERIAL": "!", "HOUSEKEEPING": "."}
    print(f"\n  {p.name} — {len(clauses)} numbered clause(s)\n")
    if not findings:
        print("  clean — nothing to report\n")
        return 0
    for level in ("BLOCKING", "MATERIAL", "HOUSEKEEPING"):
        for f in findings:
            if f.level == level:
                print(f"  {icon[level]} {level:<13} {f.where:<16} {f.message}")
    counts = {lv: sum(1 for f in findings if f.level == lv) for lv in icon}
    print(f"\n  {counts['BLOCKING']} blocking, {counts['MATERIAL']} material, "
          f"{counts['HOUSEKEEPING']} housekeeping\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
