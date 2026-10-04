import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router';
import { ArrowRight, CaretLeft, CaretRight, Pause, Play } from '@phosphor-icons/react';
import { AUDIT_CINEMA, CANDIDATE_DESCRIPTIONS, CANDIDATE_IDS } from '../../config/display';
import { useAssets, useEscalations, useRankChanges } from '../../hooks';
import { usePrefersReducedMotion } from '../../hooks/motion';
import { useFlip } from '../../hooks/useFlip';
import { useAssetLink } from '../../hooks/useAssetLink';
import { api } from '../../lib/api';
import { formatSigned } from '../../lib/format';
import type { AssetListItem, AuditEvent } from '../../types/api';
import { DecisionPill } from '../Pill/Pill';
import { Term } from '../Term/Term';
import type { CandidateFrame, Frame, Highlight } from './replayFrames';
import { frameAt } from './replayFrames';
import type { Cinema } from './useCinema';
import styles from './AgentCinema.module.css';

const EASE_MOVE = 'cubic-bezier(0.77, 0, 0.175, 1)';
const EASE_OUT = 'cubic-bezier(0.22, 1, 0.36, 1)';

function toneOf(type: string): 'accept' | 'reject' | 'warn' | 'neutral' {
  if (type === 'ACCEPT') return 'accept';
  if (type === 'REJECT') return 'reject';
  if (type === 'ESCALATE') return 'warn';
  return 'neutral';
}

const HIGHLIGHT_CAPTION: Record<Highlight, string> = {
  'plan-v1': 'V1 plan: its Top 25 appear',
  'selected-v1': 'Evaluated: V1 assets inside the frozen capacity',
  'changed-v2': 'V2 plan: new to the Top 25, or listed in rank changes',
  escalated: 'Escalated for human review',
  none: 'No per-segment data for this step in the audit artifact',
};

// ---------------------------------------------------------------- positions

interface Pt {
  id: string;
  lat: number;
  lon: number;
}

const MAP_VIEW = { w: 320, h: 230, pad: 18 };

/** Equirectangular projection of asset centroids into the mini-map. Presentation only. */
export function projectPoints(points: Pt[]): Map<string, { x: number; y: number }> {
  const out = new Map<string, { x: number; y: number }>();
  if (points.length === 0) return out;
  const lats = points.map((p) => p.lat);
  const lons = points.map((p) => p.lon);
  const [minLat, maxLat, minLon, maxLon] = [Math.min(...lats), Math.max(...lats), Math.min(...lons), Math.max(...lons)];
  const k = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
  const w = Math.max((maxLon - minLon) * k, 1e-6);
  const h = Math.max(maxLat - minLat, 1e-6);
  const { w: W, h: H, pad } = MAP_VIEW;
  const s = Math.min((W - 2 * pad) / w, (H - 2 * pad) / h);
  const ox = (W - w * s) / 2;
  const oy = (H - h * s) / 2;
  for (const p of points) out.set(p.id, { x: ox + (p.lon - minLon) * k * s, y: oy + (maxLat - p.lat) * s });
  return out;
}

