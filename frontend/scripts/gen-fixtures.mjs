// Deterministic generator for SYNTHETIC frontend fixtures.
// Usage (from frontend/): node scripts/gen-fixtures.mjs
// Every number here is made up. Files carry meta.synthetic = true.
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'fixtures');
mkdirSync(OUT, { recursive: true });

// ---- seeded PRNG (mulberry32) ----
let state = 20261003;
function rand() {
  state = (state + 0x6d2b79f5) >>> 0;
  let t = state;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
const between = (a, b) => a + (b - a) * rand();
const pick = (arr) => arr[Math.floor(rand() * arr.length)];
function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
const round = (x, d) => Number(x.toFixed(d));

const META = { synthetic: true, config_hash: 'PLACEHOLDER' };
const envelope = (data) => ({ meta: META, data });
function write(name, obj) {
  writeFileSync(join(OUT, name), JSON.stringify(obj, null, 2) + '\n');
}

// =========================================================== health
write('health.json', {
  status: 'ok',
  artifacts_loaded: true,
  artifact_dir: 'artifacts/synthetic',
  synthetic: true,
});

// =========================================================== assets
const N = 60;
const SELECTED_CUTOFF = 25;
const ids = Array.from({ length: N }, (_, i) => `seg_${String(i + 1).padStart(6, '0')}`);

const KM_LAT = 111.0;
const KM_LON = 111.0 * Math.cos((51.04 * Math.PI) / 180);

function makeGeometry() {
  const nVerts = 2 + Math.floor(rand() * 4); // 2..5
  const totalM = between(100, 400);
  const segM = totalM / (nVerts - 1);
  let lon = between(-114.25, -113.92);
  let lat = between(50.9, 51.18);
  let bearing = between(0, Math.PI * 2);
  const coords = [[round(lon, 6), round(lat, 6)]];
  for (let i = 1; i < nVerts; i++) {
    bearing += between(-0.5, 0.5);
    lon += (Math.sin(bearing) * segM) / 1000 / KM_LON;
    lat += (Math.cos(bearing) * segM) / 1000 / KM_LAT;
    coords.push([round(lon, 6), round(lat, 6)]);
  }
  return coords;
}
function lengthM(coords) {
  let total = 0;
  for (let i = 1; i < coords.length; i++) {
    const dx = (coords[i][0] - coords[i - 1][0]) * KM_LON * 1000;
    const dy = (coords[i][1] - coords[i - 1][1]) * KM_LAT * 1000;
    total += Math.hypot(dx, dy);
  }
  return round(total, 1);
}

// Compact synthetic street grid (~3 km x 2 km around -114.08, 51.04): 7 x 5
// junctions, 500 m spacing, jittered; 58 grid edges + 2 diagonals = 60 runs
// that share endpoints. Separate PRNG so other fixtures are unaffected.
function makeNetwork() {
  let st = 777001;
  const r = () => {
    st = (st + 0x6d2b79f5) >>> 0;
    let t = st;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const COLS = 7;
  const ROWS = 5;
  const STEP = 500;
  const toLon = (m) => m / 1000 / KM_LON;
  const toLat = (m) => m / 1000 / KM_LAT;
  const lon0 = -114.08 - toLon(((COLS - 1) * STEP) / 2);
  const lat0 = 51.04 - toLat(((ROWS - 1) * STEP) / 2);
  const node = [];
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      node.push([x * STEP + (r() - 0.5) * 100, y * STEP + (r() - 0.5) * 100]); // metres
    }
  }
  const at = (x, y) => node[y * COLS + x];
  const pairs = [];
  for (let y = 0; y < ROWS; y++) for (let x = 0; x < COLS - 1; x++) pairs.push([at(x, y), at(x + 1, y)]);
  for (let x = 0; x < COLS; x++) for (let y = 0; y < ROWS - 1; y++) pairs.push([at(x, y), at(x, y + 1)]);
  pairs.push([at(1, 1), at(2, 2)], [at(4, 2), at(5, 3)]);
  return pairs.map(([a, b]) => {
    const pts = [a];
    if (r() < 0.5) {
      const dx = b[0] - a[0];
      const dy = b[1] - a[1];
      const off = (r() - 0.5) * 0.14; // gentle bend as a fraction of run length
      pts.push([a[0] + dx / 2 - dy * off, a[1] + dy / 2 + dx * off]);
    }
    pts.push(b);
    return pts.map(([mx, my]) => [round(lon0 + toLon(mx), 6), round(lat0 + toLat(my), 6)]);
  });
}

