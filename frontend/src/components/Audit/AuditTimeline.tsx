import type { ReactNode } from 'react';
import {
  CheckCircle,
  ChartLine,
  Flask,
  ListNumbers,
  MagnifyingGlass,
  MapTrifold,
  WarningOctagon,
  XCircle,
} from '@phosphor-icons/react';
import type { AuditEvent } from '../../types/api';
import { formatDate } from '../../lib/format';
import { CandidateGate } from './CandidateGate';
import styles from './Audit.module.css';

type Tone = 'neutral' | 'accept' | 'reject' | 'warn';

function eventStyle(type: string): { icon: ReactNode; tone: Tone } {
  const p = { size: 20, weight: 'bold' as const, 'aria-hidden': true };
  switch (type) {
    case 'PLAN_V1':
      return { icon: <MapTrifold {...p} />, tone: 'neutral' };
    case 'PLAN_V2':
      return { icon: <ListNumbers {...p} />, tone: 'neutral' };
    case 'EVALUATE':
      return { icon: <ChartLine {...p} />, tone: 'neutral' };
    case 'DIAGNOSE':
      return { icon: <MagnifyingGlass {...p} />, tone: 'neutral' };
    case 'TEST_CANDIDATE':
      return { icon: <Flask {...p} />, tone: 'neutral' };
    case 'ACCEPT':
      return { icon: <CheckCircle {...p} />, tone: 'accept' };
    case 'REJECT':
      return { icon: <XCircle {...p} />, tone: 'reject' };
    case 'ESCALATE':
      return { icon: <WarningOctagon {...p} />, tone: 'warn' };
    default:
      return { icon: <ListNumbers {...p} />, tone: 'neutral' };
  }
}

function formatDetailValue(v: unknown): string {
  return typeof v === 'string' ? v : JSON.stringify(v);
}

export interface AuditTimelineProps {
  events: AuditEvent[];
}

const sameCandidate = (a?: AuditEvent, b?: AuditEvent) =>
  !!a?.candidate && !!b?.candidate && a.candidate.candidate_id === b.candidate.candidate_id;

/** Events render in the order supplied. Bracketing is presentation only. */
export function AuditTimeline({ events }: AuditTimelineProps) {
  return (
    <ol className={styles.timeline}>
      {events.map((e, i) => {
        const { icon, tone } = eventStyle(e.event_type);
        const prev = events[i - 1];
        const next = events[i + 1];
        const joinsPrev =
          (e.event_type === 'ACCEPT' || e.event_type === 'REJECT') &&
          prev?.event_type === 'TEST_CANDIDATE' &&
          sameCandidate(prev, e);
        const joinsNext =
          e.event_type === 'TEST_CANDIDATE' &&
          (next?.event_type === 'ACCEPT' || next?.event_type === 'REJECT') &&
          sameCandidate(e, next);
        const detailEntries = Object.entries(e.details ?? {});
        const cls = [
          styles.item,
          styles[`tone_${tone}`],
          joinsNext ? styles.bracketTop : '',
          joinsPrev ? styles.bracketBottom : '',
        ]
          .filter(Boolean)
          .join(' ');
        return (
          <li key={e.seq} className={cls} data-event-type={e.event_type}>
            <span className={styles.node} aria-hidden="true">
              {e.seq}
            </span>
            <div className={styles.card}>
              <div className={styles.cardHead}>
                <span className={styles.type}>
                  {icon}
                  <span className={styles.typeLabel}>{e.event_type}</span>
                </span>
                <span className={styles.seqText}>Step {e.seq}</span>
                <time className={styles.time} dateTime={e.timestamp}>
                  {formatDate(e.timestamp, true)}
                </time>
              </div>
              <p className={styles.summary}>{e.summary}</p>
              {e.candidate && <CandidateGate candidate={e.candidate} />}
              {detailEntries.length > 0 && (
                <details className={styles.details}>
                  <summary>Details</summary>
                  <dl>
                    {detailEntries.map(([k, v]) => (
                      <div key={k} className={styles.detailRow}>
                        <dt>{k}</dt>
                        <dd>{formatDetailValue(v)}</dd>
                      </div>
                    ))}
                  </dl>
                </details>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
