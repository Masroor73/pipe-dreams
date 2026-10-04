// Plain-English glossary for judge-facing jargon. The single source for every
// tooltip and the glossary page. Wording must stay faithful to docs/DECISIONS.md,
// docs/EXPERIMENT_PROTOCOL.md and docs/ARCHITECTURE.md: no claims beyond them.

export type GlossaryId =
  | 'synthetic'
  | 'v1'
  | 'v2'
  | 'candidates'
  | 'hl10'
  | 'capture'
  | 'length_budget'
  | 'count_only'
  | 'organizer_cell'
  | 'revision_gate'
  | 'bootstrap_se'
  | 'reachable_share'
  | 'evidence_confidence'
  | 'consequence_tier'
  | 'priority'
  | 'recommended_action'
  | 'verify_escalate';

export interface GlossaryEntry {
  id: GlossaryId;
  term: string;
  /** One or two plain sentences. Shown in tooltips and on the glossary page. */
  short: string;
  /** Optional extra detail for the glossary page only. */
  more?: string;
  /** Doc section the wording comes from (for maintainers; shown on the glossary page). */
  source: string;
}

export const GLOSSARY: GlossaryEntry[] = [
  {
    id: 'synthetic',
    term: 'Synthetic / placeholder data',
    short:
      'Made-up data with the same shape as the real engine output, used to build and test the app. Numbers shown under the yellow banner are not real results.',
    source: 'API_CONTRACT.md: response envelope',
  },
  {
    id: 'v1',
    term: 'V1',
    short:
      'The declared starting plan: full break history, no recency decay, segments ranked per asset. It is deliberately not the best-tuned policy.',
    more: 'Known weakness: under a length budget, per-asset ranking lets long segments use up more of the inspection capacity.',
    source: 'DECISIONS.md §8; EXPERIMENT_PROTOCOL.md §7',
  },
  {
    id: 'v2',
    term: 'V2',
    short:
      'The plan after the agent tests the candidate revisions. It is the passing candidate with the highest pooled validation score; if none pass, V2 stays the same as V1.',
    source: 'DECISIONS.md §9',
  },
  {
    id: 'candidates',
    term: 'C1–C4 (candidate revisions)',
    short:
      'The four frozen changes the agent may try against V1. C1: only breaks from 2000 on. C2: full history with hl10 recency weighting. C3: rank per metre instead of per segment. C4: 2000-on history plus hl10.',
    more: 'No other candidates are added after the fact.',
    source: 'DECISIONS.md §9; EXPERIMENT_PROTOCOL.md §8',
  },
  {
    id: 'hl10',
    term: 'hl10',
    short:
      'Recency weighting with a 10-year half-life: a break 10 years old counts half as much as a recent one. The only alternative tested is no decay.',
    source: 'DECISIONS.md §10; EXPERIMENT_PROTOCOL.md §6',
  },
  {
    id: 'capture',
    term: 'Capture',
    short:
      'Of the assets that broke in the following years, the share that were inside the inspected part of the ranked list. Higher is better.',
    more: 'Asset capture counts pipe segments; event capture counts break events. The two are not interchangeable.',
    source: 'DECISIONS.md §12; EXPERIMENT_PROTOCOL.md §9',
  },
  {
    id: 'length_budget',
    term: 'Length budget',
    short:
      'How much of the network you can inspect, as a share of eligible pipe length: 1%, 2%, 5% or 10%. The plan fills the budget from the top of the ranking down.',
    source: 'EXPERIMENT_PROTOCOL.md §9',
  },
  {
    id: 'count_only',
    term: 'Count-only baseline',
    short:
      'A simple comparison that ranks the same pipe segments by how many breaks they have had. Pipe Dreams has to beat it to be useful.',
    source: 'EXPERIMENT_PROTOCOL.md §12',
  },
  {
    id: 'organizer_cell',
    term: 'Organizer cell baseline',
    short:
      'The organizers’ comparison, which ranks rounded-coordinate map cells rather than pipes. It is scored on break events captured, never on pipes captured.',
    source: 'EXPERIMENT_PROTOCOL.md §12',
  },
  {
    id: 'revision_gate',
    term: 'Revision gate',
    short:
      'The fixed rule a candidate must pass to replace V1: beat V1 on at least 2 of the 3 validation periods, and improve the pooled score by at least one bootstrap SE.',
    more: 'The score is mean capture across the 1, 2, 5 and 10% budgets. This is a practical decision rule, not a formal significance test.',
    source: 'DECISIONS.md §12; EXPERIMENT_PROTOCOL.md §11',
  },
  {
    id: 'bootstrap_se',
    term: 'SE / bootstrap SE',
    short:
      'Standard error: how much the score could wobble by chance. It is estimated by resampling 1 km × 1 km map blocks, because nearby breaks tend to cluster.',
    source: 'DECISIONS.md §13; EXPERIMENT_PROTOCOL.md §10',
  },
  {
    id: 'reachable_share',
    term: 'Reachable / matched share',
    short:
      'The share of recorded breaks that could be matched to a pipe in today’s public network. Older breaks match less often, because the present-day network does not include every historical pipe.',
    source: 'EXPERIMENT_PROTOCOL.md §2, §14; ARCHITECTURE.md §16',
  },
  {
    id: 'evidence_confidence',
    term: 'Evidence confidence',
    short:
      'HIGH, MEDIUM or LOW_VERIFY: how complete and stable the evidence behind a segment’s ranking is. It is not a failure probability.',
    more: 'Thresholds come from validation data only and are frozen before the final test.',
    source: 'DECISIONS.md §14; EXPERIMENT_PROTOCOL.md §13',
  },
  {
    id: 'consequence_tier',
    term: 'Consequence tier (T1, T2, …)',
    short:
      'A rough label for how serious a failure would be, based on pipe diameter and asset class. It describes impact, not likelihood. The tier bands are still a prototype.',
    source: 'DECISIONS.md §16',
  },
  {
    id: 'priority',
    term: 'Priority score and rank',
    short:
      'The planning output that orders segments for inspection. It is kept separate from evidence confidence, and it is not a probability of failure.',
    source: 'DECISIONS.md §14',
  },
  {
    id: 'recommended_action',
    term: 'Recommended action (INSPECT, MONITOR, VERIFY, …)',
    short:
      'The label the engine attaches to each segment. The allowed values are fixed in the project config; the app shows them exactly as given. Pipe Dreams plans inspections. It does not authorise repair or replacement.',
    source: 'API_CONTRACT.md: enums; DECISIONS.md §1',
  },
  {
    id: 'verify_escalate',
    term: 'VERIFY / ESCALATE / DEFER',
    short:
      'Governance rules that send a segment to a person, for example high consequence with low evidence confidence. They are review rules, not validated predictions.',
    source: 'DECISIONS.md §15; ARCHITECTURE.md (governance)',
  },
];

export const GLOSSARY_BY_ID: Record<GlossaryId, GlossaryEntry> = Object.fromEntries(
  GLOSSARY.map((g) => [g.id, g]),
) as Record<GlossaryId, GlossaryEntry>;

export const GLOSSARY_PATH = '/glossary';
