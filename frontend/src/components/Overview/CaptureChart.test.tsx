import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { beforeAll, describe, expect, it } from 'vitest';
import overviewFixture from '../../fixtures/overview.json';
import type { Resource } from '../../hooks';
import type { Overview } from '../../types/api';
import { CaptureChart } from './CaptureChart';
import { nudgeLabels } from './chartLabels';

const overview: Resource<Overview> = {
  status: 'success',
  data: overviewFixture.data as unknown as Overview,
  meta: undefined,
  error: undefined,
  reload: () => undefined,
};

beforeAll(() => {
  // jsdom has no layout: report a fixed size so Recharts renders the plot.
  globalThis.ResizeObserver = class {
    constructor(private cb: ResizeObserverCallback) {}
    observe(target: Element) {
      const rect = { width: 900, height: 360, x: 0, y: 0, top: 0, left: 0, right: 900, bottom: 360, toJSON: () => ({}) };
      this.cb(
        [{ target, contentRect: rect, borderBoxSize: [], contentBoxSize: [], devicePixelContentBoxSize: [] } as unknown as ResizeObserverEntry],
        this as unknown as ResizeObserver,
      );
    }
    unobserve() {}
    disconnect() {}
  };
});

describe('CaptureChart', () => {
  it('labels each line directly and marks the 5% headline budget', () => {
    const { container } = render(
      <MemoryRouter>
        <CaptureChart overview={overview} />
      </MemoryRouter>,
    );
    const svgText =Array.from(container.querySelectorAll('svg text')).map((t) => t.textContent);
    expect(svgText).toContain('V2 (C2)');
    expect(svgText).toContain('V1');
    expect(svgText).toContain('Count-only');
    expect(svgText).toContain('Organizer cell (event capture)');
    expect(svgText).toContain('5% budget (headline)');
    expect(container.querySelector('ul[aria-label="Series"]')).toBeNull();
  });

  it('accepts numeric validation cutoff years from real artifacts', () => {
    const data = overviewFixture.data as unknown as Overview;
    const numeric: Resource<Overview> = {
      ...overview,
      data: {
        ...data,
        series: data.series.map((r) =>
          r.origin_cutoff ? { ...r, origin_cutoff: Number(String(r.origin_cutoff).slice(0, 4)) } : r,
        ),
      },
    };
    const { getByText } = render(
      <MemoryRouter>
        <CaptureChart overview={numeric} />
      </MemoryRouter>,
    );
    expect(getByText('Validation · origin 2013')).toBeTruthy();
  });
});

describe('nudgeLabels', () => {
  it('separates colliding labels deterministically and keeps order', () => {
    const slots = [
      { key: 'a', y: 100, height: 18 },
      { key: 'b', y: 102, height: 18 },
      { key: 'c', y: 104, height: 18 },
    ];
    const dy = nudgeLabels(slots, 300);
    const ys = slots.map((s) => s.y + dy[s.key]!);
    expect(ys[1]! - ys[0]!).toBeGreaterThanOrEqual(18);
    expect(ys[2]! - ys[1]!).toBeGreaterThanOrEqual(18);
    expect(nudgeLabels(slots, 300)).toEqual(dy);
  });

  it('keeps labels inside the plot bottom', () => {
    const dy = nudgeLabels([{ key: 'a', y: 299, height: 18 }, { key: 'b', y: 300, height: 18 }], 300);
    expect(299 + dy.a! + 18).toBeLessThanOrEqual(300 + 1);
    expect(300 + dy.b!).toBeLessThanOrEqual(300);
  });
});