// v1 ranking = random permutation of assets
const v1Order = shuffle(ids); // v1Order[r-1] = asset at v1 rank r
const v1Rank = Object.fromEntries(v1Order.map((id, i) => [id, i + 1]));

// v2 ranking = v1 with three swaps (only swapped assets move)
const v2Order = [...v1Order];
function swapRanks(a, b) {
  [v2Order[a - 1], v2Order[b - 1]] = [v2Order[b - 1], v2Order[a - 1]];
}
swapRanks(40, 3); // riser 40 -> 3, partner 3 -> 40
swapRanks(5, 31); // faller 5 -> 31, partner 31 -> 5
swapRanks(28, 22); // action change 28 -> 22, partner 22 -> 28
const v2Rank = Object.fromEntries(v2Order.map((id, i) => [id, i + 1]));

const riser = v1Order[39];
const riserPartner = v1Order[2];
const faller = v1Order[4];
const fallerPartner = v1Order[30];
const actionAsset = v1Order[27];
const actionPartner = v1Order[21];
const forcedHigh = new Set([riser, faller, actionAsset]);

// confidence mix: 30 HIGH, 18 MEDIUM, 12 LOW_VERIFY
const confPool = shuffle([
  ...Array(30).fill('HIGH'),
  ...Array(18).fill('MEDIUM'),
  ...Array(12).fill('LOW_VERIFY'),
]);
const conf = Object.fromEntries(ids.map((id, i) => [id, confPool[i]]));
for (const id of forcedHigh) {
  if (conf[id] !== 'HIGH') {
    const donor = ids.find((o) => !forcedHigh.has(o) && conf[o] === 'HIGH');
    [conf[id], conf[donor]] = [conf[donor], conf[id]];
  }
}

const TIERS = ['T1', 'T2', 'T3'];
function actionFor(id, rank) {
  if (conf[id] === 'LOW_VERIFY') return 'VERIFY';
  if (rank <= 12) return 'INSPECT';
  if (rank <= SELECTED_CUTOFF) return 'CONDITION_ASSESS';
  return 'MONITOR';
}

const REASONS = {
  [riser]: ['recency weighting', 'recent breaks weighted under hl10'],
  [riserPartner]: ['relative reorder after recency weighting', null],
  [faller]: ['older breaks down-weighted', null],
  [fallerPartner]: ['relative reorder after recency weighting', null],
  [actionAsset]: ['recent breaks weighted under hl10', 'crosses inspection budget cut-off'],
  [actionPartner]: ['relative reorder after recency weighting', null],
};
const DEMO = new Set([riser, faller, actionAsset]);

function priorityFor(rank) {
  return round(0.95 - (0.9 * (rank - 1)) / (N - 1) + between(-0.003, 0.003), 3);
}

