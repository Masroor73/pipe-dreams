import { Term } from '../components/Term/Term';
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
          In-dataset assets that need human review before action. <Term id="verify_escalate">VERIFY / ESCALATE</Term>{' '}
          are governance rules, not validated predictions. Each row pairs a{' '}
          <Term id="consequence_tier">consequence tier</Term> with{' '}
          <Term id="evidence_confidence">evidence confidence</Term>.
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
