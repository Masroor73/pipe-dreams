import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import auditFixture from '../fixtures/audit.json';
import { AUDIT_CINEMA } from '../config/display';
import { ApiError, api } from '../lib/api';
import { MetaProvider } from '../lib/synthetic';
import type { Audit, Envelope } from '../types/api';
import AuditPage from './AuditPage';

const meta = { synthetic: false, config_hash: 'abc' };

function renderPage() {
  return render(
    <MetaProvider>
      <MemoryRouter>
        <AuditPage />
      </MemoryRouter>
    </MetaProvider>,
  );
}

const audit: Envelope<Audit> = {
  meta,
  data: {
    events: [
      { seq: 1, event_type: 'PLAN_V1', timestamp: '2026-10-03T14:04:56Z', summary: 'first thing', candidate: null, details: { policy_id: 'V1' } },
      {
        seq: 2,
        event_type: 'TEST_CANDIDATE',
        timestamp: '2026-10-03T14:10:00Z',
        summary: 'second thing',
        candidate: {
          candidate_id: 'C2',
          origin_wins: 3,
          n_origins: 3,
          pooled_v1_score: 0.19,
          pooled_candidate_score: 0.205,
          difference: 0.015,
          bootstrap_se: 0.004,
          required_delta: 0.004,
          decision: 'ACCEPT',
          reason: 'won all origins',
        },
        details: {},
      },
      { seq: 3, event_type: 'ESCALATE', timestamp: '2026-10-03T14:20:00Z', summary: 'third thing', candidate: null, details: {} },
    ],
  },
};

afterEach(() => vi.restoreAllMocks());

describe('AuditPage', () => {
  it('renders all events in the order given with candidate decision from data', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    expect(await screen.findByText('first thing')).toBeInTheDocument();
    const items = screen.getAllByRole('listitem').filter((li) => li.hasAttribute('data-event-type'));
    expect(items.map((li) => li.getAttribute('data-event-type'))).toEqual(['PLAN_V1', 'TEST_CANDIDATE', 'ESCALATE']);
    const table = screen.getByRole('table', { name: /revision gate result for C2/i });
    expect(within(table).getByText('ACCEPT')).toBeInTheDocument();
    expect(within(table).getByText('0.205')).toBeInTheDocument();
    expect(screen.getByText('won all origins')).toBeInTheDocument();
  });

  it('shows the gate table once per candidate when a test is followed by its decision', async () => {
    const test = audit.data.events[1]!;
    const grouped: Envelope<Audit> = {
      meta,
      data: {
        events: [
          test,
          { ...test, seq: 3, event_type: 'ACCEPT', summary: 'accepted C2' },
        ],
      },
    };
    vi.spyOn(api, 'getAudit').mockResolvedValue(grouped);
    renderPage();
    expect((await screen.findAllByText('accepted C2')).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('table')).toHaveLength(1);
    expect(screen.getByText('second thing')).toBeInTheDocument();
  });

  it('has no event-type filter or redundant step text', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    await screen.findByText('first thing');
    expect(screen.queryByRole('group', { name: /filter by event type/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/^Step \d/)).not.toBeInTheDocument();
  });

  it('shows details as key/value pairs', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    expect(await screen.findByText('policy_id')).toBeInTheDocument();
  });

  it('shows the empty state', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue({ meta, data: { events: [] } });
    renderPage();
    expect(await screen.findByText('No audit events recorded.')).toBeInTheDocument();
  });

  it('shows the error state', async () => {
    vi.spyOn(api, 'getAudit').mockRejectedValue(new ApiError(500, 'boom', 'Audit exploded'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('Audit exploded');
  });
});

