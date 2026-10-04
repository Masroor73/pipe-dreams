import { useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { GLOSSARY_BY_ID, GLOSSARY_PATH } from '../../config/glossary';
import type { GlossaryId } from '../../config/glossary';
import styles from './Term.module.css';

export interface TermProps {
  id: GlossaryId;
  /** Visible text; defaults to the glossary term. */
  children?: ReactNode;
}

/**
 * Inline glossary term. A button with a dotted underline toggles a small popover
 * with the plain-English definition (hover / focus also reveal it on pointer devices).
 * Esc or clicking elsewhere closes it. Text comes only from config/glossary.ts.
 */
export function Term({ id, children }: TermProps) {
  const entry = GLOSSARY_BY_ID[id];
  const [open, setOpen] = useState(false);
  const popId = useId();
  const wrapRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    const onDown = (e: PointerEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onDown);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onDown);
    };
  }, [open]);

  return (
    <span className={styles.wrap} ref={wrapRef} data-open={open || undefined}>
      <button
        type="button"
        className={styles.term}
        aria-expanded={open}
        aria-controls={popId}
        aria-describedby={popId}
        onClick={() => setOpen((o) => !o)}
      >
        {children ?? entry.term}
      </button>
      <span id={popId} role="tooltip" className={styles.pop}>
        <span className={styles.popTerm}>{entry.term}</span>
        <span className={styles.popText}>{entry.short}</span>
        <Link to={`${GLOSSARY_PATH}#${id}`} className={styles.popLink} tabIndex={open ? 0 : -1}>
          Glossary
        </Link>
      </span>
    </span>
  );
}
