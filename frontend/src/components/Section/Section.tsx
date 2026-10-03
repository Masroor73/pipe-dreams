import type { ReactNode } from 'react';
import styles from './Section.module.css';

export interface SectionProps {
  title: string;
  eyebrow?: string;
  description?: ReactNode;
  actions?: ReactNode;
  id?: string;
  children?: ReactNode;
}

export function Section({ title, eyebrow, description, actions, id, children }: SectionProps) {
  const headingId = id ? `${id}-heading` : undefined;
  return (
    <section id={id} className={styles.section} aria-labelledby={headingId}>
      <header className={styles.header}>
        <div className={styles.titles}>
          {eyebrow && <span className={styles.eyebrow}>{eyebrow}</span>}
          <h2 id={headingId}>{title}</h2>
          {description && <p className={styles.description}>{description}</p>}
        </div>
        {actions && <div className={styles.actions}>{actions}</div>}
      </header>
      {children}
    </section>
  );
}