// Geometry comes from a separate seeded PRNG (makeNetwork) so the main PRNG
// sequence, and therefore every other fixture value, is unchanged.
const NETWORK = makeNetwork();
const assets = ids.map((id, idx) => {
  const legacyCoords = makeGeometry(); // consumed only to keep the main PRNG sequence stable
  const coords = NETWORK[idx];
  const mid = coords[Math.floor(coords.length / 2)];
  const c = conf[id];
  const quality =
    c === 'HIGH' ? between(0.82, 0.98) : c === 'MEDIUM' ? between(0.6, 0.8) : between(0.35, 0.58);
  return {
    id,
    coords,
    length_m: lengthM(legacyCoords),
    tier: pick(TIERS),
    conf: c,
    lat: mid[1],
    lon: mid[0],
    quality: round(quality, 2),
    stability: round(between(0.4, 0.95), 2),
    nBreaks: c === 'HIGH' ? 2 + Math.floor(rand() * 4) : c === 'MEDIUM' ? 1 + Math.floor(rand() * 2) : 0,
    dist: round(between(1, 18), 0),
    sourceIds: Array.from({ length: 1 + Math.floor(rand() * 2) }, () =>
      String(10000 + Math.floor(rand() * 89999)),
    ),
  };
});
const byId = Object.fromEntries(assets.map((a) => [a.id, a]));

function planFields(id, plan) {
  const rank = plan === 'v1' ? v1Rank[id] : v2Rank[id];
  const priority = priorityFor(rank);
  let action = actionFor(id, rank);
  if (id === actionAsset) action = plan === 'v1' ? 'MONITOR' : 'INSPECT';
  const likelihood = round(Math.min(0.99, priority * between(0.85, 1.08)), 2);
  return {
    rank,
    selected: rank <= SELECTED_CUTOFF,
    likelihood_score: likelihood,
    priority_score: priority,
    recommended_action: action,
    revision_reason: plan === 'v2' && REASONS[id] ? REASONS[id][0] : null,
  };
}

const planV1 = Object.fromEntries(ids.map((id) => [id, planFields(id, 'v1')]));
const planV2 = Object.fromEntries(ids.map((id) => [id, planFields(id, 'v2')]));

function evidenceBasis(a) {
  if (a.conf === 'HIGH')
    return `${a.nBreaks} matched breaks since 2000; nearest-line distance < ${Math.max(5, a.dist)} m`;
  if (a.conf === 'MEDIUM')
    return `${a.nBreaks} matched break${a.nBreaks === 1 ? '' : 's'} since 2000; match distance about ${a.dist} m`;
  return 'No matched breaks since 2000; asset record unverified, needs field confirmation';
}

// geojson (v1, v2 share geometry)
function geojson(plan) {
  const planMap = plan === 'v1' ? planV1 : planV2;
  const features = assets
    .map((a) => ({
      type: 'Feature',
      id: a.id,
      geometry: { type: 'LineString', coordinates: a.coords },
      properties: {
        asset_id: a.id,
        rank: planMap[a.id].rank,
        selected: planMap[a.id].selected,
        consequence_tier: a.tier,
        evidence_confidence: a.conf,
        recommended_action: planMap[a.id].recommended_action,
      },
    }))
    .sort((x, y) => x.properties.rank - y.properties.rank);
  return envelope({ type: 'FeatureCollection', features });
}
write('assets_geojson_v1.json', geojson('v1'));
write('assets_geojson_v2.json', geojson('v2'));

// assets list (plan v2)
write(
  'assets.json',
  envelope({
    plan: 'v2',
    total: N,
    limit: 100,
    offset: 0,
    items: assets
      .map((a) => ({
        asset_id: a.id,
        rank: planV2[a.id].rank,
        selected: planV2[a.id].selected,
        length_m: a.length_m,
        priority_score: planV2[a.id].priority_score,
        consequence_tier: a.tier,
        evidence_confidence: a.conf,
        recommended_action: planV2[a.id].recommended_action,
        latitude: a.lat,
        longitude: a.lon,
      }))
      .sort((x, y) => x.rank - y.rank),
  }),
);

