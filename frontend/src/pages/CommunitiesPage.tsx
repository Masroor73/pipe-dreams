import { useMemo } from 'react';
import { useSearchParams } from 'react-router';
import { CommunityMap } from '../components/Communities/CommunityMap';
import { DataState } from '../components/DataState/DataState';
import { ConfidencePill, Pill } from '../components/Pill/Pill';
import { useAllAssets, useCommunities, useCommunitiesGeoJson } from '../hooks';
import { assetDots } from '../components/Communities/dots';
import type { DotCollection } from '../components/Communities/dots';
import { useAssetLink } from '../hooks/useAssetLink';
import { formatNumber } from '../lib/format';
import { useIsSynthetic } from '../lib/synthetic';
import type { Resource } from '../hooks';
import type { AssetList, CommunityFeatureCollection, CommunityProperties } from '../types/api';
import styles from '../components/Communities/Communities.module.css';

const EMPTY_DOTS: DotCollection = { type: 'FeatureCollection', features: [] };

function CommunityRow({ c, onSelect }: { c: CommunityProperties; onSelect: (id: string) => void }) {
  return (
    <li>
      <button type="button" className={styles.row} onClick={() => onSelect(c.community_id)}>
        <span className={styles.rowTitle}>{c.community_name}</span>
        <span className={styles.meta}>
          <span>{formatNumber(c.historical_break_count)} historical breaks</span>
          <span>
            {c.historical_breaks_per_km === null ? 'n/a' : formatNumber(c.historical_breaks_per_km, 2)} breaks / km
          </span>
          <span>{formatNumber(c.pipe_length_km, 1)} km of pipe</span>
        </span>
        {c.data_quality_flags.length > 0 && (
          <span className={styles.pillRow}>
            {c.data_quality_flags.map((f) => (
              <Pill key={f}>{f}</Pill>
            ))}
          </span>
        )}
      </button>
    </li>
  );
}

/** Pipes of the selected community in API (citywide-rank) order. Never re-ranked here. */
function PipeList({
  community,
  selectedOnly,
  onToggle,
  onClear,
  assetId,
  list,
}: {
  list: Resource<AssetList>;
  community: CommunityProperties;
  selectedOnly: boolean;
  onToggle: (v: boolean) => void;
  onClear: () => void;
  assetId: string | null;
}) {
  const openAsset = useAssetLink();
  const items = list.data?.items ?? [];
  return (
    <section aria-label="Pipes in selected community" style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      <div className={styles.toolbar}>
        <h2 className={styles.subhead}>{community.community_name}</h2>
        <button type="button" className={styles.btn} onClick={onClear}>
          Clear selection
        </button>
      </div>
      <label className={styles.toggle}>
        <input type="checkbox" checked={selectedOnly} onChange={(e) => onToggle(e.target.checked)} />
        Selected for inspection only
      </label>
      <p className={styles.note}>
        Pipes are listed in citywide rank order. Rank is not recomputed within the community.
      </p>
      <DataState
        status={list.status}
        errorMessage={list.error?.message}
        onRetry={list.reload}
        empty={list.status === 'success' && items.length === 0}
        emptyMessage={selectedOnly ? 'No pipes here are selected for inspection.' : 'No pipes in this community.'}
        loadingLabel="Loading pipes"
      >
        <p className={styles.note}>
          {list.data
            ? `${list.data.total} pipes${list.data.total > items.length ? `, showing ${items.length}` : ''}`
            : ''}
        </p>
        <ul className={styles.list}>
          {items.map((a) => (
            <li key={a.asset_id}>
              <button
                type="button"
                className={`${styles.row} ${assetId === a.asset_id ? styles.rowActive : ''}`}
                onClick={() => openAsset(a.asset_id)}
              >
                <span className={styles.rowTitle}>
                  <span className={styles.assetId}>{a.asset_id}</span>
                  <span className={styles.rank}>#{a.rank} citywide</span>
                </span>
                <span className={styles.meta}>
                  <span>{formatNumber(a.length_m, a.length_m < 10 ? 2 : 0)} m</span>
                  <span>{a.recommended_action}</span>
                </span>
                <span className={styles.pillRow}>
                  <Pill>Consequence tier {a.consequence_tier}</Pill>
                  <ConfidencePill confidence={a.evidence_confidence} />
                </span>
              </button>
            </li>
          ))}
        </ul>
      </DataState>
    </section>
  );
}

