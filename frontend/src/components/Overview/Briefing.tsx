import { useEffect, useState } from 'react';
import { SpeakerHigh } from '@phosphor-icons/react';
import styles from './Briefing.module.css';

const AUDIO_URL = '/briefing.mp3';
const TEXT_URL = '/briefing.txt';

/** Optional spoken planner briefing; renders nothing unless /briefing.mp3 exists. */
export function Briefing() {
  const [available, setAvailable] = useState(false);
  const [transcript, setTranscript] = useState('');

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const head = await fetch(AUDIO_URL, { method: 'HEAD' });
        const type = head.headers?.get('content-type') ?? '';
        if (!head.ok || type.includes('text/html')) return;
        if (live) setAvailable(true);
        const t = await fetch(TEXT_URL);
        if (t.ok && live) setTranscript(await t.text());
      } catch {
        /* control stays hidden */
      }
    })();
    return () => {
      live = false;
    };
  }, []);

  if (!available) return null;
  return (
    <section className={styles.briefing} aria-label="Planner briefing">
      <h3 className={styles.title}>
        <SpeakerHigh size={18} weight="bold" aria-hidden="true" />
        Play planner briefing (ElevenLabs)
      </h3>
      <audio controls preload="none" src={AUDIO_URL} className={styles.audio} />
      {transcript && (
        <details className={styles.details}>
          <summary>Transcript</summary>
          <p>{transcript}</p>
        </details>
      )}
    </section>
  );
}
