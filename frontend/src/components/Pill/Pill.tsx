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

/** ACCEPT / REJECT. Colour mapping only. */
export function DecisionPill({ decision }: { decision: CandidateDecision }) {
  return decision === 'ACCEPT' ? (
    <Pill tone="accept" icon={<CheckCircle size={16} weight="fill" aria-hidden="true" />}>
      {decision}
    </Pill>
  ) : (
    <Pill tone="reject" icon={<XCircle size={16} weight="fill" aria-hidden="true" />}>
      {decision}
    </Pill>
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
