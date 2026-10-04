import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { DataState } from '../components/DataState/DataState';
import { MapLegend } from '../components/Map/MapLegend';
import { NetworkMap } from '../components/Map/NetworkMap';
import { PlanToggle } from '../components/Map/PlanToggle';
import { changedAssetIds } from '../components/Map/changedSegments';
import { useAssetsGeoJson } from '../hooks';
import { useAssetLink } from '../hooks/useAssetLink';
import { api } from '../lib/api';
import type { AssetFeature, PlanId } from '../types/api';
import styles from '../components/Map/Map.module.css';

/**
 * The open asset may sit outside the plan's selected segments (e.g. a rank-change card for a
 * segment below the capacity line). Fetch its detail and draw it too, so the panel's asset is
 * always on the map. Presentation only: geometry and fields come straight from /api/assets/{id}.
 */
function useOutsideSelected(selectedId: string | null, features: AssetFeature[], plan: PlanId): AssetFeature | null {
  const inLayer = !!selectedId && features.some((f) => f.properties.asset_id === selectedId);
  const [extra, setExtra] = useState<AssetFeature | null>(null);
  useEffect(() => {
    setExtra(null);
    if (!selectedId || inLayer) return;
    let alive = true;
    api
      .getAsset(selectedId)
      .then(({ data: d }) => {
        if (!alive) return;
        const pf = plan === 'v1' ? d.v1 : d.v2;
        setExtra({
          type: 'Feature',
          id: d.asset_id,
          geometry: d.geometry,
          properties: {
            asset_id: d.asset_id,
            rank: pf.rank,
            selected: pf.selected,
            consequence_tier: d.consequence_tier,
            evidence_confidence: d.evidence_confidence,
            recommended_action: pf.recommended_action,
          },
        });
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [selectedId, inLayer, plan]);
  return extra;
}

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

  const planFeatures = useMemo(() => geo.data?.features ?? [], [geo.data]);
  const extra = useOutsideSelected(selectedId, planFeatures, plan);
  const features = useMemo(() => (extra ? [...planFeatures, extra] : planFeatures), [planFeatures, extra]);
  // Presentation only: segments in this plan that the other plan does not select.
  const changedIds = useMemo(
    () => changedAssetIds(planFeatures, other.status === 'success' ? (other.data?.features ?? []) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [planFeatures, other.data, other.status],
  );

  return (
    <div className={styles.stage}>
      <h1 className={styles.srOnly}>Map</h1>
      {geo.status === 'success' && planFeatures.length > 0 && (
        <NetworkMap features={features} selectedId={selectedId}
          changedIds={changedIds}
          pulseKey={`${plan}:${changedIds.size}`}
          onSelect={openAsset}
        />
      )}
      {geo.status !== 'success' || planFeatures.length === 0 ? (
        <div className={styles.overlay}>
          <div className={styles.overlayInner}>
            <DataState
              status={geo.status}
              errorMessage={geo.error?.message}
              onRetry={geo.reload}
              empty={planFeatures.length === 0}
              emptyMessage="No selected segments in this plan."
              loadingLabel="Loading map"
              minHeight={200}
            />
          </div>
        </div>
      ) : null}
      <PlanToggle plan={plan} onChange={setPlan} />
      {geo.status === 'success' && <MapLegend count={planFeatures.length} plan={plan} />}
    </div>
  );
}
