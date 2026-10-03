import 'maplibre-gl/dist/maplibre-gl.css';
import { useEffect, useMemo, useRef, useState } from 'react';
import { setWorkerUrl } from 'maplibre-gl';
import Map, { Layer, Source } from 'react-map-gl/maplibre';
import type { MapRef } from 'react-map-gl/maplibre';
import type { MapLayerMouseEvent } from 'react-map-gl/maplibre';
import {
  BASEMAP_OFFLINE_NOTE,
  BASEMAP_STYLE_URL,
  CONFIDENCE_COLORS,
  FIT_MAX_ZOOM,
  FIT_EASE_MS,
  INITIAL_VIEW,
  CASING_COLOR,
  CHANGED_PULSE,
  CASING_EXTRA,
  HALO_COLOR,
  HALO_EXTRA,
  LINE_WIDTH_STOPS,
  MAPLIBRE_WORKER_PATH,
} from '../../config/map';
import type { AssetFeatureCollection, AssetFeatureProperties } from '../../types/api';
import { useChangedPulse } from './changedSegments';
import { featureBounds, fitPadding } from './geo';
import { OFFLINE_STYLE } from './offlineStyle';
import { useBasemap } from './useBasemap';
import type { MapViewProps } from './SvgFallbackMap';
import styles from './Map.module.css';

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

// Vite bundles/pre-bundles maplibre, which breaks its default worker URL; use the fixed copy.
setWorkerUrl(new URL(`${import.meta.env.BASE_URL}${MAPLIBRE_WORKER_PATH}`, window.location.href).href);

type Stops = readonly (readonly [number, number])[];
const widthExpr = (stops: Stops, extra = 0) =>
  ['interpolate', ['linear'], ['zoom'], ...stops.flatMap(([z, w]) => [z, w + extra])] as never;

const LINE_LAYOUT = { 'line-cap': 'round' as const, 'line-join': 'round' as const };

const EMPTY_IDS: ReadonlySet<string> = new Set();

function idFilter(id: string | null) {
  return ['==', ['get', 'asset_id'], id ?? ''] as never;
}

/** line-opacity: full for every segment, or dimmed for ids not in `changed` while the pulse runs. */
function pulseOpacity(dimmed: boolean, changed: ReadonlySet<string>) {
  if (!dimmed) return 1;
  return ['case', ['in', ['get', 'asset_id'], ['literal', [...changed]]], 1, CHANGED_PULSE.dimOpacity] as never;
}

