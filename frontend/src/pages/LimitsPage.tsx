import { useDataQuality, useNotCovered } from '../hooks';
import { DataState } from '../components/DataState/DataState';
import { Section } from '../components/Section/Section';
import { NotCoveredList } from '../components/Limits/NotCoveredList';
import { DataQualityPanel } from '../components/Limits/DataQualityPanel';
import styles from './LimitsPage.module.css';

export default function LimitsPage() {
  const nc = useNotCovered();
  const dq = useDataQuality();
  const items = nc.data?.items ?? [];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Limits</h1>
        <p className={styles.intro}>What the prototype leaves out, and how complete the underlying data is.</p>
      </header>
      <Section title="What this prototype does not cover" id="not-covered">
        <DataState
          status={nc.status}
          errorMessage={nc.error?.message}
          onRetry={nc.reload}
          empty={nc.status === 'success' && items.length === 0}
          emptyMessage="No coverage gaps listed."
          loadingLabel="Loading coverage gaps"
        >
          <NotCoveredList items={items} />
        </DataState>
      </Section>
      <Section title="Data quality" id="data-quality">
        <DataState
          status={dq.status}
          errorMessage={dq.error?.message}
          onRetry={dq.reload}
          loadingLabel="Loading data quality"
        >
          {dq.data && <DataQualityPanel data={dq.data} />}
        </DataState>
      </Section>
    </div>
  );
}
