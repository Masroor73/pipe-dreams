import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import overviewFixture from '../../fixtures/overview.json';
import { runCountUp } from '../../hooks/countUp';
import type { Resource } from '../../hooks';
import { formatPct } from '../../lib/format';
import { MetaProvider } from '../../lib/synthetic';
import type { Overview } from '../../types/api';
import { AnimatedValue } from './AnimatedValue';
import { GateCards } from './GateCards';
import { RankChangeCards } from './RankChangeCards';

const overview: Resource<Overview> = {
  status: 'success',
  data: overviewFixture.data as unknown as Overview,
  meta: undefined,
  error: undefined,
  reload: () => undefined,
};

/** Simulate a browser with motion enabled and everything immediately in view. */
function enableMotion() {
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockReturnValue({ matches: false, addEventListener: () => undefined, removeEventListener: () => undefined }),
  );
  class IO {
    constructor(private cb: IntersectionObserverCallback) {}
    observe(el: Element) {
      this.cb([{ isIntersecting: true, target: el } as IntersectionObserverEntry], this as unknown as IntersectionObserver);
    }
    disconnect() {}
    unobserve() {}
  }
  vi.stubGlobal('IntersectionObserver', IO);
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('runCountUp', () => {
  beforeEach(() => vi.useFakeTimers());

  it('ticks monotonically and ends exactly on the target', () => {
    const frames: number[] = [];
    runCountUp({ from: 0, to: 0.2437, durationMs: 600, onFrame: (v) => frames.push(v) });
    vi.advanceTimersByTime(1000);
    expect(frames.length).toBeGreaterThan(3);
    expect(frames[frames.length - 1]).toBe(0.2437);
    for (let i = 1; i < frames.length; i++) expect(frames[i]!).toBeGreaterThanOrEqual(frames[i - 1]!);
  });

  it('rounds intermediate integer ticks and ends on the exact rank', () => {
    const frames: number[] = [];
    runCountUp({ from: 40, to: 3, durationMs: 320, integer: true, onFrame: (v) => frames.push(v) });
    vi.advanceTimersByTime(600);
    expect(frames.every(Number.isInteger)).toBe(true);
    expect(frames[frames.length - 1]).toBe(3);
  });

  it('can be cancelled', () => {
    const onFrame = vi.fn();
    const cancel = runCountUp({ from: 0, to: 1, durationMs: 600, onFrame });
    cancel();
    vi.advanceTimersByTime(1000);
    expect(onFrame).not.toHaveBeenCalled();
  });
});

describe('AnimatedValue', () => {
  it('renders the final formatted value immediately under reduced motion (jsdom default)', () => {
    render(<AnimatedValue value={0.24} format={(n) => formatPct(n, 0)} />);
    expect(screen.getByText('24%')).toBeInTheDocument();
  });

  it('counts up with motion enabled, exposes the final value to AT, and ends on the API value', () => {
    enableMotion();
    vi.useFakeTimers();
    const { container } = render(<AnimatedValue value={0.24} format={(n) => formatPct(n, 0)} />);
    // While running: ticking text is aria-hidden and the final value is still in the DOM.
    expect(container.querySelector('[aria-hidden="true"]')).not.toBeNull();
    expect(screen.getByText('24%')).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(container.querySelector('[aria-hidden="true"]')).toBeNull();
    expect(container).toHaveTextContent(/^24%$/);
  });
});

describe('GateCards motion', () => {
  function renderCards() {
    return render(
      <MetaProvider>
        <MemoryRouter>
          <GateCards overview={overview} />
        </MemoryRouter>
      </MetaProvider>,
    );
  }

  it('shows final outcomes and "Selected as V2" immediately under reduced motion', async () => {
    renderCards();
    expect(await screen.findByText('Selected as V2')).toBeInTheDocument();
    expect(document.querySelectorAll('[data-candidate]')).toHaveLength(4);
    expect(screen.getAllByText(/^(PASSED|FAILED)/).length).toBe(4);
  });

  it('plays a from-only sequence in card order with motion enabled, and Escape finishes it', async () => {
    enableMotion();
    const finish = vi.fn();
    const calls: { delay: number; el: string }[] = [];
    Element.prototype.animate = function (this: HTMLElement, _kf: unknown, o: KeyframeAnimationOptions) {
      calls.push({ delay: Number(o.delay), el: this.dataset.anim ?? '' });
      return { playState: 'running', finish } as unknown as Animation;
    } as never;
    renderCards();
    await screen.findByText('Selected as V2');
    const stamps = calls.filter((c) => c.el === 'stamp').map((c) => c.delay);
    expect(stamps).toEqual([470, 870, 1270, 1670]);
    expect(calls.find((c) => c.el === 'ring')?.delay).toBe(1800);
    // End state is already in the DOM.
    expect(screen.getByText('Selected as V2')).toBeInTheDocument();
    await userEvent.keyboard('{Escape}');
    expect(finish).toHaveBeenCalled();
    delete (Element.prototype as { animate?: unknown }).animate;
  });
});

describe('RankChangeCards end state', () => {
  it('shows V1 and V2 ranks from the API', async () => {
    render(
      <MetaProvider>
        <MemoryRouter>
          <RankChangeCards />
        </MemoryRouter>
      </MetaProvider>,
    );
    expect(await screen.findByText('#40 → #3')).toBeInTheDocument();
  });

  it('shows the real V2 rank with motion enabled even before the card scrolls into view', async () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({ matches: false, addEventListener: () => undefined, removeEventListener: () => undefined }),
    );
    // Observer that never fires: the card is off-screen (or being printed / screenshotted).
    class IdleIO {
      observe() {}
      disconnect() {}
      unobserve() {}
    }
    vi.stubGlobal('IntersectionObserver', IdleIO);
    render(
      <MetaProvider>
        <MemoryRouter>
          <RankChangeCards />
        </MemoryRouter>
      </MetaProvider>,
    );
    expect(await screen.findByText('#40 → #3')).toBeInTheDocument();
    expect(screen.queryByText('#40 → #40')).not.toBeInTheDocument();
  });
});
