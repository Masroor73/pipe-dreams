import { Link } from 'react-router';
import { ArrowRight } from '@phosphor-icons/react';
import { DataState } from '../DataState/DataState';
import { Section } from '../Section/Section';
import { ESCALATION_TEASER_COUNT, LIMITS_TEASER_COUNT } from '../../config/display';
import { useEscalations, useNotCovered } from '../../hooks';
import { Reveal } from './Reveal';
import styles from './Teasers.module.css';

function EscalationTeaser() {
  const esc = useEscalations();
  const items = esc.data?.items ?? [];
  return (
    <div className={styles.card}>
      <h3>Escalation</h3>
      <DataState
        status={esc.status}
        errorMessage={esc.error?.message}
        onRetry={esc.reload}
        empty={esc.status === 'success' && items.length === 0}
        emptyMessage="No assets are escalated."
        loadingLabel="Loading escalations"
        minHeight={140}
      >
        <p className={styles.count}>
          <span className={styles.big}>{items.length}</span> assets need human review
        </p>
        <ul className={styles.list}>
          {items.slice(0, ESCALATION_TEASER_COUNT).map((e) => (
            <li key={e.asset_id}>
              <span className={styles.id}>{e.asset_id}</span>
              <span>{e.escalation_reason}</span>
            </li>
          ))}
        </ul>
        <Link to="/escalation" className={styles.link}>
          Open escalation list
          <ArrowRight size={18} weight="bold" aria-hidden="true" />
        </Link>
      </DataState>
    </div>
  );
}

function LimitsTeaser() {
  const nc = useNotCovered();
  const items = nc.data?.items ?? [];
  return (
    <div className={styles.card}>
      <h3>Limits</h3>
      <DataState
        status={nc.status}
        errorMessage={nc.error?.message}
        onRetry={nc.reload}
        empty={nc.status === 'success' && items.length === 0}
        emptyMessage="No limits recorded."
        loadingLabel="Loading limits"
        minHeight={140}
      >
        <p className={styles.count}>What this analysis does not cover</p>
        <ul className={styles.list}>
          {items.slice(0, LIMITS_TEASER_COUNT).map((n) => (
            <li key={n.coverage_issue_id}>
              <span>{n.scope}</span>
            </li>
          ))}
        </ul>
        <Link to="/limits" className={styles.link}>
          See all limits
          <ArrowRight size={18} weight="bold" aria-hidden="true" />
        </Link>
      </DataState>
    </div>
  );
}

export function Teasers() {
  return (
    <Reveal>
      <Section id="teasers" variant="supporting" title="Where a human stays in the loop">
        <div className={styles.row}>
          <EscalationTeaser />
          <LimitsTeaser />
        </div>
      </Section>
    </Reveal>
  );
}
