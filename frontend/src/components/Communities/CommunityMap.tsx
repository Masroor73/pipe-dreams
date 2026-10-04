import 'maplibre-gl/dist/maplibre-gl.css';
import { useEffect, useMemo, useRef, useState } from 'react';
import { setWorkerUrl } from 'maplibre-gl';
import Map, { Layer, Source } from 'react-map-gl/maplibre';
import type { MapLayerMouseEvent, MapRef } from 'react-map-gl/maplibre';
import {
  BASEMAP_OFFLINE_NOTE,
  STREET_BASEMAP_STYLE,
  CASING_COLOR,
  CONFIDENCE_COLORS,
  INITIAL_VIEW,
  MAPLIBRE_WORKER_PATH,
} from '../../config/map';
import type { AssetFeatureCollection, CommunityFeatureCollection } from '../../types/api';
import { OFFLINE_STYLE } from '../Map/offlineStyle';
import { hasWebGL } from '../Map/geo';
import { useBasemap } from '../Map/useBasemap';
import type { DotCollection } from './dots';
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

const CONF_COLOR = [
  'match',
  ['get', 'evidence_confidence'],
  'HIGH',
  CONFIDENCE_COLORS.HIGH,
  'MEDIUM',
  CONFIDENCE_COLORS.MEDIUM,
  'LOW_VERIFY',
  CONFIDENCE_COLORS.LOW_VERIFY,
  CONFIDENCE_COLORS.HIGH,
] as unknown as never;

const MUTED = '#8795a5';
const colorBySelected = ['case', ['get', 'selected'], CONF_COLOR, MUTED] as never;
const LINE_LAYOUT = { 'line-cap': 'round' as const, 'line-join': 'round' as const };

export interface CommunityMapProps {
  communities: CommunityFeatureCollection;
  selectedCommunityId: string | null;
  /** Pipe lines (WGS84). null when only dots are available. */
  lines: AssetFeatureCollection | null;
  /** Small circles for pipes; fade out at street zoom when lines are present. */
  points: DotCollection;
  selectedAssetId: string | null;
  onSelectCommunity: (id: string) => void;
  onSelectAsset: (id: string) => void;
}

