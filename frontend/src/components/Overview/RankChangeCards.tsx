import { ArrowDown, ArrowRight, ArrowUp } from '@phosphor-icons/react';
import { DataState } from '../DataState/DataState';
import { Section } from '../Section/Section';
import { DEMO_CARD_COUNT } from '../../config/display';
import { useRankChanges } from '../../hooks';
import { useAssetLink } from '../../hooks/useAssetLink';
import { formatDelta } from '../../lib/format';
import styles from './RankChangeCards.module.css';

export function RankChangeCards() {
  const changes = useRankChanges({ demo_only: true, limit: DEMO_CARD_COUNT });
  const openAsset = useAssetLink();
  const items = (changes.data?.items ?? []).slice(0, DEMO_CARD_COUNT);

  return (
    <Section
      id="rank-changes"
      eyebrow="What changed"
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
          {items.map((c) => {
            const rose = c.delta_rank < 0;
            const fell = c.delta_rank > 0;
            const actionChanged = c.action_v1 !== c.action_v2;
            return (
              <li key={c.asset_id}>
                <button
                  type="button"
                  className={styles.card}
                  aria-label={`Open asset ${c.asset_id}`}
                  onClick={() => openAsset(c.asset_id)}
                >
                  <span className={styles.asset}>{c.asset_id}</span>
                  <span className={styles.ranks}>
                    <span className={styles.rankNum}>
                      {`#${c.rank_v1} → #${c.rank_v2}`}
                    </span>
                    <span className={`${styles.delta} ${rose ? styles.rose : styles.fell}`}>
                      {rose && <ArrowUp size={18} weight="bold" aria-hidden="true" />}
                      {fell && <ArrowDown size={18} weight="bold" aria-hidden="true" />}
                      {formatDelta(c.delta_rank)}
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
          })}
        </ul>
      </DataState>
    </Section>
  );
}
