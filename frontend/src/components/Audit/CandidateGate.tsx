import type { CandidateResult } from '../../types/api';
import { DecisionPill } from '../Pill/Pill';
import { Term } from '../Term/Term';
import { formatNumber } from '../../lib/format';
import styles from './Audit.module.css';

/** Gate numbers exactly as supplied by the artifact. */
export function CandidateGate({ candidate }: { candidate: CandidateResult }) {
  const c = candidate;
  return (
    <div className={styles.gateWrap}>
      <table className={styles.gate}>
        <caption className={styles.srOnly}>Revision gate result for {c.candidate_id}</caption>
        <thead>
          <tr>
            <th scope="col">Candidate</th>
            <th scope="col">Origin wins</th>
            <th scope="col">Pooled V1</th>
            <th scope="col">Pooled candidate</th>
            <th scope="col">Difference</th>
            <th scope="col">
              <Term id="bootstrap_se">Bootstrap SE</Term>
            </th>
            <th scope="col">Required delta</th>
            <th scope="col">Decision</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">{c.candidate_id}</th>
            <td className={styles.num}>
              {c.origin_wins} / {c.n_origins}
            </td>
            <td className={styles.num}>{formatNumber(c.pooled_v1_score, 3)}</td>
            <td className={styles.num}>{formatNumber(c.pooled_candidate_score, 3)}</td>
            <td className={styles.num}>{formatNumber(c.difference, 3)}</td>
            <td className={styles.num}>{formatNumber(c.bootstrap_se, 3)}</td>
            <td className={styles.num}>{formatNumber(c.required_delta, 3)}</td>
            <td>
              <DecisionPill decision={c.decision} />
            </td>
          </tr>
        </tbody>
      </table>
      <p className={styles.reason}>
        <span className={styles.reasonLabel}>Reason</span> {c.reason}
      </p>
    </div>
  );
}
