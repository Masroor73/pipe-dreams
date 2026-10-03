import { Warning } from '@phosphor-icons/react';
import { useIsSynthetic } from '../../lib/synthetic';
import styles from './AppShell.module.css';

/** Persistent banner; visible whenever any loaded response is synthetic / placeholder. */
export function SyntheticBanner() {
  const synthetic = useIsSynthetic();
  if (!synthetic) return null;
  return (
    <div className={styles.banner} role="status">
      <Warning size={20} weight="fill" aria-hidden="true" />
      <span>SYNTHETIC / PLACEHOLDER DATA — not real results</span>
    </div>
  );
}
