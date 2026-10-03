import type { AssetFeatureProperties } from '../../types/api';
import styles from './Map.module.css';

export interface HoverInfo {
  props: AssetFeatureProperties;
  x: number;
  y: number;
}

export function MapTooltip({ hover }: { hover: HoverInfo | null }) {
  if (!hover) return null;
  const { props, x, y } = hover;
  return (
    <div className={styles.tooltip} style={{ left: x + 14, top: y + 14 }} role="tooltip">
      <strong>{props.asset_id}</strong>
      <span>
        Rank {props.rank} · {props.evidence_confidence}
      </span>
      <span>{props.recommended_action}</span>
    </div>
  );
}
