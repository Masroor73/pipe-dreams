import { useAudit } from '../hooks';
import { DataState } from '../components/DataState/DataState';
import { AuditTimeline } from '../components/Audit/AuditTimeline';
import styles from './AuditPage.module.css';

export default function AuditPage() {
  const { status, data, error, reload } = useAudit();
  const events = data?.events ?? [];

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
        <AuditTimeline events={events} />
      </DataState>
    </div>
  );
}
