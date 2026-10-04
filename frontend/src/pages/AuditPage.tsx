import { useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router';
import { useAudit } from '../hooks';
import { Term } from '../components/Term/Term';
import { AgentCinema } from '../components/Audit/AgentCinema';
import { replayOrder } from '../components/Audit/replayFrames';
import { useCinema } from '../components/Audit/useCinema';
import { DataState } from '../components/DataState/DataState';
import { AuditTimeline } from '../components/Audit/AuditTimeline';
import styles from './AuditPage.module.css';

export default function AuditPage() {
  const { status, data, error, reload } = useAudit();
  const events = useMemo(() => data?.events ?? [], [data]);
  const sorted = useMemo(() => replayOrder(events), [events]);
  const order = useMemo(() => sorted.map((e) => e.seq), [sorted]);
  const cinema = useCinema(sorted);

  // One-shot: /audit?replay=1 (from the voice copilot) starts playback of the logged decisions, then clears the flag.
  const [params, setParams] = useSearchParams();
  const replayRequested = params.get('replay') === '1';
  const { play } = cinema;
  useEffect(() => {
    if (!replayRequested || sorted.length === 0) return;
    play();
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete('replay');
        return next;
      },
      { replace: true },
    );
  }, [replayRequested, sorted, play, setParams]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Agent audit</h1>
        <p className={styles.intro}>
          Autonomous loop: plan <Term id="v1">V1</Term> → evaluate → diagnose → test{' '}
          <Term id="candidates">candidates</Term> → accept/reject → plan <Term id="v2">V2</Term>
        </p>
      </header>
      <DataState
        status={status}
        errorMessage={error?.message}
        onRetry={reload}
        empty={status === 'success' && events.length === 0}
        emptyMessage="No audit events recorded."
        loadingLabel="Loading audit trail"
        minHeight={320}
      >
        <AgentCinema sorted={sorted} cinema={cinema} />
        <h2 className={styles.trailTitle}>Full audit trail</h2>
        <AuditTimeline events={events} step={cinema.engaged ? cinema.step : null} replayOrder={order} />
      </DataState>
    </div>
  );
}
