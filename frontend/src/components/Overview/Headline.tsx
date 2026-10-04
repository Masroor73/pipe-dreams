import type { ReactNode } from 'react';
import { DataState } from '../DataState/DataState';
import { Pill } from '../Pill/Pill';
import { Term } from '../Term/Term';
import { CANDIDATE_DESCRIPTIONS, CANDIDATE_IDS, HEADLINE_BUDGET_PCT, headlineCaption } from '../../config/display';
import { formatPct, formatSigned } from '../../lib/format';
import { useAudit } from '../../hooks';
import { findCandidate } from './GateCards';
import type { Resource } from '../../hooks';
import type { Overview, SeriesRow } from '../../types/api';
import { AnimatedValue } from './AnimatedValue';
import styles from './Headline.module.css';

/** Final-split row for a policy at the headline budget (selection only). */
function findFinalRow(series: SeriesRow[], policyId: string): SeriesRow | undefined {
  return series.find(
    (r) => r.split === 'final' && r.policy_id === policyId && r.budget_pct === HEADLINE_BUDGET_PCT && r.asset_capture !== null,
  );
}

/** Same formatter as the static values in the meta line. */
const formatPct0 = (n: number) => formatPct(n, 0);

/** Wrap the first "hl10" in a candidate description with its glossary term. */
function describeCandidate(text: string): ReactNode {
  const [before, ...rest] = text.split('hl10');
  if (rest.length === 0) return text;
  return (
    <>
      {before}
      <Term id="hl10">hl10</Term>
      {rest.join('hl10')}
    </>
  );
}

export function Headline({ overview }: { overview: Resource<Overview> }) {
  const data = overview.data;
  const selectedRow = data ? findFinalRow(data.series, data.selected_policy_id) : undefined;
  const baselineRow = data ? findFinalRow(data.series, 'count_only') : undefined;
  const hasFinal = !!data && data.series.some((r) => r.split === 'final');
  const missing = !selectedRow || !baselineRow;

  return (
    <div className={styles.headline}>
      <DataState
        status={overview.status}
        errorMessage={overview.error?.message}
        onRetry={overview.reload}
        empty={overview.status === 'success' && (!hasFinal || missing)}
        emptyMessage="Final-test results not available yet"
        loadingLabel="Loading headline result"
        minHeight={260}
      >
        {data && selectedRow && baselineRow && (
          <div className={styles.panel} data-focal="headline">
            <div className={styles.result}>
              <div className={styles.figures}>
                <div className={`${styles.figure} ${styles.primary}`}>
                  <AnimatedValue
                    key={selectedRow.asset_capture}
                    className={styles.number}
                    value={selectedRow.asset_capture!}
                    format={formatPct0}
                  />
                  <span className={styles.figureLabel}>
                    {data.v2_equals_v1 ? (
                      <>
                        <Term id="v1">V1</Term> (retained)
                      </>
                    ) : (
                      <>
                        <Term id="v2">V2</Term> ({data.selected_policy_id})
                      </>
                    )}
                  </span>
                </div>
                <span className={styles.versus}>vs</span>
                <div className={`${styles.figure} ${styles.baseline}`}>
                  <AnimatedValue className={styles.number} value={baselineRow.asset_capture!} format={formatPct0} />
                  <span className={styles.figureLabel}>
                    <Term id="count_only">count-only</Term>
                  </span>
                </div>
              </div>
              <p className={styles.figureCaption}>{headlineCaption(HEADLINE_BUDGET_PCT)}</p>
              <p className={styles.meta}>
                Final test 2023–2025 · {data.selected_policy_id} 95% CI {formatPct(selectedRow.ci_low, 0)}–
                {formatPct(selectedRow.ci_high, 0)} · count-only {formatPct(baselineRow.ci_low, 0)}–
                {formatPct(baselineRow.ci_high, 0)}
              </p>
            </div>

            <div className={styles.decision}>
              {data.v2_equals_v1 ? (
                <>
                  <Pill tone="neutral">V1 retained</Pill>
                  <p className={styles.decisionTitle}>
                    No candidate passed the <Term id="revision_gate">revision gate</Term>
                  </p>
                  <RefusalReasons />
                </>
              ) : (
                <>
                  <Pill tone="accent">V2 = {data.selected_policy_id}</Pill>
                  <p className={styles.decisionTitle}>
                    Selected by the <Term id="revision_gate">revision gate</Term>
                  </p>
                  <p className={styles.decisionDesc}>
                    {data.selected_policy_id}: {describeCandidate(CANDIDATE_DESCRIPTIONS[data.selected_policy_id] ?? '')}
                  </p>
                </>
              )}
            </div>
          </div>
        )}
      </DataState>
    </div>
  );
}

/**
 * "The agent refused to change": when V2 = V1, list why each candidate failed the gate.
 * Every value is the logged gate result from /api/audit; nothing is re-evaluated here.
 */
function RefusalReasons() {
  const audit = useAudit();
  if (!audit.data) return null;
  const rows = CANDIDATE_IDS.flatMap((id) => {
    const c = findCandidate(audit.data!, id);
    return c ? [c] : [];
  });
  if (rows.length === 0) return null;
  return (
    <ul className={styles.refusals} aria-label="Why each candidate was rejected">
      {rows.map((c) => (
        <li key={c.candidate_id}>
          <span className={styles.refusalId}>{c.candidate_id}</span> won {c.origin_wins}/{c.n_origins} origins · gain{' '}
          {formatSigned(c.difference)} (needs {formatSigned(c.required_delta)}) · {c.reason}
        </li>
      ))}
    </ul>
  );
}
