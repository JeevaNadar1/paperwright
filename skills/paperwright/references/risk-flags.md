# Risk flags

The review catalogue. Work the review order from SKILL.md, and grade every
finding, because a document with 40 undifferentiated comments gets ignored.

## Contents

1. Severity grades
2. Money traps
3. Exit traps
4. Liability traps
5. Scope traps
6. Ownership traps
7. Dispute traps
8. Machinery and drafting traps
9. Arithmetic and consistency checks
10. Output format for a review

---

## 1. Severity grades

| Grade | Definition | Action |
|---|---|---|
| **Blocking** | Could cost more than the contract is worth, or makes performance impossible | Do not sign until changed |
| **Material** | Real money or real risk, negotiable | Put it in the markup; trade it if refused |
| **Housekeeping** | Wrong, but cheap. Inconsistencies, stale cross-references, drafting slips | Fix in one batch, do not spend negotiating capital |

Lead the review with the Blocking list. If there are none, say so in the first
line — it is the most useful sentence in a review and the one most often buried.

---

## 2. Money traps

| Trap | The loss | The fix |
|---|---|---|
| Payment trigger is acceptance, acceptance has no deadline | Completed work bills nothing, indefinitely | Deemed acceptance after a fixed period |
| Payment clock starts at "receipt of undisputed invoice" | Any query resets the clock to zero | Disputes limited to the disputed line; the rest pays on time |
| Retention with no long-stop release date | Permanent discount equal to the retention | Outer date, unconditional |
| Rates inclusive of all taxes, present and future | Every rate change is your cost | Exclusive of indirect taxes, plus a change-in-law clause |
| Set-off right granted to the client only | They net any alleged claim against your invoice | Mutual, or limited to finally determined amounts |
| No late payment interest | Chasing is a favour, not a right | Interest plus a suspension right |
| Volume or SLA credits with no annual cap | A bad quarter erases the year's margin | Cap credits as a percentage of annual fees |
| Currency unstated on a cross-border contract | Exchange movement lands on whoever did not specify | State the currency and the conversion date basis |

## 3. Exit traps

| Trap | The loss | The fix |
|---|---|---|
| Asymmetric termination notice | They exit in 7 days, you are locked for 90 | Match the periods, or price the gap |
| Auto-renewal with a long notice window | A missed date renews the whole term | Calendar the notice date at signature; shorten the window |
| Lock-in with no corresponding service commitment | You are committed, they are not | Tie lock-in to an SLA or a minimum volume |
| Termination for convenience with no payment for work in progress | Committed costs and demobilisation land on you | Payment for work performed plus committed third-party costs |
| No survival list | Confidentiality and IP assignment arguably lapse | List surviving clauses expressly |
| Transition assistance obligation with no rate | Months of unpaid work after the revenue stops | State a day rate and a maximum duration |

## 4. Liability traps

| Trap | The loss | The fix |
|---|---|---|
| Uncapped indemnity alongside a capped liability clause | The cap is decorative | Make indemnities expressly subject to the cap, except fraud and personal injury |
| Cap set at fees paid, on a low-fee high-risk engagement | Cap is meaningless relative to downside | Raise the cap, buy insurance, or narrow the obligation |
| Consequential loss excluded but "loss of profit" left in scope | The largest realistic claim survives the exclusion | Name each excluded head of loss expressly |
| Indemnity for "any claim arising in connection with" the services | Covers claims caused by the client's own acts | Narrow to claims arising from your breach or your IP |
| Insurance requirement above what the business carries | Breach on day one | Check the certificate before signing, not after |
| Liability cap per claim rather than in aggregate | Multiple claims multiply the cap | Aggregate across the term |

## 5. Scope traps

