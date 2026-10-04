import { useEffect } from 'react';
import { useLocation } from 'react-router';
import { GLOSSARY } from '../config/glossary';
import styles from './GlossaryPage.module.css';

/** Every glossary entry from config/glossary.ts, with its doc source. */
export default function GlossaryPage() {
  const { hash } = useLocation();
  useEffect(() => {
    if (!hash) return;
    const el = document.getElementById(decodeURIComponent(hash.slice(1)));
    if (el && typeof el.scrollIntoView === 'function') el.scrollIntoView({ block: 'start' });
  }, [hash]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Glossary</h1>
        <p className={styles.intro}>Plain-English meanings of the terms used in this prototype.</p>
      </header>
      <dl className={styles.list}>
        {GLOSSARY.map((g) => (
          <div key={g.id} id={g.id} className={`${styles.entry} ${hash === `#${g.id}` ? styles.target : ''}`}>
            <dt className={styles.term}>{g.term}</dt>
            <dd className={styles.def}>
              <p>{g.short}</p>
              {g.more && <p className={styles.more}>{g.more}</p>}
              <p className={styles.source}>Source: {g.source}</p>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
