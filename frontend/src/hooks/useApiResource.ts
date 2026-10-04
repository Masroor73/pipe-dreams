import { useCallback, useEffect, useId, useRef, useState } from 'react';
import type { DependencyList } from 'react';
import { ApiError } from '../lib/api';
import { useReportMeta } from '../lib/synthetic';
import type { Envelope, Meta } from '../types/api';

export type ResourceStatus = 'loading' | 'error' | 'success';

export interface Resource<T> {
  status: ResourceStatus;
  data: T | undefined;
  meta: Meta | undefined;
  error: ApiError | undefined;
  reload: () => void;
}

function toApiError(e: unknown): ApiError {
  if (e instanceof ApiError) return e;
  return new ApiError(0, 'unknown_error', e instanceof Error ? e.message : 'Unexpected error.');
}

interface State<T> {
  status: ResourceStatus;
  data: T | undefined;
  meta: Meta | undefined;
  error: ApiError | undefined;
}

/**
 * Core loader: runs `fetcher` on mount, whenever `deps` change and on reload().
 * Results from a superseded or unmounted request are ignored.
 */
function useAsync<R, T>(
  fetcher: () => Promise<R>,
  unwrap: (r: R) => { data: T; meta?: Meta },
  deps: DependencyList,
  onMeta?: (meta: Meta) => void,
): Resource<T> {
  const [state, setState] = useState<State<T>>({
    status: 'loading',
    data: undefined,
    meta: undefined,
    error: undefined,
  });
  const [nonce, setNonce] = useState(0);
  const latest = useRef(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const unwrapRef = useRef(unwrap);
  unwrapRef.current = unwrap;
  const onMetaRef = useRef(onMeta);
  onMetaRef.current = onMeta;

  useEffect(() => {
    const id = ++latest.current;
    setState({ status: 'loading', data: undefined, meta: undefined, error: undefined });
    fetcherRef
      .current()
      .then((r) => {
        if (id !== latest.current) return;
        const { data, meta } = unwrapRef.current(r);
        if (meta) onMetaRef.current?.(meta);
        setState({ status: 'success', data, meta, error: undefined });
      })
      .catch((e: unknown) => {
        if (id !== latest.current) return;
        setState({ status: 'error', data: undefined, meta: undefined, error: toApiError(e) });
      });
    return () => {
      // Invalidate in-flight work when deps change or the component unmounts.
      latest.current++;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce, ...deps]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { ...state, reload };
}

/** Enveloped endpoint: unwraps `{meta, data}` and reports `meta` to the synthetic-data context. */
export function useApiResource<T>(
  fetcher: () => Promise<Envelope<T>>,
  deps: DependencyList = [],
): Resource<T> {
  const report = useReportMeta();
  const key = useId();
  useEffect(() => () => report(key, null), [report, key]);
  return useAsync<Envelope<T>, T>(
    fetcher,
    (env) => ({ data: env.data, meta: env.meta }),
    deps,
    (meta) => report(key, meta),
  );
}

/** Non-enveloped endpoint (health). */
export function useRawResource<T>(fetcher: () => Promise<T>, deps: DependencyList = []): Resource<T> {
  return useAsync<T, T>(fetcher, (data) => ({ data }), deps);
}
