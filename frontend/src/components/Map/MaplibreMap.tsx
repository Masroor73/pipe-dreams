import 'maplibre-gl/dist/maplibre-gl.css';
import { useMemo, useState } from 'react';
import { setWorkerUrl } from 'maplibre-gl';
import Map, { Layer, Source } from 'react-map-gl/maplibre';
import type { MapLayerMouseEvent } from 'react-map-gl/maplibre';
import {
  CONFIDENCE_COLORS,
  FIT_MAX_ZOOM,
  FIT_PADDING,
  INITIAL_VIEW,
  CASING_COLOR,
  CASING_EXTRA,
  HALO_COLOR,
  HALO_EXTRA,
  LINE_WIDTH_STOPS,
  MAPLIBRE_WORKER_PATH,
} from '../../config/map';
import type { AssetFeatureCollection, AssetFeatureProperties } from '../../types/api';
import { featureBounds } from './geo';
import { OFFLINE_STYLE } from './offlineStyle';
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

function idFilter(id: string | null) {
  return ['==', ['get', 'asset_id'], id ?? ''] as never;
}

export function MaplibreMap({ features, selectedId, onSelect, onHover, onError }: MapViewProps) {
  const [hoverId, setHoverId] = useState<string | null>(null);
  const data = useMemo<AssetFeatureCollection>(() => ({ type: 'FeatureCollection', features }), [features]);
  const bounds = useMemo(() => featureBounds(features), [features]);
  const initialViewState = bounds
    ? { bounds, fitBoundsOptions: { padding: FIT_PADDING, maxZoom: FIT_MAX_ZOOM } }
    : INITIAL_VIEW;

  const propsAt = (e: MapLayerMouseEvent): AssetFeatureProperties | null =>
    (e.features?.[0]?.properties as AssetFeatureProperties | undefined) ?? null;

  return (
    <div className={styles.mapFill}>
      <Map
        initialViewState={initialViewState}
        mapStyle={OFFLINE_STYLE}
        interactiveLayerIds={['lines']}
        attributionControl={false}
        onError={() => onError?.()}
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
            paint={{ 'line-color': CASING_COLOR, 'line-width': widthExpr(LINE_WIDTH_STOPS.base, CASING_EXTRA) }}
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
            paint={{ 'line-color': LINE_COLOR, 'line-width': widthExpr(LINE_WIDTH_STOPS.base) }}
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
    </div>
  );
}