| Trap | The loss | The fix |
|---|---|---|
| No exclusions list | Everything unstated is arguable | Itemised exclusions plus the catch-all sentence |
| "Including but not limited to" in the scope clause | Scope has no boundary | Delete, or move the phrase to the exclusions where it helps you |
| Undefined "minor changes absorbed at no cost" | Scope creep with a contractual basis | Define numerically or delete |
| Client dependencies with no consequence | Their delay becomes your delay | Day-for-day extension plus standby cost |
| Acceptance criteria stated as satisfaction | Subjective, unwinnable | Objective, testable criteria in a schedule |
| Assumptions not written down | Priced for one thing, delivering another | An assumption register in the SOW |
| Unlimited revision rounds | The last 10% consumes the margin | Name the number of rounds and the rate beyond |

## 6. Ownership traps

| Trap | The loss | The fix |
|---|---|---|
| IP assigns on creation, not on payment | You hand over the asset before being paid for it | Assignment conditional on full payment |
| Assignment includes background IP, tools, methodology | You cannot reuse your own toolkit on the next job | Carve out background IP in a schedule |
| No express licence back for generic know-how | Same problem, arriving later | Express carve-out for skills, know-how and reusable components |
| Third-party and open-source components not addressed | You warrant something you do not own | Disclose components and their licences in a schedule |
| Moral rights not waived where the jurisdiction permits | Attribution and integrity claims survive assignment | Express waiver where lawful |
| Data ownership conflated with IP ownership | Client data and your models get tangled | Separate clauses, separate definitions |

## 7. Dispute traps

| Trap | The loss | The fix |
|---|---|---|
| Venue stated, seat unstated | A dispute about where the dispute happens | State the seat expressly |
| Jurisdiction at the counterparty's location, far away | Cost of enforcement exceeds the claim | Neutral seat, or arbitration |
| Arbitration with a three-member panel on a small contract | Panel costs exceed the amount in dispute | Sole arbitrator below a stated threshold |
| Escalation step with no deadline | Indefinite delay before any remedy | Fixed escalation window, then arbitration |
| Governing law different from the seat, unintentionally | Two legal systems, one document | Align them unless there is a deliberate reason |

## 8. Machinery and drafting traps

| Trap | The loss | The fix |
|---|---|---|
| Notices clause requires a method nobody uses | A valid notice served invalidly does nothing | Permit email with a confirmation mechanism |
| Order of precedence unstated between MSA and SOW | Conflicts resolve unpredictably | State it, split by legal versus commercial terms |
| Defined term used but never defined | Ambiguity at the worst moment | `check_doc.py` catches these |
| Defined term defined twice, differently | Same, but harder to spot | Single definitions section |
| Cross-references to renumbered clauses | Clause 9.3 points at nothing | Lint before issue |
| Party name drifts between the recitals and the operative clauses | Argument about who is bound | Use the defined party label throughout |
| Signature block without name, title and date | Authority questions later | Full block, with a capacity line |
| Schedules referenced but not attached | The commercial core is missing | Attach or delete the reference |

## 9. Arithmetic and consistency checks

Run these on every document, incoming or outgoing.

1. Milestone amounts sum to the contract total.
2. Percentages in the payment schedule sum to 100.
3. Dates run in sequence: start before milestones before completion before defect liability expiry.
4. The cure period is shorter than the termination notice period, otherwise cure is impossible before termination bites.
5. Notice periods are compatible with the term: a 90-day notice on a 60-day engagement cannot be exercised.
6. The liability cap is stated in the same currency and basis as the fees.
7. Retention release dates fall after the defect liability period ends.
8. Every schedule referenced exists; every schedule attached is referenced.
9. Numbers in words and figures agree.
10. The escalation percentage and the escalation frequency are both stated.

## 10. Output format for a review

```
## Verdict
[One line: sign, sign after these changes, or do not sign — and the single reason.]

## Blocking — [n]
1. **Clause [x], [name].** [What it does.] [The loss, quantified where possible.]
   Ask: [the specific redraft.]

## Material — [n]
[Same shape, briefer.]

## Housekeeping — [n]
[One line each, batched.]

## Negotiation note
[Which two or three items to actually fight for, which to trade, and what to
offer in exchange.]
```

The negotiation note is the part that converts a review into a decision. A list
of defects without a view on which ones to spend capital on leaves the work
unfinished.
