import { X } from '@phosphor-icons/react';
import styles from './AssetPanel.module.css';

export interface AssetPanelProps {
  assetId: string;
  onClose: () => void;
}

/** Placeholder: Task 3 replaces the body with the V1 vs V2 detail view. */
export function AssetPanel({ assetId, onClose }: AssetPanelProps) {
  return (
    <aside className={styles.panel} aria-label="Asset detail">
      <header className={styles.header}>
        <h2>{assetId}</h2>
        <button type="button" className={styles.close} onClick={onClose} aria-label="Close asset panel">
          <X size={22} aria-hidden="true" />
        </button>
      </header>
    </aside>
  );
}
