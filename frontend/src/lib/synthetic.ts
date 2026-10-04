import { createContext, createElement, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { Meta } from '../types/api';

/** Contract rule: banner shows when meta.synthetic is true or config_hash is "PLACEHOLDER". */
export function isSyntheticMeta(meta: Meta | null | undefined): boolean {
  if (!meta) return false;
  return meta.synthetic === true || meta.config_hash === 'PLACEHOLDER';
}

type ReportFn = (sourceKey: string, meta: Meta | null) => void;

interface SyntheticContextValue {
  report: ReportFn;
  isSynthetic: boolean;
}

const noop: ReportFn = () => undefined;
const SyntheticContext = createContext<SyntheticContextValue>({ report: noop, isSynthetic: false });

export function MetaProvider({ children }: { children: ReactNode }) {
  const [metas, setMetas] = useState<Record<string, Meta>>({});

  const report = useCallback<ReportFn>((key, meta) => {
    setMetas((prev) => {
      if (meta === null) {
        if (!(key in prev)) return prev;
        const next = { ...prev };
        delete next[key];
        return next;
      }
      const old = prev[key];
      if (old && old.synthetic === meta.synthetic && old.config_hash === meta.config_hash) return prev;
      return { ...prev, [key]: meta };
    });
  }, []);

  const isSynthetic = useMemo(() => Object.values(metas).some(isSyntheticMeta), [metas]);
  const value = useMemo(() => ({ report, isSynthetic }), [report, isSynthetic]);

  return createElement(SyntheticContext.Provider, { value }, children);
}

/** Data hooks call the returned function with each response's meta. */
export function useReportMeta(): ReportFn {
  return useContext(SyntheticContext).report;
}

/** True when any reported response was synthetic / placeholder. */
export function useIsSynthetic(): boolean {
  return useContext(SyntheticContext).isSynthetic;
}
