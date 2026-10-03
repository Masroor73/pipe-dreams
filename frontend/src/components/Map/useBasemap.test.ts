import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { isStyleLevelError, useBasemap } from './useBasemap';

describe('useBasemap', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('goes offline on a style-level error before the style loads', () => {
    const { result } = renderHook(() => useBasemap(4000));
    expect(result.current.mode).toBe('online');
    act(() => result.current.onMapError({}));
    expect(result.current.mode).toBe('offline');
  });

  it('goes offline when the style does not load within the timeout', () => {
    const { result } = renderHook(() => useBasemap(4000));
    act(() => vi.advanceTimersByTime(3999));
    expect(result.current.mode).toBe('online');
    act(() => vi.advanceTimersByTime(2));
    expect(result.current.mode).toBe('offline');
  });

  it('stays online when the style loads in time, even after a later error', () => {
    const { result } = renderHook(() => useBasemap(4000));
    act(() => result.current.onStyleLoaded());
    act(() => result.current.onMapError({}));
    act(() => vi.advanceTimersByTime(10000));
    expect(result.current.mode).toBe('online');
  });

  it('ignores tile errors before the style has loaded', () => {
    const { result } = renderHook(() => useBasemap(4000));
    act(() => result.current.onMapError({ sourceId: 'openmaptiles', tile: {} }));
    expect(result.current.mode).toBe('online');
    expect(isStyleLevelError({ sourceId: 'x' })).toBe(false);
    expect(isStyleLevelError({})).toBe(true);
  });
});