export function MaplibreMap({ features, selectedId, changedIds, pulseKey, onSelect, onHover, onError }: MapViewProps) {
  const [hoverId, setHoverId] = useState<string | null>(null);
  const { mode, onStyleLoaded, onMapError } = useBasemap();
  const changed = changedIds ?? EMPTY_IDS;
  const dimmed = useChangedPulse(pulseKey ?? '', changed.size);
  // Dim instantly, then ease back to full opacity via MapLibre's paint transition.
  const opacityPaint = {
    'line-opacity': pulseOpacity(dimmed, changed),
    'line-opacity-transition': { duration: dimmed ? 0 : CHANGED_PULSE.returnMs, delay: 0 },
  } as never;
  const data = useMemo<AssetFeatureCollection>(() => ({ type: 'FeatureCollection', features }), [features]);
  const bounds = useMemo(() => featureBounds(features), [features]);
  const mapRef = useRef<MapRef>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const fittedBounds = useRef(bounds);
  const panelOpenRef = useRef(selectedId !== null);
  panelOpenRef.current = selectedId !== null;
  const initialViewState = bounds
    ? {
        bounds,
        fitBoundsOptions: {
          padding: fitPadding(typeof window === 'undefined' ? 0 : window.innerWidth, selectedId !== null),
          maxZoom: FIT_MAX_ZOOM,
        },
      }
    : INITIAL_VIEW;

  // Refit when the loaded segments change (e.g. the V1/V2 toggle); the first fit is the initial view state.
  useEffect(() => {
    if (!bounds || fittedBounds.current === bounds) return;
    fittedBounds.current = bounds;
    const reduced = typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const width = wrapRef.current?.clientWidth ?? window.innerWidth;
    mapRef.current?.fitBounds(bounds, {
      padding: fitPadding(width, panelOpenRef.current),
      maxZoom: FIT_MAX_ZOOM,
      duration: reduced ? 0 : FIT_EASE_MS,
    });
  }, [bounds]);

  const propsAt = (e: MapLayerMouseEvent): AssetFeatureProperties | null =>
    (e.features?.[0]?.properties as AssetFeatureProperties | undefined) ?? null;

  return (
    <div className={styles.mapFill} ref={wrapRef}>
      <Map
        ref={mapRef}
        key={mode}
        initialViewState={initialViewState}
        mapStyle={mode === 'online' ? BASEMAP_STYLE_URL : OFFLINE_STYLE}
        interactiveLayerIds={['lines']}
        attributionControl={{ compact: true }}
        onStyleData={onStyleLoaded}
        onError={(e) => {
          if (mode === 'offline') onError?.();
          else onMapError(e as unknown as { sourceId?: string; tile?: unknown });
        }}
        onMouseMove={(e) => {
          const p = propsAt(e);
          e.target.getCanvas().style.cursor = p ? 'pointer' : '';
          setHoverId(p?.asset_id ?? null);
          onHover(p ? { props: p, x: e.point.x, y: e.point.y } : null);
        }}
        onMouseLeave={() => {
          setHoverId(null);
          onHover(null);
        }}
        onClick={(e) => {
          const p = propsAt(e);
          if (p) onSelect(p.asset_id);
        }}
      >
        <Source id="assets" type="geojson" data={data}>
          <Layer
            id="lines-selected-halo"
            type="line"
            filter={idFilter(selectedId)}
            layout={LINE_LAYOUT}
            paint={{
              'line-color': HALO_COLOR,
              'line-opacity': 0.35,
              'line-width': widthExpr(LINE_WIDTH_STOPS.selected, HALO_EXTRA),
            }}
          />
          <Layer
            id="lines-casing"
            type="line"
            layout={LINE_LAYOUT}
            paint={{
              'line-color': CASING_COLOR,
              'line-width': widthExpr(LINE_WIDTH_STOPS.base, CASING_EXTRA),
              ...(opacityPaint as object),
            }}
          />
          <Layer
            id="lines-hover-casing"
            type="line"
            filter={idFilter(hoverId)}
            layout={LINE_LAYOUT}
            paint={{ 'line-color': CASING_COLOR, 'line-width': widthExpr(LINE_WIDTH_STOPS.hover, CASING_EXTRA) }}
          />
          <Layer
            id="lines-selected-casing"
            type="line"
            filter={idFilter(selectedId)}
            layout={LINE_LAYOUT}
            paint={{ 'line-color': CASING_COLOR, 'line-width': widthExpr(LINE_WIDTH_STOPS.selected, CASING_EXTRA) }}
          />
          <Layer
            id="lines"
            type="line"
            layout={LINE_LAYOUT}
            paint={{
              'line-color': LINE_COLOR,
              'line-width': widthExpr(LINE_WIDTH_STOPS.base),
              ...(opacityPaint as object),
            }}
          />
          <Layer
            id="lines-hover"
            type="line"
            filter={idFilter(hoverId)}
            layout={LINE_LAYOUT}
            paint={{ 'line-color': LINE_COLOR, 'line-width': widthExpr(LINE_WIDTH_STOPS.hover) }}
          />
          <Layer
            id="lines-selected"
            type="line"
            filter={idFilter(selectedId)}
            layout={LINE_LAYOUT}
            paint={{ 'line-color': LINE_COLOR, 'line-width': widthExpr(LINE_WIDTH_STOPS.selected) }}
          />
        </Source>
      </Map>
      {mode === 'offline' && <p className={`${styles.note} ${styles.basemapNote}`}>{BASEMAP_OFFLINE_NOTE}</p>}
    </div>
  );
}