// rank changes
function rankChangeRow(id) {
  const [r1, r2] = REASONS[id];
  return {
    asset_id: id,
    rank_v1: v1Rank[id],
    rank_v2: v2Rank[id],
    delta_rank: v2Rank[id] - v1Rank[id],
    action_v1: planV1[id].recommended_action,
    action_v2: planV2[id].recommended_action,
    reason_1: r1,
    reason_2: r2,
    show_in_demo: DEMO.has(id),
  };
}
const changedIds = [riser, faller, actionAsset, riserPartner, fallerPartner, actionPartner];
const rankChangeRows = changedIds.map(rankChangeRow);
write('rank_changes.json', envelope({ items: rankChangeRows }));
const rcById = Object.fromEntries(rankChangeRows.map((r) => [r.asset_id, r]));

// asset details (values are the `data` of /api/assets/{id})
const details = {};
for (const a of assets) {
  const rc = rcById[a.id];
  details[a.id] = {
    asset_id: a.id,
    source_segment_ids: a.sourceIds,
    length_m: a.length_m,
    consequence_tier: a.tier,
    evidence_confidence: a.conf,
    association_quality: a.quality,
    rank_stability: a.stability,
    evidence_basis: evidenceBasis(a),
    latitude: a.lat,
    longitude: a.lon,
    geometry: { type: 'LineString', coordinates: a.coords },
    v1: planV1[a.id],
    v2: planV2[a.id],
    rank_change: rc
      ? {
          delta_rank: rc.delta_rank,
          reason_1: rc.reason_1,
          reason_2: rc.reason_2,
          show_in_demo: rc.show_in_demo,
        }
      : null,
  };
}
write('asset_details.json', details);

// =========================================================== overview
const BUDGETS = [1, 2, 5, 10];
const BASE = {
  count_only: [0.06, 0.1, 0.18, 0.29],
  V1: [0.08, 0.13, 0.21, 0.33],
  C2: [0.09, 0.15, 0.24, 0.36],
};
const ORIGINS = ['2013-12-31', '2016-12-31', '2019-12-31'];
const ORIGIN_OFFSET = { '2013-12-31': -0.012, '2016-12-31': 0, '2019-12-31': 0.01 };
const MATCH_SHARE = { '2013-12-31': 0.81, '2016-12-31': 0.84, '2019-12-31': 0.86 };

// gate figures (shared by overview series and audit)
const GATE = {
  C1: { wins: [false, true, false], pooled: 0.193, se: 0.009 },
  C2: { wins: [true, false, true], pooled: 0.205, se: 0.008 },
  C3: { wins: [false, true, true], pooled: 0.194, se: 0.009 },
  C4: { wins: [false, false, false], pooled: 0.184, se: 0.008 },
};
const POOLED_V1 = 0.19;
const REQUIRED_WINS = 2;
const N_ORIGINS = 3;
const MIN_SE = 1.0;
for (const [cid, g] of Object.entries(GATE)) {
  g.originWins = g.wins.filter(Boolean).length;
  g.difference = round(g.pooled - POOLED_V1, 4);
  g.required = round(MIN_SE * g.se, 4);
  g.decision = g.originWins >= REQUIRED_WINS && g.difference >= g.required ? 'ACCEPT' : 'REJECT';
}
if (
  GATE.C1.decision !== 'REJECT' ||
  GATE.C2.decision !== 'ACCEPT' ||
  GATE.C3.decision !== 'REJECT' ||
  GATE.C4.decision !== 'REJECT'
) {
  throw new Error('fixture gate outcomes drifted from the intended C1 R, C2 A, C3 R, C4 R');
}

function captureFor(policy, bi, origin) {
  const offset = origin ? ORIGIN_OFFSET[origin] : 0;
  let base;
  if (policy === 'count_only' || policy === 'V1' || policy === 'C2') {
    base = BASE[policy][bi];
    if (policy === 'C2' && origin) {
      // C2 pattern: wins 2013 and 2019, loses 2016
      const oi = ORIGINS.indexOf(origin);
      base = BASE.V1[bi] + (GATE.C2.wins[oi] ? 0.011 : -0.006);
    }
  } else {
    const oi = ORIGINS.indexOf(origin);
    const win = GATE[policy].wins[oi];
    base = BASE.V1[bi] + (win ? 0.007 : -0.006);
  }
  return Math.max(0.01, base + offset + between(-0.002, 0.002));
}
const ORGANIZER = [0.05, 0.08, 0.14, 0.23];

