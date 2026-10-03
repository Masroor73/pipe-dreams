import { useState } from 'react';
import type { AssetFeature } from '../../types/api';
import { hasWebGL } from './geo';
import { MapTooltip } from './MapTooltip';
import type { HoverInfo } from './MapTooltip';
import { MaplibreMap } from './MaplibreMap';
import { SvgFallbackMap } from './SvgFallbackMap';
import styles from './Map.module.css';

export interface NetworkMapProps {
  features: AssetFeature[];
  selectedId: string | null;
  changedIds?: ReadonlySet<string>;
  pulseKey?: string;
  onSelect: (assetId: string) => void;
}

/** MapLibre canvas on an offline style; falls back to a plain SVG drawing if WebGL or the map fails. */
export function NetworkMap({ features, selectedId, changedIds, pulseKey, onSelect }: NetworkMapProps) {
  const [failed, setFailed] = useState(() => !hasWebGL());
  const [hover, setHover] = useState<HoverInfo | null>(null);
  const View = failed ? SvgFallbackMap : MaplibreMap;

  return (
    <div className={styles.stage}>
      <View
        features={features}
        selectedId={selectedId}
        changedIds={changedIds}
        pulseKey={pulseKey}
        onSelect={onSelect}
        onHover={setHover}
        onError={() => setFailed(true)}
      />
      <MapTooltip hover={hover} />
    </div>
  );
}
