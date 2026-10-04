import { describe, expect, it } from 'vitest';
import globalCss from './global.css?raw';
import tokensCss from './tokens.css?raw';

const css = (f: 'global.css' | 'tokens.css') => (f === 'global.css' ? globalCss : tokensCss);

/** The universal reduced-motion block in global.css. */
function reducedBlock(src: string): string {
  const start = src.search(/@media \(prefers-reduced-motion: reduce\) \{\s*\*,/);
  expect(start).toBeGreaterThan(-1);
  return src.slice(start, src.indexOf('\n}', start));
}

describe('reduced motion policy', () => {
  it('removes keyframe movement but keeps short opacity/colour cross-fades', () => {
    const block = reducedBlock(css('global.css'));
    expect(block).toMatch(/animation:\s*none !important/);
    const props = /transition-property:\s*([^;]+);/.exec(block)![1]!;
    expect(props).toMatch(/opacity/);
    expect(props).toMatch(/color/);
    expect(props).not.toMatch(/transform|translate|scale|width|height|top|left/);
    expect(block).not.toMatch(/0\.01ms/);
  });

  it('reduced fade duration is 150ms or less', () => {
    const ms = Number(/--reduced-fade-ms:\s*(\d+)ms/.exec(css('tokens.css'))![1]);
    expect(ms).toBeGreaterThan(0);
    expect(ms).toBeLessThanOrEqual(150);
  });
});