const series = [];
function pushRows(split, origin, policies) {
  const countOnly = {};
  const rows = [];
  for (const policy of policies) {
    BUDGETS.forEach((budget, bi) => {
      const isBaseline = policy === 'count_only' || policy === 'organizer_cell';
      let asset = null;
      let event;
      if (policy === 'organizer_cell') {
        event = round(ORGANIZER[bi] + (origin ? ORIGIN_OFFSET[origin] * 0.5 : 0), 3);
      } else {
        asset = round(captureFor(policy, bi, origin), 3);
        event = round(Math.min(0.95, asset * between(1.04, 1.16)), 3);
      }
      const row = { policy, bi, budget, isBaseline, asset, event };
      rows.push(row);
      if (policy === 'count_only') countOnly[budget] = row;
    });
  }
  for (const r of rows) {
    const co = countOnly[r.budget];
    const lift =
      r.asset !== null
        ? round(r.asset / co.asset, 2)
        : round(r.event / co.event, 2);
    const centre = r.asset !== null ? r.asset : r.event;
    const width = round(between(0.015, 0.035) * (1 + r.bi * 0.35), 3);
    const g = GATE[r.policy];
    series.push({
      split,
      origin_cutoff: origin,
      policy_id: r.policy,
      policy_type: r.isBaseline ? 'baseline' : 'policy',
      budget_pct: r.budget,
      asset_capture: r.asset,
      event_capture: r.event,
      lift_vs_count_only: lift,
      ci_low: round(Math.max(0, centre - width), 3),
      ci_high: round(centre + width, 3),
      matched_break_share:
        r.policy === 'organizer_cell'
          ? null
          : origin
            ? round(MATCH_SHARE[origin] + between(-0.01, 0.01), 2)
            : round(0.85 + between(-0.01, 0.01), 2),
      pooled_gate_score:
        split === 'validation' && !r.isBaseline ? (r.policy === 'V1' ? POOLED_V1 : g.pooled) : null,
      accepted_vs_v1:
        split === 'validation' && g ? g.decision === 'ACCEPT' : null,
      notes:
        r.policy === 'organizer_cell'
          ? 'Event capture only; no asset-level capture for this baseline'
          : split === 'confirmation'
            ? 'Directional relative lift only'
            : null,
    });
  }
}
for (const origin of ORIGINS) {
  pushRows('validation', origin, ['V1', 'C1', 'C2', 'C3', 'C4', 'count_only', 'organizer_cell']);
}
pushRows('final', null, ['V1', 'C2', 'count_only', 'organizer_cell']);

// confirmation: relative lift only, asset_capture null
{
  const base = {};
  for (const policy of ['count_only', 'V1', 'C2']) {
    for (const budget of [5, 10]) {
      const bi = BUDGETS.indexOf(budget);
      base[`${policy}-${budget}`] = round(BASE[policy][bi] * between(1.05, 1.15), 3);
    }
  }
  for (const policy of ['count_only', 'V1', 'C2']) {
    for (const budget of [5, 10]) {
      const ev = base[`${policy}-${budget}`];
      const co = base[`count_only-${budget}`];
      series.push({
        split: 'confirmation',
        origin_cutoff: null,
        policy_id: policy,
        policy_type: policy === 'count_only' ? 'baseline' : 'policy',
        budget_pct: budget,
        asset_capture: null,
        event_capture: ev,
        lift_vs_count_only: round(ev / co, 2),
        ci_low: round(ev - 0.03, 3),
        ci_high: round(ev + 0.03, 3),
        matched_break_share: 0.84,
        pooled_gate_score: null,
        accepted_vs_v1: null,
        notes: 'Directional relative lift only',
      });
    }
  }
}

