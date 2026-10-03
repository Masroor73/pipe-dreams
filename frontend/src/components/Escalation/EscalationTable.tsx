import { useMemo, useState } from 'react';
import { CaretDown, CaretUp, CaretUpDown } from '@phosphor-icons/react';
import type { Escalation } from '../../types/api';
import { useAssetLink } from '../../hooks/useAssetLink';
import { formatDate } from '../../lib/format';
import { ConfidencePill, Pill } from '../Pill/Pill';
import styles from './Escalation.module.css';

type SortKey = keyof Escalation;
type Dir = 'asc' | 'desc';

interface Column {
  key: SortKey;
  label: string;
  numeric?: boolean;
}

const COLUMNS: Column[] = [
  { key: 'priority_rank', label: 'Priority rank', numeric: true },
  { key: 'asset_id', label: 'Asset' },
  { key: 'consequence_tier', label: 'Consequence tier' },
  { key: 'evidence_confidence', label: 'Evidence confidence' },
  { key: 'escalation_reason', label: 'Escalation reason' },
  { key: 'owner', label: 'Owner' },
  { key: 'required_action', label: 'Required action' },
  { key: 'response_deadline', label: 'Response deadline' },
  { key: 'status', label: 'Status' },
  { key: 'last_reviewed', label: 'Last reviewed' },
];

const DATE_KEYS: SortKey[] = ['response_deadline', 'last_reviewed'];

/** UI ordering only: compares the provided values, never derives anything. */
function compare(a: Escalation, b: Escalation, key: SortKey): number {
  const av = a[key];
  const bv = b[key];
  if (typeof av === 'number' && typeof bv === 'number') return av - bv;
  if (DATE_KEYS.includes(key)) {
    const ad = Date.parse(String(av));
    const bd = Date.parse(String(bv));
    if (!Number.isNaN(ad) && !Number.isNaN(bd)) return ad - bd;
  }
  return String(av).localeCompare(String(bv), 'en', { numeric: true });
}

/** Colour mapping for known frozen status strings only; unknown values stay neutral. */
function StatusPill({ status }: { status: string }) {
  const tone = status === 'OPEN' ? 'conf-medium' : status === 'IN_REVIEW' ? 'accent' : 'neutral';
  return <Pill tone={tone}>{status}</Pill>;
}

export function EscalationTable({ items }: { items: Escalation[] }) {
  const openAsset = useAssetLink();
  const [sort, setSort] = useState<{ key: SortKey; dir: Dir }>({ key: 'priority_rank', dir: 'asc' });

  const rows = useMemo(() => {
    const sign = sort.dir === 'asc' ? 1 : -1;
    return [...items].sort((a, b) => sign * compare(a, b, sort.key));
  }, [items, sort]);

  const toggle = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }));

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {COLUMNS.map((c) => {
              const active = sort.key === c.key;
              const ariaSort = active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none';
              const Icon = !active ? CaretUpDown : sort.dir === 'asc' ? CaretUp : CaretDown;
              return (
                <th key={c.key} scope="col" aria-sort={ariaSort} className={c.numeric ? styles.numCol : undefined}>
                  <button type="button" className={styles.sortBtn} onClick={() => toggle(c.key)}>
                    {c.label}
                    <Icon size={16} weight={active ? 'bold' : 'regular'} aria-hidden="true" />
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.asset_id}-${r.priority_rank}`}>
              <td className={styles.numCol}>{r.priority_rank}</td>
              <td>
                <button
                  type="button"
                  className={styles.assetBtn}
                  onClick={() => openAsset(r.asset_id)}
                  aria-label={`Open asset ${r.asset_id}`}
                >
                  {r.asset_id}
                </button>
              </td>
              <td>{r.consequence_tier}</td>
              <td>
                <ConfidencePill confidence={r.evidence_confidence} />
              </td>
              <td className={styles.wide}>{r.escalation_reason}</td>
              <td>{r.owner}</td>
              <td className={styles.wide}>{r.required_action}</td>
              <td className={styles.date}>{formatDate(r.response_deadline)}</td>
              <td>
                <StatusPill status={r.status} />
              </td>
              <td className={styles.date}>{formatDate(r.last_reviewed)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
