import { useLayoutEffect, useRef } from 'react';
import { ArrowDown, ArrowRight, ArrowUp } from '@phosphor-icons/react';
import { DataState } from '../DataState/DataState';
import { Section } from '../Section/Section';
import { DEMO_CARD_COUNT } from '../../config/display';
import { useRankChanges } from '../../hooks';
import { useAssetLink } from '../../hooks/useAssetLink';
import { formatRankShift } from '../../lib/format';
import { prefersReducedMotion, useInViewOnce } from '../../hooks/motion';
import { EASE_OUT_CSS, MOTION } from '../../hooks/overviewMotion';
import type { RankChange } from '../../types/api';
import styles from './RankChangeCards.module.css';

/** Arrow slides in (translateX 8px + opacity), staggered per card; from-only so the end state is the DOM state. */
function useArrowSlide(index: number) {
  const [ref, inView] = useInViewOnce<HTMLLIElement>({ threshold: 0.4 });
  const arrowRef = useRef<HTMLSpanElement | null>(null);
  useLayoutEffect(() => {
    const el = arrowRef.current;
    if (!inView || !el || prefersReducedMotion() || typeof el.animate !== 'function') return;
    el.animate(
      [
        { opacity: 0, transform: `translateX(${MOTION.rank.arrowOffsetPx}px)` },
        { opacity: 1, transform: 'none' },
      ],
      {
        duration: MOTION.rank.durationMs,
        delay: index * MOTION.rank.staggerMs,
        easing: EASE_OUT_CSS,
        fill: 'backwards',
      },
    );
  }, [inView, index]);
  return { ref, arrowRef };
}

function RankCard({ c, index, onOpen }: { c: RankChange; index: number; onOpen: (id: string) => void }) {
  const { ref, arrowRef } = useArrowSlide(index);
  const rose = c.delta_rank < 0;
  const fell = c.delta_rank > 0;
  const actionChanged = c.action_v1 !== c.action_v2;
  return (
    <li ref={ref}>
      <button type="button" className={styles.card} aria-label={`Open asset ${c.asset_id}`} onClick={() => onOpen(c.asset_id)}>
        <span className={styles.asset}>{c.asset_id}</span>
        <span className={styles.ranks}>
          {/* Ranks are ordinal: no count-up through ranks that never existed; the arrow carries the motion. */}
          <span className={styles.rankNum}>{`#${c.rank_v1} → #${c.rank_v2}`}</span>
          <span
            ref={arrowRef}
            className={`${styles.delta} ${rose ? styles.rose : styles.fell}`}
            title={rose ? 'Moved up' : fell ? 'Moved down' : 'No change'}
          >
            {rose && <ArrowUp size={20} weight="bold" aria-label="Moved up" />}
            {fell && <ArrowDown size={20} weight="bold" aria-label="Moved down" />}
            {!rose && !fell && <ArrowRight size={20} weight="bold" aria-label="No change" />}
            {formatRankShift(c.delta_rank)}
          </span>
        </span>
        <span className={`${styles.actions} ${actionChanged ? styles.actionChanged : ''}`}>
          {c.action_v1} <ArrowRight size={16} weight="bold" aria-hidden="true" /> {c.action_v2}
        </span>
        <span className={styles.reasons}>
          {c.reason_1 && <span>{c.reason_1}</span>}
          {c.reason_2 && <span>{c.reason_2}</span>}
        </span>
      </button>
    </li>
  );
}

export function RankChangeCards() {
  const changes = useRankChanges({ demo_only: true, limit: DEMO_CARD_COUNT });
  const openAsset = useAssetLink();
  const items = (changes.data?.items ?? []).slice(0, DEMO_CARD_COUNT);

  return (
    <Section
      id="rank-changes"
      variant="supporting"
      title="How V2 moved the ranking"
      description="Assets whose priority rank changed most between V1 and V2. Select one to see why."
    >
      <DataState
        status={changes.status}
        errorMessage={changes.error?.message}
        onRetry={changes.reload}
        empty={changes.status === 'success' && items.length === 0}
        emptyMessage="No rank changes to show."
        loadingLabel="Loading rank changes"
        minHeight={220}
      >
        <ul className={styles.row}>
          {items.map((c, i) => (
            <RankCard key={c.asset_id} c={c} index={i} onOpen={openAsset} />
          ))}
        </ul>
      </DataState>
    </Section>
  );
}
