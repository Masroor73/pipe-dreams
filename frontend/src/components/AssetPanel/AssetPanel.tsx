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

function PlanColumn({ title, fields, other }: { title: string; fields: PlanFields; other: PlanFields }) {
  const actionDiffers = fields.recommended_action !== other.recommended_action;
  return (
    <section className={styles.col} aria-label={`${title} plan`}>
      <h3>{title}</h3>
      <dl>
        <dt>Rank</dt>
        <dd>{fields.rank}</dd>
        <dt>Selected</dt>
        <dd>{fields.selected ? 'Yes' : 'No'}</dd>
        <dt>Priority score</dt>
        <dd>{fields.priority_score.toFixed(3)}</dd>
        <dt>Likelihood score</dt>
        <dd>{fields.likelihood_score.toFixed(3)}</dd>
        <dt>Recommended action</dt>
        <dd>
          <span className={actionDiffers ? styles.differs : undefined}>{fields.recommended_action}</span>
        </dd>
        <dt>Revision reason</dt>
        <dd>{fields.revision_reason ?? '—'}</dd>
      </dl>
    </section>
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

      <div className={styles.cols}>
        <PlanColumn title="V1" fields={asset.v1} other={asset.v2} />
        <PlanColumn title="V2" fields={asset.v2} other={asset.v1} />
      </div>

      {rc && (
        <p className={styles.delta}>
          <strong>Rank change {formatDelta(rc.delta_rank)}</strong>
          {[rc.reason_1, rc.reason_2].filter(Boolean).map((r) => (
            <span key={r}>{r}</span>
          ))}
        </p>
      )}

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
