import { useMemo, useState } from 'react';
import { CartesianGrid, ErrorBar, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { DataState } from '../DataState/DataState';
import { Section } from '../Section/Section';
import {
  CHART_HEIGHT,
  COUNT_ONLY_LABEL,
  ORGANIZER_LABEL,
  SERIES_STYLE,
  type ChartSeriesKey,
} from '../../config/display';
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

export function CaptureChart({ overview }: { overview: Resource<Overview> }) {
  const data = overview.data;
  const options = useMemo(() => (data ? buildOptions(data.series) : []), [data]);
  const [chosen, setChosen] = useState<string | null>(null);
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

  return (
    <Section
      id="capture"
      eyebrow="Evidence"
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
                  onClick={() => setChosen(o.key)}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          <ul className={styles.legend} aria-label="Series">
            {visibleLines.map((l) => (
              <li key={l.key}>
                <svg width="28" height="10" aria-hidden="true">
                  <line
                    x1="0"
                    y1="5"
                    x2="28"
                    y2="5"
                    stroke={SERIES_STYLE[l.key].color}
                    strokeWidth={SERIES_STYLE[l.key].width}
                    strokeDasharray={SERIES_STYLE[l.key].dash}
                  />
                </svg>
                {l.label}
              </li>
            ))}
          </ul>

          <div className={styles.plot} role="img" aria-label="Line chart of capture by length budget">
            <ResponsiveContainer width="100%" height={CHART_HEIGHT} initialDimension={{ width: 900, height: CHART_HEIGHT }}>
              <LineChart data={points} margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="#d9e0e8" vertical={false} />
                <XAxis
                  dataKey="budget"
                  tick={{ fontSize: 14, fill: '#4a5b6d' }}
                  tickLine={false}
                  axisLine={{ stroke: '#b6c2cf' }}
                  label={{ value: 'Length budget', position: 'insideBottom', offset: -4, fontSize: 14, fill: '#4a5b6d' }}
                  height={48}
                />
                <YAxis
                  tickFormatter={(v: number) => formatPct(v, 0)}
                  tick={{ fontSize: 14, fill: '#4a5b6d' }}
                  tickLine={false}
                  axisLine={false}
                  width={56}
                  domain={[0, 'auto']}
                />
                <Tooltip content={<ChartTooltip lines={visibleLines} />} cursor={{ stroke: '#b6c2cf' }} />
                {[...visibleLines].reverse().map((l) => (
                  <Line
                    key={l.key}
                    type="monotone"
                    dataKey={l.key}
                    name={l.label}
                    stroke={SERIES_STYLE[l.key].color}
                    strokeWidth={SERIES_STYLE[l.key].width}
                    strokeDasharray={SERIES_STYLE[l.key].dash}
                    dot={{ r: 4, strokeWidth: 0, fill: SERIES_STYLE[l.key].color }}
                    activeDot={{ r: 6 }}
                    connectNulls={false}
                  >
                    <ErrorBar dataKey={`${l.key}_err`} width={5} strokeWidth={1.5} stroke={SERIES_STYLE[l.key].color} opacity={0.55} />
                  </Line>
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <p className={styles.note}>
            Asset capture = share of future breaking assets inside the inspected length budget. Whiskers show the
            confidence interval. The organizer baseline is cell-based, so it is plotted as event capture.
          </p>
        </div>
      </DataState>
    </Section>
  );
}
