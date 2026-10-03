import type { ReactNode } from 'react';
import { CloudSlash } from '@phosphor-icons/react';
import { useHealth } from '../../hooks';
import styles from './AppShell.module.css';

/** Renders children only when /api/health reports loaded artifacts. */
export function HealthGate({ children }: { children: ReactNode }) {
  const health = useHealth();

  if (health.status === 'loading') {
    return (
      <div className={styles.gate} role="status" aria-busy="true">
        <p>Connecting to the API…</p>
      </div>
    );
  }

  if (health.status === 'error') {
    return (
      <div className={styles.gate} role="alert">
        <CloudSlash size={40} weight="duotone" aria-hidden="true" />
        <h1>Artifacts unavailable</h1>
        <p>The API could not be reached: {health.error?.message}</p>
        <button type="button" className={styles.gateButton} onClick={health.reload}>
          Retry
        </button>
      </div>
    );
  }

  const h = health.data;
  if (!h || h.status !== 'ok' || !h.artifacts_loaded) {
    return (
      <div className={styles.gate} role="alert">
        <CloudSlash size={40} weight="duotone" aria-hidden="true" />
        <h1>Artifacts unavailable</h1>
        <p>
          The API is running but its artifacts did not load (status: {h?.status ?? 'unknown'}, artifacts loaded:{' '}
          {String(h?.artifacts_loaded ?? false)}).
        </p>
        {h && (
          <p>
            Artifact directory: <code>{h.artifact_dir}</code>
          </p>
        )}
        <button type="button" className={styles.gateButton} onClick={health.reload}>
          Retry
        </button>
      </div>
    );
  }

  return <>{children}</>;
}
