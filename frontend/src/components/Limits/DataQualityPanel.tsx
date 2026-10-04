import type { ReactNode } from 'react';
import { Term } from '../Term/Term';
import type { DataQuality } from '../../types/api';
import { formatNumber, formatPct } from '../../lib/format';
import styles from './Limits.module.css';

function Stat({ value, label }: { value: string; label: ReactNode }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statValue}>{value}</span>
      <span className={styles.statLabel}>{label}</span>
    </div>
  );
}

/** Keys verbatim, order as given, bar width is the supplied value in [0, 1]. */
function Bars({ title, values }: { title: string; values: Record<string, number> }) {
  return (
    <figure className={styles.bars}>
      <figcaption className={styles.barsTitle}>{title}</figcaption>
      <ul className={styles.barList}>
        {Object.entries(values).map(([k, v]) => (
          <li key={k} className={styles.barRow}>
            <span className={styles.barKey}>{k}</span>
            <span className={styles.track} aria-hidden="true">
              <span className={styles.fill} style={{ width: `${Math.min(Math.max(v, 0), 1) * 100}%` }} />
            </span>
            <span className={styles.barVal}>{formatPct(v, 0)}</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

export function DataQualityPanel({ data }: { data: DataQuality }) {
  return (
    <div className={styles.dq}>
      <div className={styles.stats}>
        <Stat value={formatNumber(data.rows_dropped_missing_coordinates)} label="rows dropped — missing coordinates" />
        <Stat value={formatNumber(data.future_year_pipe_rows_excluded)} label="future-year pipe rows excluded" />
        <Stat value={formatNumber(data.planned_rows_excluded)} label="planned rows excluded" />
        <Stat value={formatPct(data.unreachable_final_test_share, 0)} label={<><Term id="reachable_share">unreachable</Term> final-test share</>} />
      </div>
      <div className={styles.sens}>
        <h3 className={styles.subTitle}>
          Inactive-pipe sensitivity: <Term id="capture">capture</Term> at 5% <Term id="length_budget">budget</Term>
        </h3>
        <div className={styles.sensPair}>
          <Stat value={formatPct(data.inactive_sensitivity.included_capture_5pct, 1)} label="inactive included" />
          <Stat value={formatPct(data.inactive_sensitivity.excluded_capture_5pct, 1)} label="inactive excluded" />
        </div>
      </div>
      <div className={styles.barGrid}>
        <Bars title="Match rate by origin" values={data.match_rate_by_origin} />
        <Bars title="Match rate by era" values={data.match_rate_by_era} />
        <Bars title="Unmatched share by era" values={data.unmatched_share_by_era} />
        <Bars title="Retired status strata" values={data.retired_status_strata} />
      </div>
      <ul className={styles.notes}>
        {data.notes.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
    </div>
  );
}
