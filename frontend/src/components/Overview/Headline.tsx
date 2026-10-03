import { DataState } from '../DataState/DataState';
import { Pill } from '../Pill/Pill';
import { HEADLINE_BUDGET_PCT } from '../../config/display';
import { formatPct } from '../../lib/format';
import type { Resource } from '../../hooks';
import type { Overview, SeriesRow } from '../../types/api';
import styles from './Headline.module.css';

/** Final-split row for a policy at the headline budget (selection only). */
function findFinalRow(series: SeriesRow[], policyId: string): SeriesRow | undefined {
  return series.find(
    (r) => r.split === 'final' && r.policy_id === policyId && r.budget_pct === HEADLINE_BUDGET_PCT && r.asset_capture !== null,
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
          <>
            {data.v2_equals_v1 ? (
              <p className={styles.kicker}>
                <Pill tone="neutral">V1 retained</Pill>
                <span>No candidate passed the revision gate</span>
              </p>
            ) : (
              <p className={styles.kicker}>
                <Pill tone="accent">
                  V2 = {data.selected_policy_id}
                </Pill>
                <span>Selected by the revision gate</span>
              </p>
            )}
            {/* Figures are aria-hidden: the sentence below carries the same values for screen readers. */}
            <div className={styles.figures} aria-hidden="true">
              <div className={`${styles.figure} ${styles.primary}`}>
                <span className={styles.number} key={selectedRow.asset_capture}>
                  {formatPct(selectedRow.asset_capture, 0)}
                </span>
                <span className={styles.figureLabel}>
                  {data.v2_equals_v1 ? 'V1 (retained)' : `V2 (${data.selected_policy_id})`}
                </span>
              </div>
              <span className={styles.versus}>vs</span>
              <div className={`${styles.figure} ${styles.baseline}`}>
                <span className={styles.number}>{formatPct(baselineRow.asset_capture, 0)}</span>
                <span className={styles.figureLabel}>count-only</span>
              </div>
              <p className={styles.figureCaption}>
                Share of future breaking assets caught at a {HEADLINE_BUDGET_PCT}% length budget
              </p>
            </div>
            <p className={styles.copy}>
              {data.v2_equals_v1 ? (
                <>
                  V1 retained — no candidate passed the revision gate. V1 catches{' '}
                  <strong>{formatPct(selectedRow.asset_capture, 0)}</strong> of future breaking assets at a{' '}
                  {HEADLINE_BUDGET_PCT}% length budget, vs <strong>{formatPct(baselineRow.asset_capture, 0)}</strong> for count-only.
                </>
              ) : (
                <>
                  V2 catches <strong>{formatPct(selectedRow.asset_capture, 0)}</strong> of future breaking assets at a{' '}
                  {HEADLINE_BUDGET_PCT}% length budget, vs <strong>{formatPct(baselineRow.asset_capture, 0)}</strong> for count-only.
                </>
              )}
            </p>
            <p className={styles.meta}>
              Final test 2023–2025 · {data.selected_policy_id} 95% CI {formatPct(selectedRow.ci_low, 0)}–
              {formatPct(selectedRow.ci_high, 0)} · count-only {formatPct(baselineRow.ci_low, 0)}–
              {formatPct(baselineRow.ci_high, 0)}
            </p>
          </>
        )}
      </DataState>
    </div>
  );
}