export function CommunityMap({
  communities,
  selectedCommunityId,
  lines,
  points,
  selectedAssetId,
  onSelectCommunity,
  onSelectAsset,
}: CommunityMapProps) {
  const mapRef = useRef<MapRef>(null);
  const [loaded, setLoaded] = useState(false);
  const webgl = useMemo(() => hasWebGL(), []);
  const { mode, onStyleLoaded, onMapError } = useBasemap();
  const cityBounds = useMemo(
    () => coordBounds(communities.features.map((f) => f.geometry.coordinates)),
    [communities],
  );
  const target = useMemo(() => {
    const sel = communities.features.find((f) => f.properties.community_id === selectedCommunityId);
    if (sel) return coordBounds(sel.geometry.coordinates);
    return cityBounds ?? coordBounds(points.features.map((f) => f.geometry.coordinates));
  }, [communities, selectedCommunityId, cityBounds, points]);

  const fittedOnce = useRef(false);
  useEffect(() => {
    if (!target || !loaded) return;
    // The first fit jumps (no animation) so the map is usable as soon as the pipes arrive.
    mapRef.current?.fitBounds(target, { padding: 80, maxZoom: 14, duration: fittedOnce.current ? 600 : 0 });
    fittedOnce.current = true;
  }, [target, loaded]);

  if (!webgl) {
    return (
      <div className={styles.noMap} role="status">
        The map needs WebGL, which is not available in this browser. The community and pipe lists still work.
      </div>
    );
  }

  const hasLines = lines !== null;
  const idFilter = ['==', ['get', 'community_id'], selectedCommunityId ?? ''] as never;
  const openFilter = ['==', ['get', 'asset_id'], selectedAssetId ?? ''] as never;
  // With lines present the circles hand over to them above street zoom; as the only layer they stay.
  const dotOpacity = hasLines ? (['interpolate', ['linear'], ['zoom'], 14, 1, 15.5, 0] as never) : 1;
  const dotRadius = ['interpolate', ['linear'], ['zoom'], 10, 2, 14, 4] as never;
  const dotRadiusMuted = ['interpolate', ['linear'], ['zoom'], 10, 1.5, 14, 3] as never;
  const lineWidth = (extra: number) =>
    ['interpolate', ['linear'], ['zoom'], 10, 1.5 + extra, 14, 3 + extra, 17, 4 + extra] as never;

  const onClick = (e: MapLayerMouseEvent) => {
    const f = e.features?.[0];
    if (!f) return;
    if (f.layer.id === 'lines' || f.layer.id.startsWith('dots')) onSelectAsset(String(f.properties?.asset_id));
    else if (f.properties?.community_id) onSelectCommunity(String(f.properties.community_id));
  };

  return (
    <div className={styles.mapWrap}>
      <Map
        key={mode}
        ref={mapRef}
        initialViewState={cityBounds ? { bounds: cityBounds, fitBoundsOptions: { padding: 48 } } : INITIAL_VIEW}
        mapStyle={mode === 'online' ? (STREET_BASEMAP_STYLE as never) : OFFLINE_STYLE}
        interactiveLayerIds={hasLines ? ['lines', 'dots-muted', 'dots', 'community-fill'] : ['dots-muted', 'dots', 'community-fill']}
        attributionControl={{ compact: true }}
        onLoad={() => setLoaded(true)}
        onIdle={() => {
          // Timing hook for load measurements (performance.getEntriesByName('pd-map-idle')); no behaviour.
          if (typeof performance !== 'undefined') performance.mark('pd-map-idle');
        }}
        onStyleData={onStyleLoaded}
        onError={(e) => {
          if (mode === 'online') onMapError(e as unknown as { sourceId?: string; tile?: unknown });
        }}
        onClick={onClick}
        onMouseMove={(e) => {
          e.target.getCanvas().style.cursor = e.features?.length ? 'pointer' : '';
        }}
      >
        <Source id="communities" type="geojson" data={communities as never}>
          <Layer id="community-fill" type="fill" paint={{ 'fill-color': '#0b6e99', 'fill-opacity': 0.04 }} />
          <Layer
            id="community-selected-fill"
            type="fill"
            filter={idFilter}
            paint={{ 'fill-color': '#0b6e99', 'fill-opacity': 0.15 }}
          />
          <Layer id="community-outline" type="line" paint={{ 'line-color': '#4a5b6d', 'line-width': 1 }} />
          <Layer
            id="community-selected-outline"
            type="line"
            filter={idFilter}
            paint={{ 'line-color': '#0b6e99', 'line-width': 3 }}
          />
        </Source>
        {lines && (
          <Source id="asset-lines" type="geojson" data={lines as never}>
            <Layer
              id="lines-casing"
              type="line"
              layout={LINE_LAYOUT}
              paint={{ 'line-color': CASING_COLOR, 'line-width': lineWidth(2) }}
            />
            <Layer
              id="lines"
              type="line"
              layout={LINE_LAYOUT}
              paint={{ 'line-color': colorBySelected, 'line-width': lineWidth(0) }}
            />
            <Layer
              id="lines-open"
              type="line"
              filter={openFilter}
              layout={LINE_LAYOUT}
              paint={{ 'line-color': '#14202e', 'line-width': lineWidth(3) }}
            />
          </Source>
        )}
        <Source id="asset-dots" type="geojson" data={points as never}>
          <Layer
            id="dots-muted"
            type="circle"
            filter={['!', ['get', 'selected']] as never}
            paint={{ 'circle-color': MUTED, 'circle-radius': dotRadiusMuted, 'circle-opacity': hasLines ? dotOpacity : 0.6 }}
          />
          <Layer
            id="dots"
            type="circle"
            filter={['get', 'selected'] as never}
            paint={{
              'circle-color': CONF_COLOR,
              'circle-radius': dotRadius,
              'circle-opacity': dotOpacity,
              'circle-stroke-color': '#ffffff',
              'circle-stroke-width': 0.75,
              'circle-stroke-opacity': dotOpacity,
            }}
          />
          <Layer
            id="dots-open"
            type="circle"
            filter={openFilter}
            paint={{
              'circle-color': '#14202e',
              'circle-radius': 7,
              'circle-stroke-color': '#ffffff',
              'circle-stroke-width': 2,
            }}
          />
        </Source>
      </Map>
      {mode === 'offline' && <p className={styles.offlineNote}>{BASEMAP_OFFLINE_NOTE}</p>}
    </div>
  );
}
