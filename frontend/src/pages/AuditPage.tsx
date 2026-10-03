import { ArrowCounterClockwise, Stop } from '@phosphor-icons/react';
import { useAudit } from '../hooks';
import { useAuditReplay } from '../components/Audit/useAuditReplay';
import { DataState } from '../components/DataState/DataState';
import { AuditTimeline } from '../components/Audit/AuditTimeline';
import styles from './AuditPage.module.css';

export default function AuditPage() {
  const { status, data, error, reload } = useAudit();
  const events = data?.events ?? [];
  const replay = useAuditReplay(events);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Agent audit</h1>
        <p className={styles.intro}>
          Autonomous loop: plan → evaluate → diagnose → test candidates → accept/reject → plan V2
        </p>
        {events.length > 0 && (
          <div className={styles.replayRow}>
            <button
              type="button"
              className={styles.replayBtn}
              onClick={replay.running ? replay.stop : replay.start}
            >
              {replay.running ? (
                <Stop size={18} weight="fill" aria-hidden="true" />
              ) : (
                <ArrowCounterClockwise size={18} weight="bold" aria-hidden="true" />
              )}
              {replay.running ? 'Stop replay' : 'Replay agent run'}
            </button>
          </div>
        )}
        <div className={styles.srOnly} aria-live="polite" aria-atomic="true">
          {replay.announcement}
        </div>
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
        <AuditTimeline events={events} revealed={replay.revealed} replayOrder={replay.order} />
      </DataState>
    </div>
  );
}
