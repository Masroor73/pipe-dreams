import { Link } from 'react-router';
import { ArrowRight } from '@phosphor-icons/react';
import { DataState } from '../DataState/DataState';
import { DecisionPill, Pill } from '../Pill/Pill';
import { Section } from '../Section/Section';
import { CANDIDATE_DESCRIPTIONS, CANDIDATE_IDS } from '../../config/display';
import { useAudit } from '../../hooks';
import type { Resource } from '../../hooks';
import { formatSigned } from '../../lib/format';
import type { Audit, CandidateResult, Overview, PolicyId } from '../../types/api';
import styles from './GateCards.module.css';

/** Select the recorded result for a candidate: last ACCEPT/REJECT event, else last TEST_CANDIDATE. */
export function findCandidate(audit: Audit, id: PolicyId): CandidateResult | undefined {
  const withCandidate = audit.events.filter((e) => e.candidate?.candidate_id === id);
  const decided = withCandidate.filter((e) => e.event_type === 'ACCEPT' || e.event_type === 'REJECT');
  const pick = decided.length > 0 ? decided : withCandidate.filter((e) => e.event_type === 'TEST_CANDIDATE');
  return pick[pick.length - 1]?.candidate ?? undefined;
}

function CandidateCard({ c, selected }: { c: CandidateResult; selected: boolean }) {
  // Visual scaling of the two given numbers only.
  const scale = Math.max(Math.abs(c.difference), Math.abs(c.required_delta), 1e-9);
  const gainPct = (Math.max(c.difference, 0) / scale) * 100;
  const reqPct = (Math.max(c.required_delta, 0) / scale) * 100;
  const negative = c.difference < 0;

  return (
    <article className={`${styles.card} ${selected ? styles.selected : ''}`} data-candidate={c.candidate_id}>
      <header className={styles.cardHead}>
        <h3>{c.candidate_id}</h3>
        <DecisionPill decision={c.decision} />
      </header>
      <p className={styles.desc}>{CANDIDATE_DESCRIPTIONS[c.candidate_id] ?? ''}</p>
      {selected && (
        <div>
          <Pill tone="accent">Selected as V2</Pill>
        </div>
      )}

      <div className={styles.wins}>
        <span className={styles.label}>
          Origin wins{' '}
          <strong>
            {c.origin_wins}/{c.n_origins}
          </strong>
        </span>
        <span className={styles.pips} aria-hidden="true">
          {Array.from({ length: c.n_origins }, (_, i) => (
            <span key={i} className={i < c.origin_wins ? styles.pipOn : styles.pip} />
          ))}
        </span>
      </div>

      <div className={styles.gain}>
        <div className={styles.gainRow}>
          <span className={styles.label}>Pooled gain</span>
          <strong className={negative ? styles.neg : undefined}>{formatSigned(c.difference)}</strong>
        </div>
        <div className={styles.track} aria-hidden="true">
          <span className={`${styles.bar} ${negative ? styles.barNeg : ''}`} style={{ width: `${gainPct}%` }} />
        </div>
        <div className={styles.gainRow}>
          <span className={styles.label}>Required</span>
          <strong>{formatSigned(c.required_delta)}</strong>
        </div>
        <div className={styles.track} aria-hidden="true">
          <span className={`${styles.bar} ${styles.barReq}`} style={{ width: `${reqPct}%` }} />
        </div>
      </div>

      <p className={styles.reason}>{c.reason}</p>
    </article>
  );
}

export function GateCards({ overview }: { overview: Resource<Overview> }) {
  const audit = useAudit();
  const status = overview.status === 'error' || audit.status === 'error' ? 'error' : overview.status === 'loading' || audit.status === 'loading' ? 'loading' : 'success';
  const gate = overview.data?.revision_gate;
  const candidates = audit.data ? CANDIDATE_IDS.flatMap((id) => findCandidate(audit.data!, id) ?? []) : [];
  const selectedId = overview.data && !overview.data.v2_equals_v1 ? overview.data.selected_policy_id : null;

  return (
    <Section
      id="agent-decision"
      eyebrow="Agent decision"
      title={`The agent tested ${candidates.length || 'four'} revisions against V1`}
      description={
        gate
          ? `Accept only if a candidate wins ≥${gate.min_origin_wins} of ${gate.n_origins} validation origins and improves the pooled score by ≥${gate.min_improvement_in_se} bootstrap SE.`
          : undefined
      }
    >
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
        <div className={styles.row}>
          {candidates.map((c) => (
            <CandidateCard key={c.candidate_id} c={c} selected={c.candidate_id === selectedId} />
          ))}
        </div>
        <Link to="/audit" className={styles.link}>
          See the full audit trail
          <ArrowRight size={18} weight="bold" aria-hidden="true" />
        </Link>
      </DataState>
    </Section>
  );
}
