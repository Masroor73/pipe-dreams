import { useMemo } from 'react';
import { CONFIDENCE_COLORS, MAP_BACKGROUND } from '../../config/map';
import type { AssetFeature } from '../../types/api';
import { useChangedPulse } from './changedSegments';
import { projectFeatures, SVG_VIEW } from './geo';
import type { HoverInfo } from './MapTooltip';
import styles from './Map.module.css';

export interface MapViewProps {
  features: AssetFeature[];
  selectedId: string | null;
  /** Asset ids that differ from the other plan; unchanged ones dim briefly on load/toggle. */
  changedIds?: ReadonlySet<string>;
  /** Changes whenever the pulse should replay (e.g. the plan id). */
  pulseKey?: string;
  onSelect: (assetId: string) => void;
  onHover: (h: HoverInfo | null) => void;
  onError?: () => void;
}

/** Plain data drawing of the same lines: used when WebGL or the map fails. */
export function SvgFallbackMap({ features, selectedId, changedIds, pulseKey, onSelect, onHover }: MapViewProps) {
  const dimmed = useChangedPulse(pulseKey ?? '', changedIds?.size ?? 0);
  const lines = useMemo(() => projectFeatures(features), [features]);
  const byId = useMemo(() => new Map(features.map((f) => [f.properties.asset_id, f.properties])), [features]);

  return (
    <div className={styles.fallback} style={{ background: MAP_BACKGROUND }}>
      <svg
        viewBox={`0 0 ${SVG_VIEW.width} ${SVG_VIEW.height}`}
        className={styles.svg}
        role="group"
        aria-label="Selected pipe segments (fallback drawing, no basemap)"
      >
        {lines.map((l) => {
          const p = byId.get(l.asset_id)!;
          const selected = l.asset_id === selectedId;
          return (
            <path
              key={l.asset_id}
              d={l.d}
              className={`${styles.svgLine} ${selected ? styles.svgLineSelected : ''} ${dimmed && !changedIds?.has(l.asset_id) ? styles.svgDim : ''}`}
              stroke={CONFIDENCE_COLORS[p.evidence_confidence]}
              fill="none"
              vectorEffect="non-scaling-stroke"
              strokeLinecap="round"
              strokeLinejoin="round"
              tabIndex={0}
              role="button"
              aria-label={`${l.asset_id}, rank ${p.rank}, ${p.evidence_confidence}`}
              data-asset-id={l.asset_id}
              onClick={() => onSelect(l.asset_id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelect(l.asset_id);
                }
              }}
              onMouseMove={(e) => {
                const r = e.currentTarget.ownerSVGElement!.parentElement!.getBoundingClientRect();
                onHover({ props: p, x: e.clientX - r.left, y: e.clientY - r.top });
              }}
              onMouseLeave={() => onHover(null)}
            />
          );
        })}
      </svg>
      <p className={`${styles.note} ${styles.basemapNote}`}>Basemap: none (offline)</p>
    </div>
  );
}
