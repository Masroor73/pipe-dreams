import { useState } from 'react';
import type { CSSProperties } from 'react';
import { CaretDown } from '@phosphor-icons/react';
import {
  COMMUNITY_COLOR,
  CONFIDENCE_COLORS,
  CONFIDENCE_MEANINGS,
  CONFIDENCE_ORDER,
  FIT_COMPACT_BELOW_PX,
  MUTED_COLOR,
  LEGEND_COLLAPSE_BELOW_HEIGHT_PX,
  OPEN_PIPE_COLOR,
} from '../../config/map';
import { Term } from '../Term/Term';
import type { PlanId } from '../../types/api';
import styles from './Map.module.css';

/** Starts collapsed on narrow or short screens so the legend never covers much of the map. */
function startsOpen(): boolean {
  if (typeof window.matchMedia !== 'function') return true;
  return !window.matchMedia(`(max-width: ${FIT_COMPACT_BELOW_PX}px), (max-height: ${LEGEND_COLLAPSE_BELOW_HEIGHT_PX}px)`).matches;
}

export interface MapLegendProps {
  plan: PlanId;
  /** Selected-segment count line (shown on /map). */
  count?: number;
  /** Grey pipes (in the community, not selected) are drawn. */
  showMuted?: boolean;
  /** A pipe is open in the detail panel. */
  showOpen?: boolean;
  /** A community polygon is selected. */
  showCommunity?: boolean;
}

function Swatch({ color, kind }: { color: string; kind?: 'open' | 'poly' }) {
  const cls = [styles.swatch, kind === 'open' ? styles.swatchOpen : '', kind === 'poly' ? styles.swatchPoly : '']
    .filter(Boolean)
    .join(' ');
  return <span className={cls} style={{ '--sw': color } as CSSProperties} data-color={color} aria-hidden="true" />;
}

/** One legend for every pipe map. Colours come from config/map.ts, the same constants the map layers use. */
export function MapLegend({ plan, count, showMuted = false, showOpen = false, showCommunity = false }: MapLegendProps) {
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
          Map legend
          <CaretDown size={16} weight="bold" aria-hidden="true" className={open ? styles.caretOpen : styles.caret} />
        </button>
      </h2>
      <div id="map-legend-body" className={open ? undefined : styles.legendHidden}>
        <p className={styles.legendTitle}>
          Pipes selected for inspection (plan {plan.toUpperCase()}), coloured by{' '}
          <Term id="evidence_confidence">evidence confidence</Term>
        </p>
        <ul className={styles.legendList} aria-label="Evidence confidence">
          {CONFIDENCE_ORDER.map((c) => (
            <li key={c}>
              <Swatch color={CONFIDENCE_COLORS[c]} />
              <span>
                <strong>{c}</strong>: {CONFIDENCE_MEANINGS[c]}
              </span>
            </li>
          ))}
          {showMuted && (
            <li>
              <Swatch color={MUTED_COLOR} />
              <span>In community, not selected for inspection</span>
            </li>
          )}
          {showOpen && (
            <li>
              <Swatch color={OPEN_PIPE_COLOR} kind="open" />
              <span>Pipe open in the detail panel</span>
            </li>
          )}
          {showCommunity && (
            <li>
              <Swatch color={COMMUNITY_COLOR} kind="poly" />
              <span>Selected community</span>
            </li>
          )}
        </ul>
        {count !== undefined && (
          <p className={styles.legendCount}>
            {count} selected segments · plan {plan.toUpperCase()}
          </p>
        )}
        <p className={styles.note}>Confidence is how much we trust the data behind a pipe&apos;s ranking, not failure probability.</p>
      </div>
    </section>
  );
}
