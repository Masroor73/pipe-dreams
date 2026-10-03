import { DataState } from '../DataState/DataState';
import type { Resource } from '../../hooks';
import type { Overview } from '../../types/api';
import { Reveal } from './Reveal';
import styles from './OverviewFooter.module.css';

export function OverviewFooter({ overview }: { overview: Resource<Overview> }) {
  const data = overview.data;
  return (
    <Reveal>
    <footer className={styles.footer}>
      <DataState
        status={overview.status}
        errorMessage={overview.error?.message}
        onRetry={overview.reload}
        loadingLabel="Loading run details"
        minHeight={80}
      >
        {data && (
          <>
            <dl className={styles.facts}>
              <div>
                <dt>Config hash</dt>
                <dd>{overview.meta?.config_hash ?? '—'}</dd>
              </div>
              <div>
                <dt>Git tag</dt>
                <dd>{data.git_tag}</dd>
              </div>
              <div>
                <dt>Git commit</dt>
                <dd>{data.git_commit}</dd>
              </div>
            </dl>
            {data.final_test_previously_viewed && (
              <p className={styles.disclosure}>
                Disclosure: the 2023–2025 final test window was viewed once before, in an earlier (flawed) audit. No
                tuning was done after the corrected result.
              </p>
            )}
          </>
        )}
      </DataState>
    </footer>
    </Reveal>
  );
}
