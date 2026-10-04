import { useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { X } from '@phosphor-icons/react';
import { CONSEQUENCE_TIER_LABEL } from '../../config/display';
import { OUTSIDE_CLICK_CLOSE_DELAY_MS, OUTSIDE_CLICK_DRAG_TOLERANCE_PX } from '../../config/map';
import { useAsset } from '../../hooks';
import { formatDelta, formatNumber } from '../../lib/format';
import type { AssetDetail, PlanFields } from '../../types/api';
import { DataState } from '../DataState/DataState';
import { ConfidencePill, Pill } from '../Pill/Pill';
import { Term } from '../Term/Term';
import styles from './AssetPanel.module.css';

export interface AssetPanelProps {
  assetId: string;
  onClose: () => void;
  /** Controlled by the shell so the panel can slide out before unmounting. Defaults to open. */
  open?: boolean;
}

interface CompareRow {
  label: string;
  /** Optional glossary-wrapped label node; `label` stays the key. */
  node?: ReactNode;
  get: (f: PlanFields) => string;
  /** Free text: may wrap. Numbers and enums never do. */
  prose?: boolean;
}

const COMPARE_ROWS: CompareRow[] = [
  { label: 'Rank', get: (f) => String(f.rank) },
  { label: 'Selected', get: (f) => (f.selected ? 'Yes' : 'No') },
  { label: 'Priority score', node: <Term id="priority">Priority score</Term>, get: (f) => f.priority_score.toFixed(3) },
  { label: 'Likelihood score', get: (f) => f.likelihood_score.toFixed(3) },
  { label: 'Recommended action', node: <Term id="recommended_action">Recommended action</Term>, get: (f) => f.recommended_action },
  { label: 'Revision reason', get: (f) => f.revision_reason ?? '—', prose: true },
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
              <th scope="row">{row.node ?? row.label}</th>
              <td className={row.prose ? styles.prose : undefined}>{a}</td>
              <td className={[a !== b ? styles.differs : '', row.prose ? styles.prose : ''].join(' ').trim() || undefined}>{b}</td>
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
        <Pill tone="neutral">
          <Term id="consequence_tier">{CONSEQUENCE_TIER_LABEL}</Term> {asset.consequence_tier}
        </Pill>
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
        <h3>
          <Term id="evidence_confidence">Evidence</Term>
        </h3>
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
  const assetIdRef = useRef(assetId);
  assetIdRef.current = assetId;
  const headingId = useId();

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

  // Outside click closes the panel with no scrim. Capture phase runs before the map's own click, so
  // a click on another segment (which sets ?asset=) wins: we only close if ?asset= is unchanged shortly
  // after. Drags (map panning) and clicks on [data-asset-trigger] elements are ignored.
  useEffect(() => {
    let down: { x: number; y: number } | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const outside = (t: EventTarget | null) =>
      t instanceof Node && !panelRef.current?.contains(t) && !(t instanceof Element && t.closest('[data-asset-trigger]'));
    const onDown = (e: PointerEvent) => {
      down = outside(e.target) ? { x: e.clientX, y: e.clientY } : null;
    };
    const onClick = (e: MouseEvent) => {
      const start = down;
      down = null;
      if (!outside(e.target)) return;
      if (start && Math.hypot(e.clientX - start.x, e.clientY - start.y) > OUTSIDE_CLICK_DRAG_TOLERANCE_PX) return;
      timer = setTimeout(() => {
        const current = new URLSearchParams(window.location.search).get('asset');
        if (current === null || current === assetIdRef.current) onCloseRef.current();
      }, OUTSIDE_CLICK_CLOSE_DELAY_MS);
    };
    document.addEventListener('pointerdown', onDown, true);
    document.addEventListener('click', onClick, true);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('pointerdown', onDown, true);
      document.removeEventListener('click', onClick, true);
    };
  }, []);

  const visible = entered && open;
  const notFound = asset.error?.code === 'asset_not_found';

  return (
    // Non-modal dialog: the map stays interactive and undimmed beside it, so aria-modal is false.
    <>
      <aside
        ref={panelRef}
        className={`${styles.panel} ${visible ? styles.panelOpen : ''}`}
        role="dialog"
        aria-modal="false"
        aria-labelledby={headingId}
        tabIndex={-1}
        data-asset-panel
      >
        <span className={styles.grab} aria-hidden="true" />
        <header className={styles.header}>
          <h2 id={headingId}>
            {`Asset ${assetId}`}
          </h2>
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
