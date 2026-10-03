import { useState } from 'react';
import { useAudit } from '../hooks';
import { DataState } from '../components/DataState/DataState';
import { AuditTimeline } from '../components/Audit/AuditTimeline';
import auditStyles from '../components/Audit/Audit.module.css';
import styles from './AuditPage.module.css';

export default function AuditPage() {
  const { status, data, error, reload } = useAudit();
  const [filter, setFilter] = useState<string | null>(null);
  const events = data?.events ?? [];
  const types = Array.from(new Set(events.map((e) => e.event_type)));
  const visible = filter ? events.filter((e) => e.event_type === filter) : events;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Agent audit</h1>
        <p className={styles.intro}>
          Autonomous loop: plan → evaluate → diagnose → test candidates → accept/reject → plan V2
        </p>
      </header>
      <DataState
        status={status}
        errorMessage={error?.message}
        onRetry={reload}
        empty={status === 'success' && events.length === 0}
        emptyMessage="No audit events recorded."
        loadingLabel="Loading audit trail"
        minHeight={320}
      >
        <div className={auditStyles.filters} role="group" aria-label="Filter by event type">
          <button
            type="button"
            className={`${auditStyles.chip} ${filter === null ? auditStyles.chipOn : ''}`}
            aria-pressed={filter === null}
            onClick={() => setFilter(null)}
          >
            All
          </button>
          {types.map((t) => (
            <button
              key={t}
              type="button"
              className={`${auditStyles.chip} ${filter === t ? auditStyles.chipOn : ''}`}
              aria-pressed={filter === t}
              onClick={() => setFilter(filter === t ? null : t)}
            >
              {t}
            </button>
          ))}
        </div>
        <AuditTimeline events={visible} />
      </DataState>
    </div>
  );
}
