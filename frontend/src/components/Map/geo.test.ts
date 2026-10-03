import { describe, expect, it } from 'vitest';
import { FIT_PADDING, FIT_PADDING_COMPACT, FIT_PANEL_WIDTH_PX } from '../../config/map';
import { fitPadding } from './geo';

describe('fitPadding', () => {
  it('uses the standard padding on wide maps without the panel', () => {
    expect(fitPadding(1440, false)).toEqual({ top: FIT_PADDING, bottom: FIT_PADDING, left: FIT_PADDING, right: FIT_PADDING });
  });
  it('reserves the right side for the asset panel when it sits beside the map', () => {
    expect(fitPadding(1440, true).right).toBe(FIT_PADDING + FIT_PANEL_WIDTH_PX);
  });
  it('ignores the panel when it would cover the whole map', () => {
    expect(fitPadding(768, true).right).toBe(FIT_PADDING);
    expect(fitPadding(390, true).right).toBe(FIT_PADDING_COMPACT);
  });
  it('uses compact padding on narrow maps', () => {
    expect(fitPadding(390, false).left).toBe(FIT_PADDING_COMPACT);
  });
});
