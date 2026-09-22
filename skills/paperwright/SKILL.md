---
name: paperwright
description: >
  Draft, review and redline the binding paper in a commercial deal — SOWs, MSAs,
  NDAs, contractor and consultancy agreements, offer letters, work orders, lease
  heads of terms, MOUs, change orders, and breach or defect rectification notices
  — as print-ready markdown, A4 PDF or a clause-level redline. Use this whenever
  someone wants to write, check, tighten or negotiate a contract or formal
  business document, including "draft an NDA for a contractor", "turn this quote
  into a SOW", "review this MSA before I sign", "what's wrong with their payment
  terms", "send the builder a rectification notice", or "make this offer letter
  tighter". Also use it when commercial terms are already agreed and now need
  papering, or when a vendor's agreement has landed and the person is uneasy
  about it, even if no document type is named. NOT for comparing prices across
  bids (use quote-forensics), persuasive pitch copy (use copywright), or branded
  proposal decks (use fluid-ai-proposal).
license: MIT
argument-hint: "[draft|review|redline|notice]"
---

# Paperwright

The stage between agreeing a deal and getting paid for it. Quotes get compared,
terms get shaken on, and then somebody has to write the document that decides
what happens when it goes wrong. This does that, in both directions: drafting
what you issue, and dismantling what you receive.

Delta: **knowledge** (clause positions, Indian instrument rules), **procedure**
(a fixed review order so nothing gets skipped because the price looked fine),
**determinism** (placeholder, term-consistency and completeness linting by
script), and **boundary** (it drafts and flags; it does not certify).

## Gate — three questions before a word gets written

1. **Which side are you on?** Issuing, or receiving. Every clause position
   inverts. If it is unclear, ask; guessing wrong reverses the whole document.
2. **Is the commercial deal actually settled?** Scope, price, timeline, payment
   trigger. If two of those four are open, draft a heads-of-terms or an MOU
   instead and say why — papering an unsettled deal manufactures a dispute.
3. **Does this instrument bind or merely record?** An MOU, a letter of intent
   and a rate card are not contracts unless drafted to be. Say which one is
   being produced in the first line of the output, so nobody discovers it later.

## Modes

| Mode | Fires when | Output |
|---|---|---|
| **draft** (default) | A document is wanted and terms exist | Full document, placeholders bolded, no clause left as a stub |
| **review** | A document is pasted or attached | Severity-graded findings, then the three changes worth fighting for |
| **redline** | Two versions exist, or a review is accepted | Clause-level diff plus a cover note for the counterparty |
| **notice** | Something has gone wrong: defects, non-payment, breach | Notice under the contract's own machinery, with the cure period and the consequence |

Modes chain. A review that finds real problems should offer the redline; a
redline that gets accepted should offer the clean execution copy.

## Pipeline

```
SIDE → INSTRUMENT → TERM SHEET → CLAUSE SET → DRAFT → LINT → OUTPUT
```

1. **Instrument.** Pick the document type and its mandatory clause set from
   `references/doc-types.md`. Picking the wrong instrument is the most expensive
   error available here — an NDA where a services agreement was needed leaves the
   work itself ungoverned.
2. **Term sheet.** Restate the commercial terms in a short table *before*
   drafting, and show it. Everything the document later says has to trace back
   to a row in it. Unknown rows become bolded placeholders, never invented
   numbers.
3. **Clause set.** Assemble from `references/clause-library.md`, choosing a
   position per clause on the strength dial below.
4. **Draft.** Full prose, numbered clauses, defined terms capitalised and used
   consistently from first definition.
5. **Lint.** Run `scripts/check_doc.py` before showing anything. It catches the
   errors that survive a careful read: a party name that drifts halfway through,
   a defined term used but never defined, an unfilled placeholder, a cure period
   that outlasts the termination notice.
6. **Output.** Markdown by default. PDF via `scripts/build_pdf.py` when it is
   going to a counterparty. `.docx` when they will want to redline it back.

## The strength dial

Every negotiable clause gets drafted at one of three positions. State which one
you used in a one-line note under the document, so the person knows what they
are holding.

| Position | Meaning | Use when |
|---|---|---|
| **Firm** | Favours the issuer, above market | You have leverage, or the downside is genuinely asymmetric |
| **Market** | What a competent counterparty signs without argument | Default. Anything else needs a reason |
| **Exposed** | Concedes the point | Only as a traded concession, and only if named as one |

