import type { NotCoveredItem } from '../../types/api';
import { Pill } from '../Pill/Pill';
import styles from './Limits.module.css';

/** Colour for known frozen severity strings only; unknown values stay neutral. */
function SeverityPill({ severity }: { severity: string }) {
  const tone = severity === 'HIGH' ? 'reject' : severity === 'MEDIUM' ? 'conf-medium' : 'neutral';
  return <Pill tone={tone}>{severity}</Pill>;
}

/** Items render in the order supplied. */
export function NotCoveredList({ items }: { items: NotCoveredItem[] }) {
  return (
    <ul className={styles.cards}>
      {items.map((it) => (
        <li key={it.coverage_issue_id} className={styles.card}>
          <div className={styles.cardHead}>
            <div className={styles.cardHeadText}>
              <h3 className={styles.cardTitle}>{it.scope}</h3>
              <span className={styles.issueId}>{it.coverage_issue_id}</span>
            </div>
            <SeverityPill severity={it.ui_severity} />
          </div>
          <p className={styles.desc}>{it.description}</p>
          <p className={styles.why}>{it.why_not_covered}</p>
          <p className={styles.need}>Would need: {it.required_evidence}</p>
          <p className={styles.note}>{it.source_note}</p>
        </li>
      ))}
    </ul>
  );
}
