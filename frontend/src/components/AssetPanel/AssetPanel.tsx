import { useEffect, useRef, useState } from 'react';
import { X } from '@phosphor-icons/react';
import { useAsset } from '../../hooks';
import { formatDelta, formatNumber } from '../../lib/format';
import type { AssetDetail, PlanFields } from '../../types/api';
import { DataState } from '../DataState/DataState';
import { ConfidencePill, Pill } from '../Pill/Pill';
import styles from './AssetPanel.module.css';

export interface AssetPanelProps {
  assetId: string;
  onClose: () => void;
  /** Controlled by the shell so the panel can slide out before unmounting. Defaults to open. */
  open?: boolean;
}

interface CompareRow {
  label: string;
  get: (f: PlanFields) => string;
}

const COMPARE_ROWS: CompareRow[] = [
  { label: 'Rank', get: (f) => String(f.rank) },
  { label: 'Selected', get: (f) => (f.selected ? 'Yes' : 'No') },
  { label: 'Priority score', get: (f) => f.priority_score.toFixed(3) },
  { label: 'Likelihood score', get: (f) => f.likelihood_score.toFixed(3) },
  { label: 'Recommended action', get: (f) => f.recommended_action },
  { label: 'Revision reason', get: (f) => f.revision_reason ?? '—' },
];

/** V1 vs V2 side by side; the V2 cell is highlighted where it differs from V1. */
function PlanComparison({ v1, v2 }: { v1: PlanFields; v2: PlanFields }) {
  return (
    <table className={styles.compare} aria-label="V1 and V2 plan comparison">
      <thead>
        <tr>
          <th scope="col">Field</th>
          <th scope="col">V1</th>
          <th scope="col">V2</th>
        </tr>
      </thead>
      <tbody>
        {COMPARE_ROWS.map((row) => {
          const a = row.get(v1);
          const b = row.get(v2);
          return (
            <tr key={row.label}>
              <th scope="row">{row.label}</th>
              <td>{a}</td>
              <td className={a !== b ? styles.differs : undefined}>{b}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Detail({ asset }: { asset: AssetDetail }) {
  const rc = asset.rank_change;
  return (
    <>
      <div className={styles.meta}>
        <Pill tone="neutral">{asset.consequence_tier}</Pill>
        <ConfidencePill confidence={asset.evidence_confidence} />
        <span className={styles.length}>{formatNumber(asset.length_m, 1)} m</span>
      </div>

      {rc && (
        <p className={styles.delta}>
          <strong>Rank change {formatDelta(rc.delta_rank)}</strong>
          {[rc.reason_1, rc.reason_2].filter(Boolean).map((r) => (
            <span key={r}>{r}</span>
          ))}
        </p>
      )}

      <PlanComparison v1={asset.v1} v2={asset.v2} />

      <section className={styles.evidence} aria-label="Evidence">
        <h3>Evidence</h3>
        <dl>
          <dt>Evidence basis</dt>
          <dd>{asset.evidence_basis}</dd>
          <dt>Association quality</dt>
          <dd>{asset.association_quality.toFixed(2)}</dd>
          <dt>Rank stability</dt>
          <dd>{asset.rank_stability.toFixed(2)}</dd>
          <dt>Source segments</dt>
          <dd>{asset.source_segment_ids.join(', ')}</dd>
        </dl>
        <p className={styles.note}>Priority and evidence confidence are separate. Neither is a failure probability.</p>
      </section>
    </>
  );
}

export function AssetPanel({ assetId, onClose, open = true }: AssetPanelProps) {
  const asset = useAsset(assetId);
  const panelRef = useRef<HTMLElement>(null);
  const [entered, setEntered] = useState(false);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  // Slide in on the frame after mount; remember and restore focus.
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    panelRef.current?.focus();
    const raf = requestAnimationFrame(() => setEntered(true));
    return () => {
      cancelAnimationFrame(raf);
      if (previous && previous.isConnected) previous.focus();
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCloseRef.current();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  const visible = entered && open;
  const notFound = asset.error?.code === 'asset_not_found';

  return (
    <>
      <div className={`${styles.scrim} ${visible ? styles.scrimVisible : ''}`} onClick={onClose} aria-hidden="true" data-testid="asset-scrim" />
      <aside
        ref={panelRef}
        className={`${styles.panel} ${visible ? styles.panelOpen : ''}`}
        role="dialog"
        aria-label={`Asset ${assetId}`}
        tabIndex={-1}
      >
        <header className={styles.header}>
          <h2>{assetId}</h2>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Close asset panel">
            <X size={22} aria-hidden="true" />
          </button>
        </header>
        {notFound ? (
          <p className={styles.notFound} role="alert">
            {asset.error?.message}
          </p>
        ) : (
          <DataState
            status={asset.status}
            errorMessage={asset.error?.message}
            onRetry={asset.reload}
            loadingLabel="Loading asset"
            minHeight={220}
          >
            {asset.data && <Detail asset={asset.data} />}
          </DataState>
        )}
      </aside>
    </>
  );
}
