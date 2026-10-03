import 'maplibre-gl/dist/maplibre-gl.css';
import { useMemo, useState } from 'react';
import Map, { Layer, Source } from 'react-map-gl/maplibre';
import type { MapLayerMouseEvent } from 'react-map-gl/maplibre';
import {
  CONFIDENCE_COLORS,
  FIT_MAX_ZOOM,
  FIT_PADDING,
  INITIAL_VIEW,
  LINE_WIDTH,
  SELECTED_OUTLINE,
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
            paint={{ 'line-color': SELECTED_OUTLINE, 'line-width': LINE_WIDTH.selected + 4 }}
          />
          <Layer id="lines" type="line" layout={LINE_LAYOUT} paint={{ 'line-color': LINE_COLOR, 'line-width': LINE_WIDTH.base }} />
          <Layer
            id="lines-hover"
            type="line"
            filter={idFilter(hoverId)}
            layout={LINE_LAYOUT}
            paint={{ 'line-color': LINE_COLOR, 'line-width': LINE_WIDTH.hover }}
          />
          <Layer
            id="lines-selected"
            type="line"
            filter={idFilter(selectedId)}
            layout={LINE_LAYOUT}
            paint={{ 'line-color': LINE_COLOR, 'line-width': LINE_WIDTH.selected }}
          />
        </Source>
      </Map>
    </div>
  );
}