/** Centroids for escalated assets that are not already in either Top N list. */
function useExtraPositions(ids: string[]): Pt[] {
  const [pts, setPts] = useState<Pt[]>([]);
  const key = ids.join(',');
  useEffect(() => {
    let alive = true;
    if (ids.length === 0) {
      setPts([]);
      return;
    }
    Promise.allSettled(ids.map((id) => api.getAsset(id))).then((res) => {
      if (!alive) return;
      setPts(
        res.flatMap((r) =>
          r.status === 'fulfilled' ? [{ id: r.value.data.asset_id, lat: r.value.data.latitude, lon: r.value.data.longitude }] : [],
        ),
      );
    });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return pts;
}

// ---------------------------------------------------------------- pieces

function Transport({ sorted, frame, cinema }: { sorted: AuditEvent[]; frame: Frame; cinema: Cinema }) {
  const progress = frame.total > 1 ? frame.step / (frame.total - 1) : 1;
  return (
    <div className={styles.transport}>
      <div className={styles.buttons}>
        <button
          type="button"
          className={styles.iconBtn}
          onClick={() => cinema.command('prev')}
          disabled={frame.step === 0}
          aria-label="Previous step"
        >
          <CaretLeft size={20} weight="bold" aria-hidden="true" />
        </button>
        <button
          type="button"
          className={`${styles.iconBtn} ${styles.playBtn}`}
          onClick={cinema.toggle}
          aria-label={cinema.playing ? 'Pause agent run' : 'Play agent run'}
        >
          {cinema.playing ? (
            <Pause size={22} weight="fill" aria-hidden="true" />
          ) : (
            <Play size={22} weight="fill" aria-hidden="true" />
          )}
        </button>
        <button
          type="button"
          className={styles.iconBtn}
          onClick={() => cinema.command('next')}
          disabled={frame.step >= frame.total - 1}
          aria-label="Next step"
        >
          <CaretRight size={20} weight="bold" aria-hidden="true" />
        </button>
      </div>
      <div className={styles.track} style={{ ['--progress' as string]: String(progress) }}>
        <input
          type="range"
          className={styles.range}
          min={0}
          max={Math.max(frame.total - 1, 0)}
          step={1}
          value={frame.step}
          onChange={(e) => cinema.setStep(Number(e.target.value))}
          aria-label="Agent run step"
          aria-valuetext={`Step ${frame.step + 1} of ${frame.total}: ${frame.event.event_type}`}
        />
        <ol className={styles.ticks} aria-hidden="true">
          {sorted.map((e, i) => (
            <li
              key={e.seq}
              className={`${styles.tick} ${styles[`tick_${toneOf(e.event_type)}`]} ${i <= frame.step ? styles.tickDone : ''} ${
                i === frame.step ? styles.tickNow : ''
              }`}
              onClick={() => cinema.setStep(i)}
              title={`${i + 1}. ${e.event_type}`}
            />
          ))}
        </ol>
      </div>
      <p className={styles.counter}>
        <span className={styles.counterNow}>{String(frame.step + 1).padStart(2, '0')}</span>
        <span className={styles.counterOf}> / {String(frame.total).padStart(2, '0')}</span>
      </p>
    </div>
  );
}

function GateRow({ c }: { c: CandidateFrame }) {
  const ref = useRef<HTMLLIElement>(null);
  const reduced = usePrefersReducedMotion();
  const prevStage = useRef(c.stage);
  useLayoutEffect(() => {
    const was = prevStage.current;
    prevStage.current = c.stage;
    const el = ref.current?.querySelector<HTMLElement>('[data-stamp]');
    if (reduced || !el || typeof el.animate !== 'function' || was === 'resolved' || c.stage !== 'resolved') return;
    el.animate([{ opacity: 0, transform: 'scale(1.08)' }, { opacity: 1, transform: 'none' }], {
      duration: AUDIT_CINEMA.stampMs,
      easing: EASE_OUT,
    });
  }, [c.stage, reduced]);
  const r = c.result;
  const decision = c.stage === 'resolved' && r ? r.decision : null;
  return (
    <li
      ref={ref}
      className={`${styles.gateRow} ${styles[`gate_${c.stage}`]} ${decision ? styles[`gate_${decision}`] : ''}`}
      data-candidate={c.id}
      data-stage={c.stage}
    >
      <span className={styles.gateId}>{c.id}</span>
      <span className={styles.gateDesc}>{CANDIDATE_DESCRIPTIONS[c.id] ?? ''}</span>
      <span className={styles.gateState} data-stamp>
        {decision ? (
          <DecisionPill decision={decision} />
        ) : c.stage === 'testing' ? (
          <span className={styles.testing}>Testing</span>
        ) : (
          <span className={styles.waiting}>Waiting</span>
        )}
      </span>
      <span className={styles.gateNums}>
        {c.stage === 'testing' && r && `On ${r.n_origins} validation origins…`}
        {c.stage === 'resolved' && r && (
          <>
            {r.origin_wins}/{r.n_origins} won · gain {formatSigned(r.difference)} · needs {formatSigned(r.required_delta)}
          </>
        )}
      </span>
    </li>
  );
}

interface RowProps {
  item: AssetListItem;
  plan: 'v1' | 'v2';
  v1Rank: number | undefined;
  lit: boolean;
  escalated: boolean;
  onOpen: (id: string) => void;
}

function RankRow({ item, plan, v1Rank, lit, escalated, onOpen }: RowProps) {
  let chip: string | null = null;
  if (plan === 'v2') chip = v1Rank === undefined ? 'new' : v1Rank === item.rank ? null : `was #${v1Rank}`;
  return (
    <li data-flip-key={item.asset_id} className={`${styles.row} ${lit ? styles.rowLit : ''}`}>
      <button type="button" className={styles.rowBtn} onClick={() => onOpen(item.asset_id)} aria-label={`Open asset ${item.asset_id}`}>
        <span className={styles.rank}>#{item.rank}</span>
        <span className={styles.assetId}>{item.asset_id}</span>
        {item.selected && <span className={styles.inPlan} title="Inside the frozen capacity (selected)" aria-label="selected" />}
        <span className={styles.rowMeta}>
          {escalated && <span className={styles.escTag}>escalated</span>}
          {chip && <span className={`${styles.chip} ${chip === 'new' ? styles.chipNew : ''}`}>{chip}</span>}
          <span className={styles.tier}>{item.consequence_tier}</span>
        </span>
      </button>
    </li>
  );
}

function MiniMap({
  points,
  plan,
  lit,
  frameKey,
  highlight,
}: {
  points: Map<string, { x: number; y: number }>;
  plan: Set<string>;
  lit: Set<string>;
  frameKey: string;
  highlight: Highlight;
}) {
  const ref = useRef<SVGSVGElement>(null);
  const reduced = usePrefersReducedMotion();
  // One expanding ring per touched asset, once per step. transform + opacity only.
  useLayoutEffect(() => {
    const svg = ref.current;
    if (reduced || !svg) return;
    const anims: Animation[] = [];
    svg.querySelectorAll<SVGCircleElement>('[data-ring]').forEach((el, i) => {
      if (typeof el.animate !== 'function') return;
      anims.push(
        el.animate(
          [
            { opacity: 0.7, transform: 'scale(1)' },
            { opacity: 0, transform: 'scale(3.2)' },
          ],
          { duration: AUDIT_CINEMA.pulseMs, delay: Math.min(i * 30, 300), easing: EASE_OUT, fill: 'both' },
        ),
      );
    });
    return () => anims.forEach((a) => a.cancel());
  }, [frameKey, reduced]);

  const entries = [...points.entries()];
  return (
    <figure className={styles.mapFig}>
      <svg
        ref={ref}
        className={styles.mini}
        viewBox={`0 0 ${MAP_VIEW.w} ${MAP_VIEW.h}`}
        role="img"
        aria-label={`Asset locations. ${lit.size} highlighted: ${HIGHLIGHT_CAPTION[highlight]}.`}
      >
        {entries.map(([id, p]) => (
          <circle
            key={id}
            cx={p.x}
            cy={p.y}
            r={lit.has(id) ? 6 : plan.has(id) ? 3.5 : 2.5}
            className={lit.has(id) ? styles.dotLit : plan.has(id) ? styles.dotPlan : styles.dotIdle}
          />
        ))}
        {!reduced &&
          entries
            .filter(([id]) => lit.has(id))
            .map(([id, p]) => (
              <circle
                key={`${frameKey}-${id}`}
                data-ring
                cx={p.x}
                cy={p.y}
                r={6}
                className={styles.ring}
                style={{ transformOrigin: `${p.x}px ${p.y}px`, transformBox: 'view-box' }}
              />
            ))}
      </svg>
      <figcaption className={styles.mapCap}>{HIGHLIGHT_CAPTION[highlight]}</figcaption>
    </figure>
  );
}

// ---------------------------------------------------------------- main

export interface AgentCinemaProps {
  sorted: AuditEvent[];
  cinema: Cinema;
}

/**
 * "Agent run as cinema": a scrubbable replay of the audit log. Gate cards resolve,
 * the Top 25 reorders (V1 -> V2) and the mini-map lights the assets each step touched.
 * Every value comes from the API; this component only chooses what is on stage.
 */
export function AgentCinema({ sorted, cinema }: AgentCinemaProps) {
  const reduced = usePrefersReducedMotion();
  const openAsset = useAssetLink();
  const topN = AUDIT_CINEMA.topN;
  const v1 = useAssets({ plan: 'v1', limit: topN });
  const v2 = useAssets({ plan: 'v2', limit: topN });
  const changes = useRankChanges({ demo_only: false, limit: 500 });
  const esc = useEscalations();

  const frame = frameAt(sorted, cinema.step, CANDIDATE_IDS);

  const v1Items = useMemo(() => v1.data?.items ?? [], [v1.data]);
  const v2Items = useMemo(() => v2.data?.items ?? [], [v2.data]);
  const v1RankById = useMemo(() => new Map(v1Items.map((i) => [i.asset_id, i.rank])), [v1Items]);
  const v2Ids = useMemo(() => new Set(v2Items.map((i) => i.asset_id)), [v2Items]);
  const escIds = useMemo(() => new Set((esc.data?.items ?? []).map((e) => e.asset_id)), [esc.data]);
  const changedIds = useMemo(() => new Set((changes.data?.items ?? []).map((c) => c.asset_id)), [changes.data]);

  const known = useMemo(() => {
    const ids = new Set<string>();
    v1Items.forEach((i) => ids.add(i.asset_id));
    v2Items.forEach((i) => ids.add(i.asset_id));
    return ids;
  }, [v1Items, v2Items]);
  const extraIds = useMemo(() => [...escIds].filter((id) => !known.has(id)).slice(0, topN), [escIds, known, topN]);
  const extra = useExtraPositions(extraIds);

  const points = useMemo(() => {
    const pts: Pt[] = [];
    const seen = new Set<string>();
    for (const i of [...v1Items, ...v2Items]) {
      if (seen.has(i.asset_id)) continue;
      seen.add(i.asset_id);
      pts.push({ id: i.asset_id, lat: i.latitude, lon: i.longitude });
    }
    extra.forEach((p) => !seen.has(p.id) && pts.push(p));
    return projectPoints(pts);
  }, [v1Items, v2Items, extra]);

  const plan = frame?.plan ?? 'v2';
  const items = plan === 'v1' ? v1Items : v2Items;
  const planIds = useMemo(() => new Set(items.map((i) => i.asset_id)), [items]);

  // Membership sets only: which API-provided assets this step lights up.
  const lit = useMemo(() => {
    const h = frame?.highlight ?? 'none';
    if (h === 'plan-v1') return new Set(v1Items.map((i) => i.asset_id));
    if (h === 'selected-v1') return new Set(v1Items.filter((i) => i.selected).map((i) => i.asset_id));
    if (h === 'changed-v2')
      return new Set(v2Items.filter((i) => !v1RankById.has(i.asset_id) || changedIds.has(i.asset_id)).map((i) => i.asset_id));
    if (h === 'escalated') return new Set(escIds);
    return new Set<string>();
  }, [frame?.highlight, v1Items, v2Items, v1RankById, changedIds, escIds]);

  const dropped = plan === 'v2' ? v1Items.filter((i) => !v2Ids.has(i.asset_id)) : [];

  const listRef = useRef<HTMLOListElement>(null);
  useFlip(listRef, `${plan}:${items.map((i) => i.asset_id).join(',')}`, {
    enabled: !reduced,
    // Autoplay is explanatory and gets the full move; manual stepping (keyboard, scrubber) stays snappy.
    moveMs: cinema.playing ? AUDIT_CINEMA.moveMs : AUDIT_CINEMA.manualMoveMs,
    staggerMs: cinema.playing ? AUDIT_CINEMA.moveStaggerMs : 0,
    enterMs: AUDIT_CINEMA.enterMs,
    fadeMs: AUDIT_CINEMA.reducedFadeMs,
    easing: EASE_MOVE,
  });

  const [announce, setAnnounce] = useState('');
  useEffect(() => {
    if (!cinema.engaged || !frame) return;
    setAnnounce(`Step ${frame.step + 1} of ${frame.total}: ${frame.event.event_type}. ${frame.event.summary}`);
  }, [cinema.engaged, frame?.step, frame?.total]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!frame) return null;
  const firstLit = [...lit][0];
  const tone = toneOf(frame.event.event_type);
  const listLoading = v1.status === 'loading' || v2.status === 'loading';
  const listError = v1.status === 'error' || v2.status === 'error';

  return (
    <section
      className={styles.cinema}
      aria-label="Agent run replay"
      onKeyDown={cinema.onKeyDown}
      data-plan={plan}
      data-step={frame.step}
      data-playing={cinema.playing || undefined}
    >
      <Transport sorted={sorted} frame={frame} cinema={cinema} />
      <p
        className={`${styles.now} ${styles[`now_${tone}`]} ${cinema.playing && !reduced ? styles.nowAnimated : ''} ${reduced && cinema.engaged ? styles.nowFade : ''}`}
        key={frame.step}
      >
        <span className={styles.nowType}>{frame.event.event_type}</span>
        <span className={styles.nowText}>{frame.event.summary}</span>
      </p>
      <p className={styles.hint}>Arrow keys step, Space plays or pauses.</p>
      <div className={styles.srOnly} aria-live="polite" aria-atomic="true">
        {announce}
      </div>

      <div className={styles.stage}>
        <div className={styles.side}>
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>
              <Term id="revision_gate">Revision gate</Term>
            </h2>
            <ol className={styles.gates}>
              {frame.candidates.map((c) => (
                <GateRow key={c.id} c={c} />
              ))}
            </ol>
          </div>
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>
              Assets touched
              {firstLit && (
                <Link className={styles.mapLink} to={`/map?asset=${encodeURIComponent(firstLit)}`}>
                  Open map <ArrowRight size={16} weight="bold" aria-hidden="true" />
                </Link>
              )}
            </h2>
            <MiniMap points={points} plan={planIds} lit={lit} frameKey={`${frame.step}`} highlight={frame.highlight} />
          </div>
        </div>

        <div className={`${styles.panel} ${styles.listPanel}`}>
          <h2 className={styles.panelTitle}>
            <span>Top {topN}</span>
            <span className={`${styles.planTag} ${plan === 'v2' ? styles.planTagV2 : ''}`}>
              {plan === 'v1' ? 'V1 plan' : 'V2 plan'}
            </span>
          </h2>
          {listError ? (
            <p className={styles.muted}>The ranked lists could not be loaded.</p>
          ) : listLoading ? (
            <p className={styles.muted}>Loading ranked lists…</p>
          ) : (
            <ol ref={listRef} className={styles.list} style={{ ['--rows' as string]: Math.ceil(items.length / 2) }}>
              {items.map((item) => (
                <RankRow
                  key={item.asset_id}
                  item={item}
                  plan={plan}
                  v1Rank={v1RankById.get(item.asset_id)}
                  lit={lit.has(item.asset_id)}
                  escalated={frame.escalated && escIds.has(item.asset_id)}
                  onOpen={openAsset}
                />
              ))}
            </ol>
          )}
          {dropped.length > 0 && (
            <p className={styles.dropped}>
              <span className={styles.droppedLabel}>Left the Top {topN}:</span>{' '}
              {dropped.map((d) => `${d.asset_id} (was #${d.rank})`).join(', ')}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