write(
  'overview.json',
  envelope({
    git_commit: '0000000',
    git_tag: 'synthetic-placeholder',
    v1_policy_id: 'V1',
    selected_policy_id: 'C2',
    v2_equals_v1: false,
    final_test_previously_viewed: true,
    budgets_pct: BUDGETS,
    revision_gate: {
      min_origin_wins: REQUIRED_WINS,
      n_origins: N_ORIGINS,
      min_improvement_in_se: MIN_SE,
      bootstrap_block_km: 1.0,
    },
    series,
  }),
);

// =========================================================== audit
const CAND_LABEL = {
  C1: 'C1 (2000+ history, no decay, per-asset)',
  C2: 'C2 (full history, hl10 recency, per-asset)',
  C3: 'C3 (full history, no decay, per-metre)',
  C4: 'C4 (2000+ history, hl10 recency, per-asset)',
};
const REASON_TEXT = {
  C1: 'won only 1/3 origins; pooled gain below 1 SE',
  C2: 'won 2/3 origins and pooled gain >= 1 SE',
  C3: 'won 2/3 origins but pooled gain 0.004 is below required 0.009 (1 SE)',
  C4: 'won 0/3 origins; pooled score below V1',
};
function candidateObj(cid) {
  const g = GATE[cid];
  return {
    candidate_id: cid,
    origin_wins: g.originWins,
    n_origins: N_ORIGINS,
    pooled_v1_score: POOLED_V1,
    pooled_candidate_score: g.pooled,
    difference: g.difference,
    bootstrap_se: g.se,
    required_delta: g.required,
    decision: g.decision,
    reason: REASON_TEXT[cid],
  };
}
const events = [];
let clock = Date.UTC(2026, 9, 3, 14, 0, 0);
function addEvent(type, summary, candidate = null, details = {}) {
  clock += 4 * 60 * 1000 + Math.floor(rand() * 90) * 1000;
  events.push({
    seq: events.length + 1,
    event_type: type,
    timestamp: new Date(clock).toISOString().replace(/\.\d{3}Z$/, 'Z'),
    summary,
    candidate,
    details,
  });
}
addEvent('PLAN_V1', 'Built V1 plan: full history, per-asset ranking, budgets 1/2/5/10%', null, {
  policy_id: 'V1',
});
addEvent('EVALUATE', 'Evaluated V1 on 3 validation origins against count-only and organizer baselines', null, {
  origins: ORIGINS,
});
addEvent('DIAGNOSE', 'Diagnosed V1 weakness: recent breaks under-weighted relative to older history', null, {
  hypothesis: 'recency weighting',
});
for (const cid of ['C1', 'C2', 'C3', 'C4']) {
  const cand = candidateObj(cid);
  addEvent('TEST_CANDIDATE', `Testing ${CAND_LABEL[cid]} against V1 on 3 validation origins`, cand, {});
  addEvent(
    cand.decision,
    cand.decision === 'ACCEPT'
      ? `Accepted ${cid}: ${REASON_TEXT[cid]}`
      : `Rejected ${cid}: ${REASON_TEXT[cid]}`,
    cand,
    {},
  );
}
addEvent('PLAN_V2', 'Built V2 plan from accepted candidate C2', null, { policy_id: 'C2' });
addEvent('ESCALATE', 'Escalated assets with high consequence and low evidence confidence for verification', null, {
  count: 8,
});
write('audit.json', envelope({ events }));

// =========================================================== escalations
const OWNERS = ['Water Integrity Lead', 'Asset Data Steward', 'Field Inspection Supervisor'];
const STATUSES = ['OPEN', 'IN_REVIEW', 'CLOSED', 'OPEN', 'IN_REVIEW', 'OPEN', 'CLOSED', 'OPEN'];
const lowVerify = assets
  .filter((a) => a.conf === 'LOW_VERIFY')
  .sort((a, b) => v2Rank[a.id] - v2Rank[b.id])
  .slice(0, 8);
