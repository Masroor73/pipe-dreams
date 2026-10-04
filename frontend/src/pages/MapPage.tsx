import { useMemo } from 'react';
import { useSearchParams } from 'react-router';
import { CommunityMap } from '../components/Communities/CommunityMap';
import { assetDots } from '../components/Communities/dots';
import { DataState } from '../components/DataState/DataState';
import { MapLegend } from '../components/Map/MapLegend';
import { PlanToggle } from '../components/Map/PlanToggle';
import { useAllAssets } from '../hooks';
import { useAssetLink } from '../hooks/useAssetLink';
import { useIsSynthetic } from '../lib/synthetic';
import type { CommunityFeatureCollection, PlanId } from '../types/api';
import styles from '../components/Map/Map.module.css';

const NO_POLYGONS: CommunityFeatureCollection = { type: 'FeatureCollection', features: [] };

/** Selected pipes of the chosen plan, plotted at the API's WGS84 latitude/longitude (no reprojection). */
export default function MapPage() {
  const [params, setParams] = useSearchParams();
  const plan: PlanId = params.get('plan') === 'v1' ? 'v1' : 'v2';
  const selectedId = params.get('asset');
  const openAsset = useAssetLink();
  const synthetic = useIsSynthetic();
  const list = useAllAssets({ plan, selected_only: true, sort: 'rank' });
  const items = list.data?.items;
  const dots = useMemo(() => assetDots(items ?? []), [items]);

  const setPlan = (next: PlanId) =>
    setParams((prev) => {
      const p = new URLSearchParams(prev);
      p.set('plan', next);
      return p;
    });

  const count = dots.features.length;
  return (
    <div
      className={styles.stage}
      // Without the synthetic banner the sticky nav still leaves a banner-height gap at the top.
      style={synthetic ? undefined : { marginTop: 'var(--banner-height)', height: 'calc(100% - var(--banner-height))' }}
    >
      <h1 className={styles.srOnly}>Map</h1>
      {list.status === 'success' && count > 0 && (
        <CommunityMap
          communities={NO_POLYGONS}
          selectedCommunityId={null}
          dots={dots}
          selectedAssetId={selectedId}
          onSelectCommunity={() => undefined}
          onSelectAsset={openAsset}
        />
      )}
      {list.status !== 'success' || count === 0 ? (
        <div className={styles.overlay}>
          <div className={styles.overlayInner}>
            <DataState
              status={list.status}
              errorMessage={list.error?.message}
              onRetry={list.reload}
              empty={count === 0}
              emptyMessage="No selected segments in this plan."
              loadingLabel="Loading map"
              minHeight={200}
            />
          </div>
        </div>
      ) : null}
      <PlanToggle plan={plan} onChange={setPlan} />
      {list.status === 'success' && <MapLegend count={count} plan={plan} />}
    </div>
  );
}
