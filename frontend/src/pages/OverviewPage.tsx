import { Briefing } from '../components/Overview/Briefing';
import { CaptureChart } from '../components/Overview/CaptureChart';
import { GateCards } from '../components/Overview/GateCards';
import { Headline } from '../components/Overview/Headline';
import { OverviewFooter } from '../components/Overview/OverviewFooter';
import { RankChangeCards } from '../components/Overview/RankChangeCards';
import { Teasers } from '../components/Overview/Teasers';
import { useOverview } from '../hooks';
import styles from './OverviewPage.module.css';

export default function OverviewPage() {
  const overview = useOverview();
  return (
    <div className={styles.page}>
      <h1 className={styles.srOnly}>Overview</h1>
      <Headline overview={overview} />
      <CaptureChart overview={overview} />
      <GateCards overview={overview} />
      <RankChangeCards />
      <Teasers />
      <Briefing />
      <OverviewFooter overview={overview} />
    </div>
  );
}
