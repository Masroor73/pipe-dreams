import { useEffect, useMemo, useRef, useState } from 'react';
import { Microphone, MicrophoneSlash, SpeakerHigh, CircleNotch } from '@phosphor-icons/react';
import { ConversationProvider, useConversationControls, useConversationMode, useConversationStatus } from '@elevenlabs/react';
import { useNavigate } from 'react-router';
import { api } from '../lib/api';
import { createVoiceTools } from './tools';
import { matchesBye, matchesWake } from './phrases';
import styles from './VoiceCopilot.module.css';

const AGENT_ID: string | undefined = import.meta.env.VITE_ELEVENLABS_AGENT_ID || undefined;

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  abort(): void;
}
type SRCtor = new () => SpeechRecognition;
declare global {
  interface Window {
    SpeechRecognition?: SRCtor;
    webkitSpeechRecognition?: SRCtor;
    __pdVoiceTools?: ReturnType<typeof createVoiceTools>;
  }
}

function micMessage(e: unknown): string {
  const name = e instanceof Error ? e.name : '';
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'Microphone access was blocked. Allow it in the browser and try again.';
  if (name === 'NotFoundError') return 'No microphone found.';
  return 'Voice assistant unavailable right now.';
}

function VoiceButton() {
  const navigate = useNavigate();
  const { startSession, endSession } = useConversationControls();
  const { status } = useConversationStatus();
  const { isSpeaking } = useConversationMode();
  const [note, setNote] = useState<string | null>(null);
  const [caption, setCaption] = useState<string | null>(null);
  const startingRef = useRef(false);
  const SR = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : undefined;
  const wakeSupported = !!SR;
  const [handsFree, setHandsFree] = useState(() => {
    try {
      return localStorage.getItem('pd-handsfree') !== 'off';
    } catch {
      return true;
    }
  });

  // Stable tools: navigate through a ref, and resolve search-only targets against the live URL.
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const tools = useMemo(
    () =>
      createVoiceTools({
        api,
        navigate: (to) => {
          if (!to.startsWith('?')) return navigateRef.current(to);
          // Search-only target: keep the other params (e.g. the open community).
          const merged = new URLSearchParams(window.location.search);
          new URLSearchParams(to).forEach((v, k) => merged.set(k, v));
          navigateRef.current(`${window.location.pathname}?${merged.toString()}`);
        },
      }),
    [],
  );

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    window.__pdVoiceTools = tools;
    return () => {
      delete window.__pdVoiceTools;
    };
  }, [tools]);

  // Stop the session if the shell unmounts.
  useEffect(() => () => endSession(), [endSession]);

  const active = status === 'connected';
  const connecting = status === 'connecting';
  const state = connecting ? 'connecting' : active ? (isSpeaking ? 'speaking' : 'listening') : 'idle';

  // Client tools hand the agent a JSON string; the agent speaks only from this.
  const endRef = useRef(endSession);
  endRef.current = endSession;
  const clientTools = useMemo(
    () => ({
      // Sleep word: let the goodbye finish, then close the session.
      end_conversation: async () => {
        setTimeout(() => endRef.current(), 2500);
        return 'ok';
      },
      ...Object.fromEntries(
        Object.entries(tools).map(([name, fn]) => [
          name,
          async (params: Record<string, unknown>) => JSON.stringify(await (fn as (p: never) => Promise<object>)(params as never)),
        ]),
      ),
    }),
    [tools],
  );

  const start = async () => {
    if (startingRef.current || !AGENT_ID) return;
    startingRef.current = true;
    setNote(null);
    setCaption(null);
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true }).then((s) => s.getTracks().forEach((t) => t.stop()));
      startSession({
        agentId: AGENT_ID,
        connectionType: 'webrtc',
        clientTools,
        onMessage: (m) => {
          if (m.role === 'agent' && m.message) setCaption(m.message);
          if (m.role === 'user' && m.message && matchesBye(m.message)) setTimeout(() => endRef.current(), 2500);
        },
        onError: () => setNote('Voice connection problem. Click to try again.'),
        onDisconnect: () => setCaption(null),
      });
    } catch (e) {
      setNote(micMessage(e));
    } finally {
      startingRef.current = false;
    }
  };
  const startRef = useRef(start);
  startRef.current = start;

  const toggle = () => {
    if (active || connecting) {
      endSession();
      setCaption(null);
      return;
    }
    void start();
  };

  // Hands-free wake word: a local Web Speech listener, only while idle (never alongside the session).
  const idle = status !== 'connected' && status !== 'connecting';
  const listeningForWake = wakeSupported && handsFree && idle && !!AGENT_ID;
  useEffect(() => {
    if (!listeningForWake || !SR) return;
    let stopped = false;
    let rec: SpeechRecognition | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const begin = () => {
      if (stopped) return;
      try {
        rec = new SR();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = 'en-US';
        rec.onresult = (ev: SpeechRecognitionEvent) => {
          let text = '';
          for (let i = ev.resultIndex; i < ev.results.length; i++) text += ev.results[i]?.[0]?.transcript ?? '' + ' ';
          if (matchesWake(text)) {
            stopped = true;
            try {
              rec?.abort();
            } catch {
              /* ignore */
            }
            // Give the mic a moment to be released before the session claims it.
            setTimeout(() => void startRef.current(), 400);
          }
        };
        rec.onerror = (ev: SpeechRecognitionErrorEvent) => {
          if (ev.error === 'not-allowed' || ev.error === 'service-not-allowed') stopped = true;
        };
        rec.onend = () => {
          if (!stopped) timer = setTimeout(begin, 500);
        };
        rec.start();
      } catch {
        if (!stopped) timer = setTimeout(begin, 1500);
      }
    };
    begin();
    return () => {
      stopped = true;
      clearTimeout(timer);
      try {
        rec?.abort();
      } catch {
        /* ignore */
      }
    };
  }, [listeningForWake, SR]);

  const toggleHandsFree = () => {
    setHandsFree((v) => {
      try {
        localStorage.setItem('pd-handsfree', v ? 'off' : 'on');
      } catch {
        /* ignore */
      }
      return !v;
    });
  };

  const label = { idle: 'Ask Pipe Dreams', connecting: 'Connecting…', listening: 'Listening… tap to stop', speaking: 'Speaking… tap to stop' }[state];
  const Icon = state === 'connecting' ? CircleNotch : state === 'speaking' ? SpeakerHigh : note ? MicrophoneSlash : Microphone;

  return (
    <div className={styles.dock}>
      {(caption || note) && (
        <p className={`${styles.caption} ${note ? styles.note : ''}`} role="status" aria-live="polite">
          {note ?? caption}
        </p>
      )}
      <button
        type="button"
        className={`${styles.button} ${styles[state]}`}
        onClick={toggle}
        aria-pressed={active}
        aria-label={label}
      >
        <Icon size={22} weight="fill" aria-hidden="true" className={state === 'connecting' ? styles.spin : undefined} />
        <span>{label}</span>
      </button>
      {wakeSupported && (
        <label className={styles.handsFree}>
          <input type="checkbox" checked={handsFree} onChange={toggleHandsFree} />
          <span>Hands-free: say 'Hello copilot'</span>
          {listeningForWake && (
            <em className={styles.listening}>
              listening for 'Hello copilot'
            </em>
          )}
        </label>
      )}
    </div>
  );
}

/** Floating voice button. Renders nothing unless VITE_ELEVENLABS_AGENT_ID is set. */
export function VoiceCopilot() {
  if (!AGENT_ID) return null;
  return (
    <ConversationProvider>
      <VoiceButton />
    </ConversationProvider>
  );
}
