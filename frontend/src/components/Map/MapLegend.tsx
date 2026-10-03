import { useState } from 'react';
import { CaretDown } from '@phosphor-icons/react';
import { CONFIDENCE_COLORS, CONFIDENCE_LABELS, CONFIDENCE_ORDER, FIT_COMPACT_BELOW_PX } from '../../config/map';
import type { PlanId } from '../../types/api';
import styles from './Map.module.css';

/** Starts collapsed on narrow screens so the legend never covers much of the map. */
function startsOpen(): boolean {
  return typeof window.matchMedia !== 'function' || !window.matchMedia(`(max-width: ${FIT_COMPACT_BELOW_PX}px)`).matches;
}

export function MapLegend({ count, plan }: { count: number; plan: PlanId }) {
  const [open, setOpen] = useState(startsOpen);
  return (
    <section className={`${styles.card} ${styles.legend}`} aria-label="Map legend">
      <h2 className={styles.cardTitle}>
        <button
          type="button"
          className={styles.legendToggle}
          aria-expanded={open}
          aria-controls="map-legend-body"
          onClick={() => setOpen((o) => !o)}
        >
          Evidence confidence
          <CaretDown size={16} weight="bold" aria-hidden="true" className={open ? styles.caretOpen : styles.caret} />
        </button>
      </h2>
      <div id="map-legend-body" className={open ? undefined : styles.legendHidden}>
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
      </div>
    </section>
  );
}
