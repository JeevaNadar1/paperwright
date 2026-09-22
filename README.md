# Paperwright

A Claude Skill for the stage between agreeing a deal and getting paid for it.
Quotes get compared, terms get shaken on, and then somebody has to write the
document that decides what happens when it goes wrong.

Paperwright drafts what you issue and dismantles what you receive: SOWs, MSAs,
NDAs, contractor and consultancy agreements, offer letters, work orders, lease
heads of terms, MOUs, change orders, settlements, and breach or defect
rectification notices. Output is print-ready markdown, an A4 PDF, or a
clause-level redline.

It has an India layer — stamping, registration, GST, TDS, MSMED payment
timelines, and the Contract Act limits that quietly void clauses copied from US
templates.

## What it actually changes

Without a skill, a model writes a plausible-looking contract and misses the
things that cost money: no exclusions clause, acceptance with no deadline, an
uncapped indemnity sitting next to a capped liability clause, a cure period
longer than the termination notice. Paperwright supplies four deltas.

1. **Knowledge** — clause positions at three strengths, and Indian instrument
   rules the model will not otherwise apply.
2. **Procedure** — a fixed review order (money, exit, liability, scope,
   ownership, disputes, machinery) so nothing gets skipped because the price
   looked fine.
3. **Determinism** — placeholder, arithmetic and consistency linting by script
   rather than by reading carefully and hoping.
4. **Boundary** — it drafts and flags. It does not certify, and it refuses
   backdating and side letters drafted to contradict the main document.

## Install

**Chat surfaces (claude.ai, desktop, mobile)**
Download [`dist/paperwright.skill`](dist/paperwright.skill) and upload it under
Settings → Capabilities → Skills.

**Claude Code**

```bash
git clone https://github.com/JeevaNadar1/paperwright.git
```

Then add the clone as a plugin marketplace source, or copy
`skills/paperwright/` into your skills directory.

**Just reading it** — everything starts at
[`skills/paperwright/SKILL.md`](skills/paperwright/SKILL.md).

## Usage

Describe the situation in plain English. It picks the mode.

```
draft an NDA for a contractor we're bringing on for the site
turn the accepted quote into a SOW with exclusions and payment milestones
vendor sent their MSA — tell me what I'm walking into before I sign
they marked up our agreement, show me what actually changed and which bits matter
the builder still hasn't fixed the defects, I want to send something formal
```

| Mode | Fires when | Output |
|---|---|---|
| draft | A document is wanted and terms exist | Full document, placeholders bolded |
| review | A document is pasted or attached | Severity-graded findings, then a negotiation note |
| redline | Two versions exist, or a review is accepted | Clause-level diff plus a cover note |
| notice | Defects, non-payment, breach | Notice under the contract's own machinery |

## Scripts

All are standalone. Python 3.9+.

```bash
# lint a draft before it leaves the room
python3 skills/paperwright/scripts/check_doc.py draft.md --type sow

# pull the commercial terms out of a contract
python3 skills/paperwright/scripts/check_doc.py contract.md --terms

# clause-level redline between two versions
python3 skills/paperwright/scripts/redline.py theirs.md ours.md --out redline.md

# print-ready A4 PDF
python3 skills/paperwright/scripts/build_pdf.py draft.md --type contract --out draft.pdf
```

`check_doc.py` and `redline.py` are stdlib only. `build_pdf.py` needs reportlab:

```bash
pip install reportlab
```

`check_doc.py` catches unfilled placeholders, a mandatory clause that was never
written, a defined term used but never defined, a party label that drifts,
milestone percentages that do not sum to 100, a cure period longer than the
termination notice, schedules referenced but not attached, and cross-references
to clauses that do not exist.

`build_pdf.py` type presets pick the typeface and body size: `contract`
(sans-serif, 14pt), `report` and `memo` (serif, 12pt), `technical` (sans
headings, serif body), `print` (sans, 12pt). The palette is Modern Minimalist —
`#5DADE2` headings, `#708090` secondary text and rules, `#D3D3D3` dividers —
with a dark slate body colour so a printed contract stays legible. Override
with `--accent` and `--body-colour`.

## Layout

```
skills/paperwright/
  SKILL.md                      router, 166 lines
  references/
    doc-types.md                13 instruments, mandatory clause sets, what gets left out
    clause-library.md           27 clauses at Firm / Market / Exposed, with language
    risk-flags.md               the review catalogue, severity-graded
    india-notes.md              stamping, registration, GST, TDS, MSMED, Contract Act limits
  scripts/
    check_doc.py                contract linter
    redline.py                  clause-level diff
    build_pdf.py                A4 PDF renderer
  assets/templates/
    sow.md  nda-mutual.md  offer-letter.md  contractor-agreement.md  defect-notice.md
  evals/
    trigger.json                20 queries, 10 should-fire and 10 near-miss
    evals.json                  4 task evals with assertions
```

## Boundaries

Paperwright yields to its neighbours, and says so in its own description so the
router does not have to guess.

1. Comparing prices across competing bids → `quote-forensics`.
2. Persuasive or sales copy → `copywright`.
3. Branded proposal or pitch decks → `fluid-ai-proposal`.
4. Reconciliation, GST returns and month-end close → `company-finance-buddy`.

## Not legal advice

This skill drafts documents and flags risks. It does not certify that anything
is valid, enforceable or compliant, and it is not a substitute for a lawyer.
Rates, thresholds and stamp duty schedules change; the India layer flags what to
verify rather than asserting current figures. Have counsel review anything
executed at material value.

## Licence

MIT. See [LICENSE](LICENSE).