Never stack Firm across every clause. A uniformly aggressive document signals
inexperience, invites a full markup, and costs more time than the concessions
would have. Pick the three clauses that carry the real risk in this deal, take
Firm on those, sit at Market everywhere else.

## Review order

Always in this order, because reading a contract front to back hides the traps
in the boring middle. The catalogue with severities and fixes:
`references/risk-flags.md`.

1. **Money** — amount, trigger, timing, currency, taxes, interest on late
   payment, retention or holdback.
2. **Exit** — term, renewal, termination for convenience and for cause, notice
   period, what survives, what gets paid on exit.
3. **Liability** — cap, exclusions, indemnities, insurance. Check the cap
   against the contract value, not in isolation.
4. **Scope** — deliverables, acceptance criteria, change-order mechanics, and
   what is expressly excluded.
5. **Ownership** — IP assignment versus licence, background versus foreground,
   data and confidentiality.
6. **Disputes** — governing law, jurisdiction or arbitration, seat, and whether
   the clause is symmetrical.
7. **Machinery** — definitions, notices, assignment, force majeure, severability.

A finding is only worth raising if you can state the loss it causes. "Clause 9
is one-sided" is noise. "Clause 9 lets them terminate on 7 days while you owe
90, so a cancelled project still bills you a quarter" is a finding.

## Placeholders and numbers

Dynamic inputs appear as bolded square brackets: **[Client Legal Name]**,
**[Contract Value: ₹XX,XX,XXX]**, **[Payment Terms: 30 days from invoice]**.
Never substitute a plausible number for a missing one, and never leave a clause
half-written with a note to finish it later — an unfinished clause in a signed
document is worse than an absent one, because it implies agreement on a term
nobody settled.

## India layer

Indian instruments carry stamping, registration, withholding and statutory
payment rules that change whether a document is admissible, not merely whether
it is good. Load `references/india-notes.md` whenever the parties, the site or
the governing law are Indian. It covers stamp duty by instrument, registration
thresholds for leases, GST treatment of contract value, TDS sections by payment
type, MSMED payment timelines, and the Contract Act limits that void otherwise
standard clauses. Rates and thresholds move: it flags what to verify rather than
asserting current figures.

## Output formats

| Need | Command |
|---|---|
| Lint a draft before showing it | `python3 scripts/check_doc.py draft.md --type sow` |
| Extract the commercial terms | `python3 scripts/check_doc.py contract.md --terms` |
| Diff two versions | `python3 scripts/redline.py theirs.md ours.md --out redline.md` |
| Print-ready A4 PDF | `python3 scripts/build_pdf.py draft.md --type contract --out draft.pdf` |

Starting points to copy rather than retype: `assets/templates/sow.md`,
`assets/templates/nda-mutual.md`, `assets/templates/offer-letter.md`,
`assets/templates/contractor-agreement.md`,
`assets/templates/defect-notice.md`.

## House rules

1. **Draft and flag; do not certify.** Say what a clause does and what it costs.
   Do not say a document is legally valid, enforceable, or compliant. For
   anything executed at material value, say once that counsel should review it,
   and then get on with the work — repeating the caveat in every section is
   padding, not caution.
2. **No invented facts.** Missing party details, registration numbers, dates and
   amounts stay as placeholders.
3. **Refuse the traps.** Do not draft clauses whose purpose is to mislead a
   counterparty about what they are signing: backdating, terms contradicted by a
   side letter, or fee structures buried under a defined term that means the
   opposite of its plain reading. Decline and say which clause and why.
4. **One instrument per document.** Employment terms do not belong inside a
   services agreement, and a settlement does not belong inside an amendment.
5. **Symmetry test.** Before shipping, read every material clause as the other
   side. If a clause would be unacceptable read from their chair, it will come
   back marked up — price that delay in now or soften it now.

## Reference index

Read on demand, not all at once.

1. `references/doc-types.md` — each instrument, its mandatory clause set, what
   people forget, and when to use a different one.
2. `references/clause-library.md` — negotiable clauses at Firm, Market and
   Exposed, with drafting language.
3. `references/risk-flags.md` — the review catalogue, severity-graded, with the
   loss each defect causes and the fix.
4. `references/india-notes.md` — stamping, registration, GST, TDS, MSMED, and
   the Contract Act limits on standard clauses.