describe('AuditPage agent-run cinema', () => {
  const dimmedSeqs = () =>
    screen
      .getAllByRole('listitem')
      .filter((li) => li.hasAttribute('data-event-type') && /future/.test(li.className))
      .map((li) => li.getAttribute('data-seq'));
  const region = () => screen.getByRole('region', { name: 'Agent run replay' });
  const step = () => Number(region().getAttribute('data-step'));

  const motionAllowed = () =>
    vi.stubGlobal('matchMedia', (q: string) => ({
      matches: false,
      media: q,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    }));

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('opens on the end state with nothing dimmed', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    await screen.findByText('first thing');
    expect(step()).toBe(2);
    expect(screen.getByRole('button', { name: 'Play agent run' })).toBeInTheDocument();
    expect(dimmedSeqs()).toEqual([]);
  });

  it('Play restarts from step 1 and advances one event per dwell, in seq order, then stops', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    await screen.findByText('first thing');
    motionAllowed();
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole('button', { name: 'Play agent run' }));
    expect(step()).toBe(0);
    expect(dimmedSeqs()).toEqual(['2', '3']);
    expect(screen.getByRole('button', { name: 'Pause agent run' })).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(AUDIT_CINEMA.dwellMs.PLAN_V1!));
    expect(step()).toBe(1);
    expect(dimmedSeqs()).toEqual(['3']);
    act(() => void vi.advanceTimersByTime(AUDIT_CINEMA.dwellMs.TEST_CANDIDATE!));
    expect(step()).toBe(2);
    expect(dimmedSeqs()).toEqual([]);
    act(() => void vi.advanceTimersByTime(5000));
    expect(step()).toBe(2);
    expect(screen.getByRole('button', { name: 'Play agent run' })).toBeInTheDocument();
  });

  it('keyboard: arrows step, Home/End jump, Space plays and pauses', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    await screen.findByText('first thing');
    fireEvent.keyDown(region(), { key: 'ArrowLeft' });
    expect(step()).toBe(1);
    fireEvent.keyDown(region(), { key: 'Home' });
    expect(step()).toBe(0);
    fireEvent.keyDown(region(), { key: 'ArrowRight' });
    expect(step()).toBe(1);
    fireEvent.keyDown(region(), { key: 'End' });
    expect(step()).toBe(2);
    fireEvent.keyDown(region(), { key: ' ' });
    expect(screen.getByRole('button', { name: 'Pause agent run' })).toBeInTheDocument();
    fireEvent.keyDown(region(), { key: ' ' });
    expect(screen.getByRole('button', { name: 'Play agent run' })).toBeInTheDocument();
  });

  it('the scrubber sets the step and announces it', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    await screen.findByText('first thing');
    fireEvent.change(screen.getByRole('slider', { name: 'Agent run step' }), { target: { value: '1' } });
    expect(step()).toBe(1);
    expect(await screen.findByText(/^Step 2 of 3: TEST_CANDIDATE/)).toBeInTheDocument();
  });

  it('a candidate shows Testing on its test step and its artifact decision afterwards', async () => {
    const withDecision: Envelope<Audit> = {
      meta,
      data: {
        events: [
          audit.data.events[0]!,
          audit.data.events[1]!,
          { ...audit.data.events[1]!, seq: 3, event_type: 'ACCEPT', summary: 'accepted C2' },
        ],
      },
    };
    vi.spyOn(api, 'getAudit').mockResolvedValue(withDecision);
    renderPage();
    await screen.findByText('first thing');
    const gateRow = () => region().querySelector<HTMLElement>('[data-candidate="C2"]')!;
    fireEvent.keyDown(region(), { key: 'Home' });
    expect(gateRow().getAttribute('data-stage')).toBe('pending');
    fireEvent.keyDown(region(), { key: 'ArrowRight' });
    expect(gateRow().getAttribute('data-stage')).toBe('testing');
    expect(within(gateRow()).queryByText('ACCEPT')).not.toBeInTheDocument();
    fireEvent.keyDown(region(), { key: 'ArrowRight' });
    expect(gateRow().getAttribute('data-stage')).toBe('resolved');
    expect(within(gateRow()).getByText('ACCEPT')).toBeInTheDocument();
  });
});

