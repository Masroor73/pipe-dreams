import { useMemo, useState } from 'react';
import { CartesianGrid, ErrorBar, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { DataState } from '../DataState/DataState';
import { Section } from '../Section/Section';
import { Term } from '../Term/Term';
import {
  CHART_FONT_PX,
  CHART_HEIGHT,
  CHART_LABEL_LINE_PX,
  CHART_MARGIN_NARROW,
  CHART_MARGIN_WIDE,
  CHART_NARROW_PX,
  CHART_XAXIS_HEIGHT,
  COUNT_ONLY_LABEL,
  COUNT_ONLY_LINE_LABEL,
  HEADLINE_BUDGET_LABEL,
  HEADLINE_BUDGET_PCT,
  ORGANIZER_LABEL,
  ORGANIZER_LINE_LABEL,
  SERIES_LABEL_COLOR,
  SERIES_STYLE,
  WHISKER_SERIES,
  type ChartSeriesKey,
} from '../../config/display';
import { nudgeLabels, type LabelSlot } from './chartLabels';
import { prefersReducedMotion, useInViewOnce } from '../../hooks/motion';
import { EASE_OUT_CSS, MOTION } from '../../hooks/overviewMotion';
import { formatPct } from '../../lib/format';
import type { Resource } from '../../hooks';
import type { Overview, SeriesRow } from '../../types/api';
import styles from './CaptureChart.module.css';

interface SplitOption {
  key: string;
  label: string;
  match: (r: SeriesRow) => boolean;
}

function buildOptions(series: SeriesRow[]): SplitOption[] {
  const options: SplitOption[] = [];
  if (series.some((r) => r.split === 'final')) {
    options.push({ key: 'final', label: 'Final test (2023–2025)', match: (r) => r.split === 'final' });
  }
  const origins = [...new Set(series.filter((r) => r.split === 'validation' && r.origin_cutoff).map((r) => r.origin_cutoff as string))].sort();
  for (const o of origins) {
    options.push({
      key: `val:${o}`,
      label: `Validation · origin ${o.slice(0, 4)}`,
      match: (r) => r.split === 'validation' && r.origin_cutoff === o,
    });
  }
  if (series.some((r) => r.split === 'confirmation')) {
    options.push({ key: 'confirmation', label: 'Confirmation', match: (r) => r.split === 'confirmation' });
  }
  return options;
}

interface Line_ {
  key: ChartSeriesKey;
  policyId: string;
  label: string;
  metric: 'asset_capture' | 'event_capture';
}

interface Point {
  budget: string;
  [k: string]: number | string | null | [number, number];
}

function ChartTooltip({
  active,
  label,
  payload,
  lines,
}: {
  active?: boolean;
  label?: string | number;
  payload?: ReadonlyArray<{ dataKey?: unknown; payload?: Point }>;
  lines: Line_[];
}) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0]?.payload;
  if (!point) return null;
  return (
    <div className={styles.tooltip}>
      <p className={styles.tooltipTitle}>{label} length budget</p>
      <ul>
        {lines.map((l) => {
          const v = point[l.key] as number | null | undefined;
          const lo = point[`${l.key}_lo`] as number | null | undefined;
          const hi = point[`${l.key}_hi`] as number | null | undefined;
          return (
            <li key={l.key}>
              <span className={styles.swatch} style={{ background: SERIES_STYLE[l.key].color }} aria-hidden="true" />
              <span className={styles.tooltipName}>{l.label}</span>
              <span className={styles.tooltipValue}>
                {formatPct(v, 1)}
                {lo != null && hi != null ? ` (${formatPct(lo, 1)}–${formatPct(hi, 1)})` : ''}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** Direct label at the right end of a line; sits in the chart's right margin. */
function LineEndLabel({
  x,
  y,
  index,
  lastIndex,
  lineKey,
  dy,
  narrow,
  text,
}: {
  text: string;
  x: number;
  y: number;
  index: number;
  lastIndex: number;
  lineKey: ChartSeriesKey;
  dy: number;
  narrow: boolean;
}) {
  if (index !== lastIndex || !Number.isFinite(x) || !Number.isFinite(y)) return null;
  const fill = SERIES_LABEL_COLOR[lineKey];
  const weight = lineKey === 'v2' ? 700 : 600;
  const common = { x: x + 10, y: y + dy, fill, fontSize: CHART_FONT_PX, fontWeight: weight, dominantBaseline: 'central' as const };
  if (lineKey === 'organizer_cell' && narrow) {
    return (
      <text {...common} y={y + dy - CHART_LABEL_LINE_PX / 2}>
        <tspan x={x + 10}>Organizer cell</tspan>
        <tspan x={x + 10} dy={CHART_LABEL_LINE_PX}>
          (event capture)
        </tspan>
      </text>
    );
  }
  const shown =
    lineKey === 'organizer_cell'
      ? ORGANIZER_LINE_LABEL
      : lineKey === 'count_only'
        ? COUNT_ONLY_LINE_LABEL
        : text;
  return <text {...common}>{shown}</text>;
}

export function CaptureChart({ overview }: { overview: Resource<Overview> }) {
  const data = overview.data;
  const options = useMemo(() => (data ? buildOptions(data.series) : []), [data]);
  const [chosen, setChosen] = useState<string | null>(null);
  const [plotRef, plotInView] = useInViewOnce<HTMLDivElement>({ threshold: 0.3 });
  // Draw-in plays on first view and on split switch; disabled for reduced motion (lines render complete).
  const animate = !prefersReducedMotion();
  const [switched, setSwitched] = useState(false);
  const [narrow, setNarrow] = useState(false);
  const drawMs = switched ? MOTION.chart.switchDrawMs : MOTION.chart.firstDrawMs;
  const active = options.find((o) => o.key === chosen) ?? options[0];

  const lines = useMemo<Line_[]>(() => {
    if (!data) return [];
    const out: Line_[] = [];
    out.push({ key: 'count_only', policyId: 'count_only', label: COUNT_ONLY_LABEL, metric: 'asset_capture' });
    out.push({ key: 'organizer_cell', policyId: 'organizer_cell', label: ORGANIZER_LABEL, metric: 'event_capture' });
    if (data.v2_equals_v1) {
      out.push({ key: 'v1', policyId: data.v1_policy_id, label: 'V1 = V2', metric: 'asset_capture' });
    } else {
      out.push({ key: 'v1', policyId: data.v1_policy_id, label: 'V1', metric: 'asset_capture' });
      out.push({ key: 'v2', policyId: data.selected_policy_id, label: `V2 (${data.selected_policy_id})`, metric: 'asset_capture' });
    }
    return out;
  }, [data]);

  const points = useMemo<Point[]>(() => {
    if (!data || !active) return [];
    const rows = data.series.filter(active.match);
    return data.budgets_pct.map((b) => {
      const p: Point = { budget: `${b}%` };
      for (const l of lines) {
        const row = rows.find((r) => r.policy_id === l.policyId && r.budget_pct === b);
        const v = row ? row[l.metric] : null;
        p[l.key] = v ?? null;
        p[`${l.key}_lo`] = row?.ci_low ?? null;
        p[`${l.key}_hi`] = row?.ci_high ?? null;
        // Whisker offsets for Recharts' ErrorBar (display geometry only).
        p[`${l.key}_err`] =
          v !== null && v !== undefined && row?.ci_low != null && row?.ci_high != null
            ? [v - row.ci_low, row.ci_high - v]
            : null;
      }
      return p;
    });
  }, [data, active, lines]);

  const visibleLines = lines.filter((l) => points.some((p) => p[l.key] !== null));

  // Axis scaling only: fit the Y axis to the data (incl. whisker tops), rounded up to the next 10%.
  const yMax = useMemo(() => {
    let max = 0;
    for (const p of points) {
      for (const l of visibleLines) {
        for (const k of [l.key, `${l.key}_hi`]) {
          const v = p[k];
          if (typeof v === 'number' && v > max) max = v;
        }
      }
    }
    return Math.max(0.1, Math.ceil(max * 10 - 1e-9) / 10);
  }, [points, visibleLines]);

  // Direct labels: last non-null point per line, nudged apart in pixel space (deterministic).
  const headlineBudget = `${HEADLINE_BUDGET_PCT}%`;
  const margin = narrow ? CHART_MARGIN_NARROW : CHART_MARGIN_WIDE;
  const { lastIndex, nudges } = useMemo(() => {
    const plotH = CHART_HEIGHT - margin.top - margin.bottom - CHART_XAXIS_HEIGHT;
    const last: Record<string, number> = {};
    const slots: LabelSlot[] = [];
    for (const l of visibleLines) {
      let idx = -1;
      points.forEach((p, i) => {
        if (p[l.key] !== null && p[l.key] !== undefined) idx = i;
      });
      last[l.key] = idx;
      const v = idx >= 0 ? (points[idx]![l.key] as number) : 0;
      slots.push({
        key: l.key,
        y: (1 - v / yMax) * plotH,
        height: (narrow && l.key === 'organizer_cell' ? 2 : 1) * CHART_LABEL_LINE_PX,
      });
    }
    return { lastIndex: last, nudges: nudgeLabels(slots, plotH) };
  }, [visibleLines, points, yMax, narrow, margin.top, margin.bottom]);

  return (
    <Section
      id="capture"
      variant="supporting"
      title="Capture by length budget"
      description="Share of future breaking assets found when inspecting only the first slice of the ranked network."
    >
      <DataState
        status={overview.status}
        errorMessage={overview.error?.message}
        onRetry={overview.reload}
        empty={overview.status === 'success' && options.length === 0}
        emptyMessage="No capture results available yet"
        loadingLabel="Loading capture chart"
        minHeight={CHART_HEIGHT}
      >
        <div className={styles.card}>
          <div className={styles.toolbar}>
            <div className={styles.segmented} role="group" aria-label="Evaluation split">
              {options.map((o) => (
                <button
                  key={o.key}
                  type="button"
                  className={styles.segment}
                  aria-pressed={o.key === active?.key}
                  onClick={() => {
                    setChosen(o.key);
                    setSwitched(true);
                  }}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          <div
            ref={plotRef}
            className={styles.plot}
            role="img"
            aria-label={`Line chart of capture by length budget. Series: ${visibleLines.map((l) => l.label).join('; ')}.`}
          >
            <ResponsiveContainer
              width="100%"
              height={CHART_HEIGHT}
              initialDimension={{ width: 900, height: CHART_HEIGHT }}
              onResize={(w) => setNarrow(w < CHART_NARROW_PX)}
            >
              <LineChart data={points} margin={{ ...margin }}>
                <CartesianGrid stroke="#e4e9ef" strokeOpacity={0.9} vertical={false} />
                <XAxis
                  dataKey="budget"
                  tick={{ fontSize: CHART_FONT_PX, fill: '#4a5b6d' }}
                  tickLine={false}
                  axisLine={{ stroke: '#d9e0e8' }}
                  label={{ value: 'Length budget', position: 'insideBottom', offset: -4, fontSize: CHART_FONT_PX, fill: '#4a5b6d' }}
                  height={CHART_XAXIS_HEIGHT}
                />
                <YAxis
                  tickFormatter={(v: number) => formatPct(v, 0)}
                  tick={{ fontSize: CHART_FONT_PX, fill: '#4a5b6d' }}
                  tickLine={false}
                  axisLine={false}
                  width={narrow ? 44 : 56}
                  domain={[0, yMax]}
                  tickCount={Math.round(yMax * 10) + 1}
                  allowDecimals
                />
                <Tooltip content={<ChartTooltip lines={visibleLines} />} cursor={{ stroke: '#d9e0e8' }} />
                {points.some((p) => p.budget === headlineBudget) && (
                  <ReferenceLine
                    x={headlineBudget}
                    stroke="#a9d2e5"
                    strokeWidth={1.5}
                    ifOverflow="visible"
                    label={{ value: HEADLINE_BUDGET_LABEL, position: 'top', fontSize: CHART_FONT_PX, fontWeight: 600, fill: '#095a7e' }}
                  />
                )}
                {[...visibleLines].reverse().map((l, i) => (
                  <Line
                    // Re-keyed per split (and once when first in view) so the draw-in replays; old lines unmount instantly.
                    key={`${active?.key}:${plotInView}:${l.key}`}
                    isAnimationActive={animate}
                    animationBegin={i * MOTION.chart.seriesStaggerMs}
                    animationDuration={drawMs}
                    animationEasing={EASE_OUT_CSS}
                    type="monotone"
                    dataKey={l.key}
                    name={l.label}
                    stroke={SERIES_STYLE[l.key].color}
                    strokeWidth={SERIES_STYLE[l.key].width}
                    strokeDasharray={SERIES_STYLE[l.key].dash}
                    dot={{ r: 3, strokeWidth: 0, fill: SERIES_STYLE[l.key].color }}
                    activeDot={{ r: 5 }}
                    connectNulls={false}
                    label={(p: { x?: number | string; y?: number | string; index?: number }) => (
                      <LineEndLabel
                        key={`${l.key}:${p.index}`}
                        x={Number(p.x)}
                        y={Number(p.y)}
                        index={p.index ?? -1}
                        lastIndex={lastIndex[l.key] ?? -1}
                        lineKey={l.key}
                        dy={nudges[l.key] ?? 0}
                        narrow={narrow}
                        text={l.label}
                      />
                    )}
                  >
                    {WHISKER_SERIES.includes(l.key) && (
                      <ErrorBar
                        isAnimationActive={animate}
                        animationBegin={i * MOTION.chart.seriesStaggerMs + drawMs}
                        animationDuration={MOTION.chart.whiskerFadeMs}
                        animationEasing={EASE_OUT_CSS}
                        dataKey={`${l.key}_err`}
                        width={4}
                        strokeWidth={1}
                        stroke={SERIES_STYLE[l.key].color}
                        opacity={0.5}
                      />
                    )}
                  </Line>
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <p className={styles.note}>
            <Term id="capture">Asset capture</Term> = share of future breaking assets inside the inspected{' '}
            <Term id="length_budget">length budget</Term>. Whiskers (V2 and count-only) show the confidence interval. The{' '}
            <Term id="organizer_cell">organizer cell baseline</Term> is cell-based, so it is plotted as event capture
            (dotted line).
          </p>
        </div>
      </DataState>
    </Section>
  );
}
