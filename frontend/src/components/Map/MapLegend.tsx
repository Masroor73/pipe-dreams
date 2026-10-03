import { CONFIDENCE_COLORS, CONFIDENCE_LABELS, CONFIDENCE_ORDER } from '../../config/map';
import type { PlanId } from '../../types/api';
import styles from './Map.module.css';

export function MapLegend({ count, plan }: { count: number; plan: PlanId }) {
  return (
    <section className={`${styles.card} ${styles.legend}`} aria-label="Map legend">
      <h2 className={styles.cardTitle}>Evidence confidence</h2>
      <ul className={styles.legendList}>
        {CONFIDENCE_ORDER.map((c) => (
          <li key={c}>
            <span className={styles.swatch} style={{ background: CONFIDENCE_COLORS[c] }} aria-hidden="true" />
            {CONFIDENCE_LABELS[c]}
          </li>
        ))}
      </ul>
      <p className={styles.legendCount}>
        {count} selected segments · plan {plan.toUpperCase()}
      </p>
      <p className={styles.note}>Evidence confidence ≠ failure probability.</p>
    </section>
  );
}