describe('AuditPage cinema: Top 25 reorder and reduced motion', () => {
  // Fixture-mode API: full audit, V1 and V2 asset lists.
  const region = () => screen.getByRole('region', { name: 'Agent run replay' });
  const listIds = () => Array.from(region().querySelectorAll('[data-flip-key]')).map((el) => el.getAttribute('data-flip-key'));
  let animate: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    animate = vi.fn(() => ({ cancel: () => undefined, finish: () => undefined, addEventListener: () => undefined }));
    Element.prototype.animate = animate as never;
    // Layout stub: each element's y is its index among its siblings.
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (this: Element) {
      const parent = this.parentElement;
      const i = parent ? Array.from(parent.children).indexOf(this) : 0;
      return { left: 0, top: i * 30, right: 100, bottom: i * 30 + 28, width: 100, height: 28, x: 0, y: i * 30, toJSON: () => ({}) } as DOMRect;
    });
  });
  afterEach(() => {
    delete (Element.prototype as { animate?: unknown }).animate;
    vi.unstubAllGlobals();
  });

  // Real API lists for the same assets in a different order (V2 reverses V1).
  const item = (id: string, rank: number) => ({
    asset_id: id,
    rank,
    selected: rank <= 2,
    length_m: 100,
    priority_score: 1 - rank / 10,
    consequence_tier: 'T1',
    evidence_confidence: 'HIGH' as const,
    recommended_action: 'INSPECT',
    latitude: 51 + rank / 100,
    longitude: -114 + rank / 100,
  });
  function mockLists() {
    const ids = ['seg_a', 'seg_b', 'seg_c', 'seg_d'];
    vi.spyOn(api, 'getAssets').mockImplementation(async (q = {}) => {
      const order = q.plan === 'v1' ? ids : [...ids].reverse();
      const items = order.map((id, i) => item(id, i + 1));
      return { meta, data: { plan: q.plan ?? 'v2', total: items.length, limit: 25, offset: 0, items } };
    });
  }

  async function openBeforePlanV2() {
    mockLists();
    renderPage();
    await waitFor(() => expect(region().querySelectorAll('[data-flip-key]').length).toBeGreaterThan(0));
    const slider = screen.getByRole('slider', { name: 'Agent run step' });
    const v2Step = auditFixture.data.events.findIndex((e) => e.event_type === 'PLAN_V2');
    fireEvent.change(slider, { target: { value: String(v2Step - 1) } });
    expect(region().getAttribute('data-plan')).toBe('v1');
    return { slider, v2Step };
  }

  it('with motion: stepping into PLAN_V2 swaps to the V2 order with FLIP moves (transform/opacity only)', async () => {
    vi.stubGlobal('matchMedia', (q: string) => ({ matches: false, media: q, addEventListener: () => undefined, removeEventListener: () => undefined }));
    const { slider, v2Step } = await openBeforePlanV2();
    const v1Order = listIds();
    animate.mockClear();
    fireEvent.change(slider, { target: { value: String(v2Step) } });
    expect(region().getAttribute('data-plan')).toBe('v2');
    expect(listIds()).not.toEqual(v1Order);
    const flips = animate.mock.calls.filter(([kf]) => Array.isArray(kf) && String((kf as Keyframe[])[0]!.transform ?? '').startsWith('translate'));
    expect(flips.length).toBeGreaterThan(0);
    for (const [kf] of animate.mock.calls) {
      for (const frame of kf as Keyframe[]) {
        expect(Object.keys(frame).every((k) => ['transform', 'opacity', 'offset'].includes(k))).toBe(true);
      }
    }
  });

  it('under reduced motion: jumps to the V2 end state; changed rows only cross-fade (no movement)', async () => {
    // jsdom has no matchMedia, which the app treats as reduced motion.
    const { slider, v2Step } = await openBeforePlanV2();
    animate.mockClear();
    fireEvent.change(slider, { target: { value: String(v2Step) } });
    expect(region().getAttribute('data-plan')).toBe('v2');
    expect(listIds().length).toBeGreaterThan(0);
    // A gentle fade still marks the change...
    expect(animate).toHaveBeenCalled();
    for (const [kf, opts] of animate.mock.calls as unknown as [Keyframe[], KeyframeAnimationOptions][]) {
      // ...but only opacity, and short.
      for (const frame of kf) expect(Object.keys(frame).filter((k) => k !== 'offset')).toEqual(['opacity']);
      expect(Number(opts.duration)).toBeLessThanOrEqual(150);
    }
    expect(region().querySelectorAll('[data-ring]')).toHaveLength(0);
  });
});
