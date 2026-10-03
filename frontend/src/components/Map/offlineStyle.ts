import type { StyleSpecification } from 'maplibre-gl';
import { MAP_BACKGROUND } from '../../config/map';

/**
 * Fully offline style: one background layer, no sources, no glyphs, no sprite,
 * no symbol layers. Nothing in it triggers a network request.
 */
export const OFFLINE_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': MAP_BACKGROUND } }],
};
