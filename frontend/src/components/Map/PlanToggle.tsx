import type { PlanId } from '../../types/api';
import styles from './Map.module.css';

const PLANS: PlanId[] = ['v1', 'v2'];

export function PlanToggle({ plan, onChange }: { plan: PlanId; onChange: (p: PlanId) => void }) {
  return (
    <div className={`${styles.card} ${styles.toggleCard}`}>
      <span className={styles.cardTitle} id="plan-toggle-label">
        Plan
      </span>
      <div className={styles.segmented} role="group" aria-labelledby="plan-toggle-label">
        {PLANS.map((p) => (
          <button
            key={p}
            type="button"
            className={`${styles.segment} ${p === plan ? styles.segmentActive : ''}`}
            aria-pressed={p === plan}
            onClick={() => onChange(p)}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}
