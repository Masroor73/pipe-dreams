# Proposal: Making the agent more genuinely autonomous

Status: **PROPOSAL, needs team approval.** Nothing here changes engine logic. Raised 2026-10-03 on `feat/integration`.

## Constraints (unchanged)

Frozen and out of scope (`DECISIONS.md` §8–13, `EXPERIMENT_PROTOCOL.md`):
- the V1 policy;
- the candidate set C1–C4;
- the recency grid (`none`, `hl10`);
- the three validation origins;
- the revision gate and its bootstrap SE rule;
- final-test discipline.

Every idea below adds decisions the agent makes and logs *within* those rules. None adds a candidate, re-tunes a threshold, or looks at the 2023–2025 result before freeze. No LLM decides anything (AGENTS.md rule 4).

"Autonomous" here means three things:
1. The agent picks its next step from evidence it computed itself.
2. It records *why* in `agent_log.jsonl`.
3. A judge can see that reason in the UI without anyone narrating it.

## Ideas, ranked

| # | Idea | What the agent decides itself | Judge-visible evidence | Owner | Cost (h) | Protocol risk |
|---|---|---|---|---|---|---|
| 1 | **Data-derived DIAGNOSE** | It computes V1's weaknesses on validation only, for example the capture shortfall by era, the share of capacity used by long segments, and how much of the score rests on stale breaks. It logs each diagnosis with the number behind it, and the order to test C1–C4 *before* any candidate runs. | Audit replay: the DIAGNOSE step shows 2–4 numbered findings, each tied to a candidate ("long segments use 41% of the 5% budget → C3 per-metre is relevant"). | Engine (diagnostics in `details`), UI (render `details.diagnoses`) | 3–4 | **Low.** Diagnosis is descriptive and uses validation data only. All four candidates are still tested; only the order and the stated rationale change. It must not skip candidates. |
| 2 | **Per-candidate rankings in the log** | Nothing new is decided, but the agent records the Top-N it *would* plan under each candidate before the gate rules on it. | The replay list changes at every TEST step, not only at PLAN_V2. This closes the gap noted in the motion spec. | Engine (artifact), API (contract field or a small `candidate_rankings.csv`), UI (cinema already FLIP-animates list changes) | 3 engine + 1 API + 1 UI | **Low.** These are rankings at the final-plan cutoff that the engine already computes. They must not show final-test capture per candidate (that would invite post-hoc selection). |
| 3 | **"Refused to change" narrative when V2 = V1** | It keeps V1 and states which gate condition each candidate failed and by how much. | Overview and Audit show "No candidate passed. C2 won 1/3 origins (needs 2) …" as a first-class outcome, not an empty state. | UI (data already exists: `v2_equals_v1`, per-candidate `origin_wins`, `difference`, `required_delta`, `reason`) | 1–2 | **None.** It only displays logged gate results. |
| 4 | **Autonomous escalation routing** | It applies the governance rules to every asset and logs the rule id, the inputs and the routed owner per escalation. It does not just emit the list. | Escalation groups show "Rule G2: T1 and LOW_VERIFY → Water Integrity Lead", and each row links to the logged rule firing. | Engine (governance log lines + `rule_id` column), API (pass-through), UI | 3 | **Low,** provided VERIFY/ESCALATE stay labelled as governance rules, not validated predictions (DECISIONS §15). The rule definitions must be frozen in config before final. |
| 5 | **Consequence-weight re-plan** | Given a weight from the frozen grid, the agent re-plans and logs what entered or left the Top 25 and why (tier mix). | The Communities view reads a precomputed artifact with "the agent re-planned at w2: 4 entered (all T1), 4 left". | Engine (artifact per `consequence-sensitivity.md`), UI (built against synthetic data) | 3–5 engine | **Medium.** The formula and tiers are an open decision. It must be a display sensitivity on the frozen plan, never fed back into the gate or tuned against final-test outcomes. |
| 6 | **2026 YTD monitoring check** | After freeze, it compares relative lift of V2 against the same baselines on 2026 YTD. It then recommends "keep" or "re-run the audit at the next cycle", or flags drift when the direction flips. | A "Monitoring" card that says "Directional only: V2 still ahead of count-only on 2026 YTD (n events)". It never shows an absolute capture next to the 3-year figure. | Engine (confirmation rows already in `validation_results.csv`), UI | 2–3 | **Medium.** The protocol (§4) allows directional relative lift only. A drift flag may recommend a review, but must never trigger re-selection or tuning. |
| 7 | **`POST /api/scenarios/capacity`** | The agent re-plans at a user-chosen capacity (Top-N or length %) using the frozen policy, and reports what changes. | A judge drags capacity from 5% to 2%, and the plan and escalations update live with the agent's explanation. | Engine (pure planner function), API (new write route, contract change), UI | 6–8 | **Medium-high.** ARCHITECTURE §7–8 allows it only *after* the core demo is stable, and only if it reuses frozen logic without re-running the audit. It adds a request-time code path and new failure modes close to the deadline. |

## Recommended top 3 for the next ~12 hours

1. **#3 "Refused to change" narrative.** UI-only, uses data that already exists, zero protocol risk. It also protects the demo if the corrected run ends with V2 = V1. **Can be built now** (no new data).
2. **#1 Data-derived DIAGNOSE.** The cheapest engine change that makes the loop visibly reason before it acts. The UI only renders `details.diagnoses`.
3. **#2 Per-candidate rankings.** Makes the replay show the agent's choice changing the plan at every step, the strongest visual proof of autonomy.

Item #5 is already contract-ready on the API and UI side with synthetic data. It needs only the engine artifact once the formula is decided.

## Pitch line

Pipe Dreams' agent plans, diagnoses its own plan, tests a frozen set of revisions against a pre-registered gate, and only changes course when the evidence clears that bar. Every decision, including the decision not to change, is logged and replayable.

## Blocked on the engine teammate

- `details.diagnoses` on the DIAGNOSE event (#1).
- Per-candidate Top-N rankings (#2).
- Governance rule ids per escalation (#4).
- The consequence formula, tier bands and weight grid, plus the real `consequence_sensitivity` artifact (#5).
- A frozen confirmation-row format for 2026 YTD (#6).
