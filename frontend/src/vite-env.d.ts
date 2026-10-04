/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_USE_FIXTURES?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_ELEVENLABS_AGENT_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
