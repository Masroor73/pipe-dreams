import { useEffect, useLayoutEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { Term } from '../Term/Term';
import { Link } from 'react-router';
import { ArrowRight } from '@phosphor-icons/react';
import { DataState } from '../DataState/DataState';
import { DecisionPill, Pill } from '../Pill/Pill';
import { Section } from '../Section/Section';
import { CANDIDATE_DESCRIPTIONS, CANDIDATE_IDS } from '../../config/display';
import { useAudit } from '../../hooks';
import type { Resource } from '../../hooks';
import { GATE_EXPLAINER, formatPts } from '../../lib/format';
import type { Audit, CandidateResult, Overview, PolicyId } from '../../types/api';
import { prefersReducedMotion, useInViewOnce } from '../../hooks/motion';
import { EASE_OUT_CSS, MOTION } from '../../hooks/overviewMotion';
import styles from './GateCards.module.css';

/** Select the recorded result for a candidate: last ACCEPT/REJECT event, else last TEST_CANDIDATE. */
export function findCandidate(audit: Audit, id: PolicyId): CandidateResult | undefined {
  const withCandidate = audit.events.filter((e) => e.candidate?.candidate_id === id);
  const decided = withCandidate.filter((e) => e.event_type === 'ACCEPT' || e.event_type === 'REJECT');
  const pick = decided.length > 0 ? decided : withCandidate.filter((e) => e.event_type === 'TEST_CANDIDATE');
  return pick[pick.length - 1]?.candidate ?? undefined;
}

/** Wrap "hl10" with its glossary term when this card is the first in the section to use it. */
function describe(text: string, withTerm: boolean): ReactNode {
  if (!withTerm || !text.includes('hl10')) return text;
  const [before, ...rest] = text.split('hl10');
  return (
    <>
      {before}
      <Term id="hl10">hl10</Term>
      {rest.join('hl10')}
    </>
  );
}

function CandidateCard({
  c,
  selected,
  selectedId,
  termHl10,
}: {
  c: CandidateResult;
  selected: boolean;
  selectedId: string | null;
  termHl10: boolean;
}) {
  // Visual scaling of the two given numbers only.
  const scale = Math.max(Math.abs(c.difference), Math.abs(c.required_delta), 1e-9);
  const gainPct = (Math.max(c.difference, 0) / scale) * 100;
  const reqPct = (Math.max(c.required_delta, 0) / scale) * 100;
  const negative = c.difference < 0;

  return (
    <article className={`${styles.card} ${selected ? styles.selected : ''}`} data-candidate={c.candidate_id}>
      {selected && <span className={styles.ring} data-anim="ring" aria-hidden="true" />}
      <div className={styles.headCol}>
        <header className={styles.cardHead}>
          <h3>{c.candidate_id}</h3>
          <span className={styles.verdict}>
            <span className={styles.testing} data-anim="testing" aria-hidden="true">
              testing…
            </span>
            <span className={styles.stamp} data-anim="stamp">
              <DecisionPill decision={c.decision} selected={selected} selectedId={selectedId} />
            </span>
          </span>
        </header>
        {selected && (
          <span className={styles.ribbon} data-anim="ribbon">
            <Pill tone="accent">Selected as V2</Pill>
          </span>
        )}
      </div>
      <div className={styles.body}>
        <p className={styles.desc}>{describe(CANDIDATE_DESCRIPTIONS[c.candidate_id] ?? '', termHl10)}</p>
        <p className={styles.reason}>{c.reason}</p>
      </div>

      <div className={styles.wins}>
        <span className={styles.label}>
          Origin wins{' '}
          <strong>
            {c.origin_wins}/{c.n_origins}
          </strong>
        </span>
        <span className={styles.pips} aria-hidden="true">
          {Array.from({ length: c.n_origins }, (_, i) => (
            <span key={i} className={styles.pip}>
              {i < c.origin_wins && <span className={styles.pipFill} data-anim="pip" />}
            </span>
          ))}
        </span>
      </div>

      <div className={styles.gain}>
        <div className={styles.gainRow}>
          <span className={styles.label}>Improvement vs V1</span>
          <strong className={negative ? styles.neg : undefined} title={`difference ${c.difference}`}>
            {formatPts(c.difference)}
          </strong>
        </div>
        <div className={styles.track} aria-hidden="true">
          <span
            className={`${styles.bar} ${negative ? styles.barNeg : ''}`}
            data-anim="bar"
            style={{ width: `${gainPct}%` }}
          />
        </div>
        <div className={styles.gainRow}>
          <span className={styles.label}>Pass bar</span>
          <strong title={`required delta ${c.required_delta}`}>{formatPts(c.required_delta)}</strong>
        </div>
        <div className={styles.track} aria-hidden="true">
          <span className={`${styles.bar} ${styles.barReq}`} style={{ width: `${reqPct}%` }} />
        </div>
      </div>
    </article>
  );
}

/**
 * "The agent deciding": cards resolve in the order given (audit order), 400 ms apart.
 * from-only WAAPI (fill: backwards) so the DOM is always the end state; returns the
 * animations so click / Esc can finish() them.
 */
function playGateSequence(row: HTMLElement): Animation[] {
  const g = MOTION.gate;
  const anims: Animation[] = [];
  const opts = (delay: number, duration: number): KeyframeAnimationOptions => ({
    delay,
    duration,
    easing: EASE_OUT_CSS,
    fill: 'backwards',
  });
  const cards = Array.from(row.querySelectorAll<HTMLElement>('[data-candidate]'));
  cards.forEach((card, i) => {
    const base = i * g.cardStaggerMs;
    const q = (name: string) => Array.from(card.querySelectorAll<HTMLElement>(`[data-anim="${name}"]`));
    q('testing').forEach((el) =>
      anims.push(
        el.animate(
          [{ opacity: 0 }, { opacity: 1, offset: 0.2 }, { opacity: 1, offset: 0.9 }, { opacity: 0 }],
          { ...opts(base, g.testingEndMs), fill: 'none' },
        ),
      ),
    );
    q('pip').forEach((el, j) =>
      anims.push(
        el.animate(
          [{ opacity: 0, transform: 'scaleX(0.4)' }, { opacity: 1, transform: 'none' }],
          opts(base + g.dotsStartMs + j * g.dotStaggerMs, g.dotDurationMs),
        ),
      ),
    );
    q('bar').forEach((el) =>
      anims.push(
        el.animate([{ transform: 'scaleX(0)' }, { transform: 'none' }], opts(base + g.barStartMs, g.barDurationMs)),
      ),
    );
    q('stamp').forEach((el) =>
      anims.push(
        el.animate(
          [{ opacity: 0, transform: 'scale(1.12)' }, { opacity: 1, transform: 'none' }],
          opts(base + g.stampStartMs, g.stampDurationMs),
        ),
      ),
    );
  });
  // Emphasis on the card selected as V2 comes last.
  row.querySelectorAll<HTMLElement>('[data-anim="ring"],[data-anim="ribbon"]').forEach((el) =>
    anims.push(el.animate([{ opacity: 0 }, { opacity: 1 }], opts(g.emphasisStartMs, g.emphasisDurationMs))),
  );
  return anims;
}

export function GateCards({ overview }: { overview: Resource<Overview> }) {
  const audit = useAudit();
  const status = overview.status === 'error' || audit.status === 'error' ? 'error' : overview.status === 'loading' || audit.status === 'loading' ? 'loading' : 'success';
  const gate = overview.data?.revision_gate;
  const candidates = audit.data ? CANDIDATE_IDS.flatMap((id) => findCandidate(audit.data!, id) ?? []) : [];
  const selectedId = overview.data && !overview.data.v2_equals_v1 ? overview.data.selected_policy_id : null;
  const firstHl10Id = candidates.find((c) => (CANDIDATE_DESCRIPTIONS[c.candidate_id] ?? '').includes('hl10'))?.candidate_id;

  // The wrapper is always mounted (DataState swaps its children), so the observer can attach immediately.
  const [wrapRef, inView] = useInViewOnce<HTMLDivElement>({ threshold: MOTION.gate.inViewThreshold });
  const rowRef = useRef<HTMLDivElement | null>(null);
  const playedRef = useRef(false);
  const animsRef = useRef<Animation[]>([]);
  const hasCards = candidates.length > 0 && status === 'success';

  useLayoutEffect(() => {
    const row = rowRef.current;
    if (!inView || !hasCards || playedRef.current || !row) return;
    playedRef.current = true;
    if (prefersReducedMotion() || typeof row.animate !== 'function') return;
    animsRef.current = playGateSequence(row);
  }, [inView, hasCards]);

  const skip = () => {
    for (const a of animsRef.current) {
      if (a.playState === 'running') a.finish();
    }
    animsRef.current = [];
  };

  // Esc skips the sequence; a click anywhere in the section (below) does too. Neither blocks interaction.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') skip();
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      skip();
    };
  }, []);

  return (
    <Section
      id="agent-decision"
      variant="supporting"
      title={`The agent tested ${candidates.length || 'four'} revisions against V1`}
      description={
        gate ? (
          <>
            A candidate passes only if it wins ≥{gate.min_origin_wins} of {gate.n_origins} validation origins and improves
            the pooled score by ≥{gate.min_improvement_in_se} <Term id="bootstrap_se">bootstrap SE</Term>.
          </>
        ) : undefined
      }
    >
      <div ref={wrapRef} onClickCapture={skip}>
      <p className={styles.explainer}>{GATE_EXPLAINER}</p>
      <DataState
        status={status}
        errorMessage={audit.error?.message ?? overview.error?.message}
        onRetry={() => {
          if (overview.status === 'error') overview.reload();
          if (audit.status === 'error') audit.reload();
        }}
        empty={status === 'success' && candidates.length === 0}
        emptyMessage="No candidate tests recorded yet"
        loadingLabel="Loading agent decision"
        minHeight={280}
      >
        <div className={styles.row} ref={rowRef}>
          {candidates.map((c) => (
            <CandidateCard
              key={c.candidate_id}
              c={c}
              selected={c.candidate_id === selectedId}
              selectedId={selectedId}
              termHl10={c.candidate_id === firstHl10Id}
            />
          ))}
        </div>
        <Link to="/audit" className={styles.link}>
          See the full audit trail
          <ArrowRight size={18} weight="bold" aria-hidden="true" />
        </Link>
      </DataState>
      </div>
    </Section>
  );
}