export default function CommunitiesPage() {
  const [params, setParams] = useSearchParams();
  const communityId = params.get('community');
  const selectedOnly = params.get('inspect') === 'true';
  const assetId = params.get('asset');
  const list = useCommunities();
  const geo = useCommunitiesGeoJson();
  const synthetic = useIsSynthetic();

  const items = list.data?.items ?? [];
  const selected = communityId ? items.find((c) => c.community_id === communityId) : undefined;
  const notFound = !!communityId && list.status === 'success' && !selected;
  const pipes = useAllAssets(
    { community_id: selected?.community_id, selected_only: selectedOnly, sort: 'rank' },
    !!selected,
  );
  const dots = useMemo(() => (pipes.data ? assetDots(pipes.data.items) : EMPTY_DOTS), [pipes.data]);

  const update = (fn: (p: URLSearchParams) => void) =>
    setParams((prev) => {
      const p = new URLSearchParams(prev);
      fn(p);
      return p;
    });
  const select = (id: string) => update((p) => p.set('community', id));
  const clear = () =>
    update((p) => {
      p.delete('community');
      p.delete('inspect');
    });
  const setSelectedOnly = (v: boolean) => update((p) => (v ? p.set('inspect', 'true') : p.delete('inspect')));

  const polygons: CommunityFeatureCollection = useMemo(
    () => geo.data ?? { type: 'FeatureCollection', features: [] },
    [geo.data],
  );
  const renderMap = (dots: DotCollection) => (
    <div className={styles.mapCol}>
      {geo.status === 'success' ? (
        <CommunityMap
          communities={polygons}
          selectedCommunityId={selected ? communityId : null}
          dots={dots}
          selectedAssetId={assetId}
          onSelectCommunity={select}
          onSelectAsset={(id) => update((p) => p.set('asset', id))}
        />
      ) : (
        <DataState
          status={geo.status}
          errorMessage={geo.error?.message}
          onRetry={geo.reload}
          loadingLabel="Loading map"
        />
      )}
    </div>
  );

  return (
    <div className={`${styles.page} ${synthetic ? '' : styles.noBanner}`}>
      <div className={styles.side}>
        <h1>Which communities should we protect first, and which pipes within them should we inspect?</h1>
        <p className={styles.note}>
          Community ranking = historical break burden per km of pipe, not social vulnerability.
        </p>
        {notFound && (
          <div role="alert" className={styles.note}>
            <strong>Community not found.</strong> No community with id '{communityId}' exists.{' '}
            <button type="button" className={styles.btn} onClick={clear}>
              Back to citywide view
            </button>
          </div>
        )}
        <DataState
          status={list.status}
          errorMessage={list.error?.message}
          onRetry={list.reload}
          empty={list.status === 'success' && items.length === 0}
          emptyMessage="No community data is available."
          loadingLabel="Loading communities"
        >
          {selected ? (
            <PipeList
              list={pipes}
              community={selected}
              selectedOnly={selectedOnly}
              onToggle={setSelectedOnly}
              onClear={clear}
              assetId={assetId}
            />
          ) : (
            <ul className={styles.list} aria-label="Communities ranked by historical break burden per km">
              {items.map((c) => (
                <CommunityRow key={c.community_id} c={c} onSelect={select} />
              ))}
            </ul>
          )}
        </DataState>
      </div>
      {renderMap(dots)}
    </div>
  );
}
