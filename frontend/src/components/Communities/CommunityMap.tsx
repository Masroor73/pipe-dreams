import 'maplibre-gl/dist/maplibre-gl.css';
import { useEffect, useMemo, useRef, useState } from 'react';
import { setWorkerUrl } from 'maplibre-gl';
import Map, { Layer, Source } from 'react-map-gl/maplibre';
import type { MapLayerMouseEvent, MapRef } from 'react-map-gl/maplibre';
import {
  CASING_COLOR,
  CONFIDENCE_COLORS,
  INITIAL_VIEW,
  LINE_WIDTH_STOPS,
  MAPLIBRE_WORKER_PATH,
} from '../../config/map';
import type { AssetFeature, CommunityFeatureCollection } from '../../types/api';
import { OFFLINE_STYLE } from '../Map/offlineStyle';
import { hasWebGL } from '../Map/geo';
import styles from './Communities.module.css';

setWorkerUrl(new URL(`${import.meta.env.BASE_URL}${MAPLIBRE_WORKER_PATH}`, window.location.href).href);

type Bounds = [[number, number], [number, number]];

/** Bounding box of every vertex in a coordinate tree; camera framing only. */
export function coordBounds(coords: unknown): Bounds | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const walk = (c: unknown) => {
    if (!Array.isArray(c)) return;
    if (typeof c[0] === 'number' && typeof c[1] === 'number') {
      const [x, y] = c as [number, number];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
      return;
    }
    c.forEach(walk);
  };
  walk(coords);
  return Number.isFinite(minX)
    ? [
        [minX, minY],
        [maxX, maxY],
      ]
    : null;
}

const LINE_COLOR = [
  'match',
  ['get', 'evidence_confidence'],
  'HIGH',
  CONFIDENCE_COLORS.HIGH,
  'MEDIUM',
  CONFIDENCE_COLORS.MEDIUM,
  'LOW_VERIFY',
  CONFIDENCE_COLORS.LOW_VERIFY,
  CONFIDENCE_COLORS.HIGH,
] as unknown as string;

const widthExpr = (stops: readonly (readonly [number, number])[], extra = 0) =>
  ['interpolate', ['linear'], ['zoom'], ...stops.flatMap(([z, w]) => [z, w + extra])] as never;

const LINE_LAYOUT = { 'line-cap': 'round' as const, 'line-join': 'round' as const };

export interface CommunityMapProps {
  communities: CommunityFeatureCollection;
  selectedCommunityId: string | null;
  pipes: AssetFeature[];
  selectedAssetId: string | null;
  onSelectCommunity: (id: string) => void;
  onSelectAsset: (id: string) => void;
}

export function CommunityMap({
  communities,
  selectedCommunityId,
  pipes,
  selectedAssetId,
  onSelectCommunity,
  onSelectAsset,
}: CommunityMapProps) {
  const mapRef = useRef<MapRef>(null);
  const [loaded, setLoaded] = useState(false);
  const webgl = useMemo(() => hasWebGL(), []);
  const pipeData = useMemo(() => ({ type: 'FeatureCollection' as const, features: pipes }), [pipes]);
  const cityBounds = useMemo(
    () => coordBounds(communities.features.map((f) => f.geometry.coordinates)),
    [communities],
  );
  const target = useMemo(() => {
    const sel = communities.features.find((f) => f.properties.community_id === selectedCommunityId);
    return sel ? coordBounds(sel.geometry.coordinates) : cityBounds;
  }, [communities, selectedCommunityId, cityBounds]);

  useEffect(() => {
    if (!target || !loaded) return;
    mapRef.current?.fitBounds(target, { padding: 48, maxZoom: 15, duration: 600 });
  }, [target, loaded]);

  if (!webgl) {
    return (
      <div className={styles.noMap} role="status">
        The map needs WebGL, which is not available in this browser. The community and pipe lists still work.
      </div>
    );
  }

  const idFilter = ['==', ['get', 'community_id'], selectedCommunityId ?? ''] as never;
  const onClick = (e: MapLayerMouseEvent) => {
    const f = e.features?.[0];
    if (!f) return;
    if (f.layer.id === 'pipes') onSelectAsset(String(f.properties?.asset_id));
    else if (f.properties?.community_id) onSelectCommunity(String(f.properties.community_id));
  };

  return (
    <div className={styles.mapWrap}>
      <Map
        ref={mapRef}
        initialViewState={cityBounds ? { bounds: cityBounds, fitBoundsOptions: { padding: 48 } } : INITIAL_VIEW}
        mapStyle={OFFLINE_STYLE}
        interactiveLayerIds={['community-fill', 'pipes']}
        attributionControl={{ compact: true }}
        onLoad={() => setLoaded(true)}
        onClick={onClick}
        onMouseMove={(e) => {
          e.target.getCanvas().style.cursor = e.features?.length ? 'pointer' : '';
        }}
      >
        <Source id="communities" type="geojson" data={communities as never}>
          <Layer id="community-fill" type="fill" paint={{ 'fill-color': '#0b6e99', 'fill-opacity': 0.08 }} />
          <Layer
            id="community-selected-fill"
            type="fill"
            filter={idFilter}
            paint={{ 'fill-color': '#0b6e99', 'fill-opacity': 0.22 }}
          />
          <Layer id="community-outline" type="line" paint={{ 'line-color': '#4a5b6d', 'line-width': 1 }} />
          <Layer
            id="community-selected-outline"
            type="line"
            filter={idFilter}
            paint={{ 'line-color': '#0b6e99', 'line-width': 3 }}
          />
        </Source>
        <Source id="community-pipes" type="geojson" data={pipeData as never}>
          <Layer
            id="pipes-casing"
            type="line"
            layout={LINE_LAYOUT}
            paint={{ 'line-color': CASING_COLOR, 'line-width': widthExpr(LINE_WIDTH_STOPS.base, 2) }}
          />
          <Layer
            id="pipes"
            type="line"
            layout={LINE_LAYOUT}
            paint={{ 'line-color': LINE_COLOR, 'line-width': widthExpr(LINE_WIDTH_STOPS.base) }}
          />
          <Layer
            id="pipes-selected"
            type="line"
            filter={['==', ['get', 'asset_id'], selectedAssetId ?? ''] as never}
            layout={LINE_LAYOUT}
            paint={{ 'line-color': '#14202e', 'line-width': widthExpr(LINE_WIDTH_STOPS.selected) }}
          />
        </Source>
      </Map>
    </div>
  );
}
