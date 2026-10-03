import { useEscalations } from '../hooks';
import { DataState } from '../components/DataState/DataState';
import { EscalationTable } from '../components/Escalation/EscalationTable';
import styles from './EscalationPage.module.css';

export default function EscalationPage() {
  const { status, data, error, reload } = useEscalations();
  const items = data?.items ?? [];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Escalation</h1>
        <p className={styles.intro}>
          In-dataset assets that need human review before action. VERIFY / ESCALATE are governance rules, not
          validated predictions.
        </p>
      </header>
      <DataState
        status={status}
        errorMessage={error?.message}
        onRetry={reload}
        empty={status === 'success' && items.length === 0}
        emptyMessage="No assets are escalated."
        loadingLabel="Loading escalations"
        minHeight={280}
      >
        <p className={styles.count}>{items.length} assets escalated</p>
        <EscalationTable items={items} />
      </DataState>
    </div>
  );
}
