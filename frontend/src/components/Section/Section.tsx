import type { ReactNode } from 'react';
import styles from './Section.module.css';

export interface SectionProps {
  title: string;
  eyebrow?: string;
  description?: ReactNode;
  actions?: ReactNode;
  id?: string;
  children?: ReactNode;
  /** "supporting" is a quieter, tighter section (smaller title, less space). */
  variant?: 'default' | 'supporting';
}

export function Section({ title, eyebrow, description, actions, id, children, variant = 'default' }: SectionProps) {
  const headingId = id ? `${id}-heading` : undefined;
  return (
    <section
      id={id}
      className={variant === 'supporting' ? `${styles.section} ${styles.supporting}` : styles.section}
      aria-labelledby={headingId}
    >
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
