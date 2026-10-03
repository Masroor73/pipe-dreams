import { useMemo } from 'react';
import { useSearchParams } from 'react-router';
import { DataState } from '../components/DataState/DataState';
import { MapLegend } from '../components/Map/MapLegend';
import { NetworkMap } from '../components/Map/NetworkMap';
import { PlanToggle } from '../components/Map/PlanToggle';
import { changedAssetIds } from '../components/Map/changedSegments';
import { useAssetsGeoJson } from '../hooks';
import { useAssetLink } from '../hooks/useAssetLink';
import type { PlanId } from '../types/api';
import styles from '../components/Map/Map.module.css';

export default function MapPage() {
  const [params, setParams] = useSearchParams();
  const plan: PlanId = params.get('plan') === 'v1' ? 'v1' : 'v2';
  const selectedId = params.get('asset');
  const openAsset = useAssetLink();
  const geoV1 = useAssetsGeoJson({ plan: 'v1', selected_only: true });
  const geoV2 = useAssetsGeoJson({ plan: 'v2', selected_only: true });
  const geo = plan === 'v1' ? geoV1 : geoV2;
  const other = plan === 'v1' ? geoV2 : geoV1;

  const setPlan = (next: PlanId) =>
    setParams((prev) => {
      const p = new URLSearchParams(prev);
      p.set('plan', next);
      return p;
    });

  const features = geo.data?.features ?? [];
  // Presentation only: segments in this plan that the other plan does not select.
  const changedIds = useMemo(
    () => changedAssetIds(features, other.status === 'success' ? (other.data?.features ?? []) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [geo.data, other.data, other.status],
  );

  return (
    <div className={styles.stage}>
      <h1 className={styles.srOnly}>Map</h1>
      {geo.status === 'success' && features.length > 0 && (
        <NetworkMap features={features} selectedId={selectedId}
          changedIds={changedIds}
          pulseKey={`${plan}:${changedIds.size}`}
          onSelect={openAsset}
        />
      )}
      {geo.status !== 'success' || features.length === 0 ? (
        <div className={styles.overlay}>
          <div className={styles.overlayInner}>
            <DataState
              status={geo.status}
              errorMessage={geo.error?.message}
              onRetry={geo.reload}
              empty={features.length === 0}
              emptyMessage="No selected segments in this plan."
              loadingLabel="Loading map"
              minHeight={200}
            />
          </div>
        </div>
      ) : null}
      <PlanToggle plan={plan} onChange={setPlan} />
      {geo.status === 'success' && <MapLegend count={features.length} plan={plan} />}
    </div>
  );
}