const DEADLINES = [
  '2026-10-24',
  '2026-11-01',
  '2026-11-07',
  '2026-11-15',
  '2026-11-21',
  '2026-12-01',
  '2026-12-12',
  '2026-12-19',
];
write(
  'escalations.json',
  envelope({
    items: lowVerify.map((a, i) => ({
      asset_id: a.id,
      priority_rank: v2Rank[a.id],
      consequence_tier: a.tier,
      evidence_confidence: a.conf,
      escalation_reason:
        a.tier === 'T1'
          ? 'high consequence, low evidence confidence'
          : 'top-ranked asset with low evidence confidence',
      owner: OWNERS[i % OWNERS.length],
      required_action:
        i % 2 === 0 ? 'Verify asset record before scheduling' : 'Confirm break history with field crew',
      response_deadline: DEADLINES[i],
      status: STATUSES[i],
      last_reviewed: i % 3 === 0 ? '2026-10-03' : '2026-10-02',
    })),
  }),
);

// =========================================================== not covered
write(
  'not_covered.json',
  envelope({
    items: [
      {
        coverage_issue_id: 'NC-01',
        scope: 'service connections',
        description: 'Service lines are not in the public pipe layer.',
        why_not_covered: 'No public geometry or break attribution.',
        required_evidence: 'Utility service-line registry',
        ui_severity: 'HIGH',
        source_note: 'Synthetic placeholder text',
      },
      {
        coverage_issue_id: 'NC-02',
        scope: 'private-side pipes',
        description: 'Pipes on private property are outside the public network layer.',
        why_not_covered: 'Ownership boundary; no break records.',
        required_evidence: 'Owner-reported leak records',
        ui_severity: 'HIGH',
        source_note: 'Synthetic placeholder text',
      },
      {
        coverage_issue_id: 'NC-03',
        scope: 'non-public facilities',
        description: 'Pump stations, reservoirs and treatment sites are not modelled as pipe assets.',
        why_not_covered: 'Different failure modes and no public records.',
        required_evidence: 'Facility maintenance logs',
        ui_severity: 'MEDIUM',
        source_note: 'Synthetic placeholder text',
      },
      {
        coverage_issue_id: 'NC-04',
        scope: 'pre-2000 unmatched breaks',
        description: 'Older breaks that cannot be matched to a present-day pipe segment.',
        why_not_covered: 'Present-day network does not reconstruct all historical assets.',
        required_evidence: 'Historical asset register or as-built drawings',
        ui_severity: 'MEDIUM',
        source_note: 'Synthetic placeholder text',
      },
      {
        coverage_issue_id: 'NC-05',
        scope: 'pressure and transient data',
        description: 'No pressure, surge or transient measurements feed the ranking.',
        why_not_covered: 'Not available in the open data used.',
        required_evidence: 'SCADA pressure time series',
        ui_severity: 'LOW',
        source_note: 'Synthetic placeholder text',
      },
    ],
  }),
);

// =========================================================== data quality
write(
  'data_quality.json',
  envelope({
    rows_dropped_missing_coordinates: 112,
    match_rate_by_origin: { '2013': 0.81, '2016': 0.84, '2019': 0.86 },
    match_rate_by_era: { pre_2000: 0.62, '2000_2012': 0.83, '2013_plus': 0.88 },
    unmatched_share_by_era: { pre_2000: 0.38, '2000_2012': 0.17, '2013_plus': 0.12 },
    unreachable_final_test_share: 0.09,
    future_year_pipe_rows_excluded: 14,
    planned_rows_excluded: 230,
    inactive_sensitivity: { included_capture_5pct: 0.21, excluded_capture_5pct: 0.2 },
    retired_status_strata: { ACTIVE: 0.93, RETIRED: 0.07 },
    notes: [
      'Synthetic placeholder figures.',
      'Present-day network does not reconstruct all historical assets.',
    ],
  }),
);

console.log('fixtures written to', OUT);
