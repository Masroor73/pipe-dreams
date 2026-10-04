import type { ReactNode } from 'react';
import { CheckCircle, Question, ShieldCheck, ShieldWarning, XCircle } from '@phosphor-icons/react';
import type { CandidateDecision, EvidenceConfidence } from '../../types/api';
import styles from './Pill.module.css';

type Tone = 'neutral' | 'accent' | 'accept' | 'reject' | 'conf-high' | 'conf-medium' | 'conf-low';

export interface PillProps {
  tone?: Tone;
  icon?: ReactNode;
  children: ReactNode;
}

/** Generic pill. Labels are always the raw API strings. */
export function Pill({ tone = 'neutral', icon, children }: PillProps) {
  return (
    <span className={`${styles.pill} ${styles[tone]}`}>
      {icon}
      {children}
    </span>
  );
}

/**
 * ACCEPT -> "PASSED", REJECT -> "FAILED" (the raw API value stays in the title).
 * `selected` marks the passing candidate adopted as V2; `selectedId` (the adopted candidate)
 * adds a hint on other passing candidates.
 */
export function DecisionPill({
  decision,
  selected = false,
  selectedId = null,
}: {
  decision: CandidateDecision;
  selected?: boolean;
  selectedId?: string | null;
}) {
  if (decision !== 'ACCEPT') {
    return (
      <Pill tone="reject" icon={<XCircle size={16} weight="fill" aria-hidden="true" />}>
        <span title={decision}>FAILED</span>
      </Pill>
    );
  }
  return (
    <span className={styles.decision}>
      <Pill tone={selected ? 'accent' : 'accept'} icon={<CheckCircle size={16} weight="fill" aria-hidden="true" />}>
        <span title={decision}>{selected ? 'PASSED · SELECTED AS V2' : 'PASSED'}</span>
      </Pill>
      {!selected && selectedId && <span className={styles.hint}>passed, but {selectedId} scored higher</span>}
    </span>
  );
}

/** HIGH / MEDIUM / LOW_VERIFY. Icon + label so colour is never the only cue. */
export function ConfidencePill({ confidence }: { confidence: EvidenceConfidence }) {
  if (confidence === 'HIGH') {
    return (
      <Pill tone="conf-high" icon={<ShieldCheck size={16} weight="fill" aria-hidden="true" />}>
        {confidence}
      </Pill>
    );
  }
  if (confidence === 'MEDIUM') {
    return (
      <Pill tone="conf-medium" icon={<ShieldWarning size={16} weight="fill" aria-hidden="true" />}>
        {confidence}
      </Pill>
    );
  }
  return (
    <Pill tone="conf-low" icon={<Question size={16} weight="bold" aria-hidden="true" />}>
      {confidence}
    </Pill>
  );
}
