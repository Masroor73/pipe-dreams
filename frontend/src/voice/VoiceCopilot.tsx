import { useEffect, useMemo, useRef, useState } from 'react';
import { Microphone, MicrophoneSlash, SpeakerHigh, CircleNotch } from '@phosphor-icons/react';
import { ConversationProvider, useConversationControls, useConversationMode, useConversationStatus } from '@elevenlabs/react';
import { useNavigate } from 'react-router';
import { api } from '../lib/api';
import { createVoiceTools } from './tools';
import styles from './VoiceCopilot.module.css';

const AGENT_ID: string | undefined = import.meta.env.VITE_ELEVENLABS_AGENT_ID || undefined;

declare global {
  interface Window {
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

  // Stable tools: navigate through a ref, and resolve search-only targets against the live URL.
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const tools = useMemo(
    () =>
      createVoiceTools({
        api,
        navigate: (to) => navigateRef.current(to.startsWith('?') ? `${window.location.pathname}${to}` : to),
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
  const clientTools = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(tools).map(([name, fn]) => [
          name,
          async (params: Record<string, unknown>) => JSON.stringify(await (fn as (p: never) => Promise<object>)(params as never)),
        ]),
      ),
    [tools],
  );

  const toggle = async () => {
    if (active || connecting) {
      endSession();
      setCaption(null);
      return;
    }
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
