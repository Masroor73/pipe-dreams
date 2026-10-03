import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

/** Returns a function that opens the asset side panel by setting `?asset=<id>` on the current path. */
export function useAssetLink(): (assetId: string) => void {
  const [, setSearchParams] = useSearchParams();
  return useCallback(
    (assetId: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set('asset', assetId);
        return next;
      });
    },
    [setSearchParams],
  );
}

/** Returns a function that closes the asset side panel (removes `?asset=`). */
export function useAssetClose(): () => void {
  const [, setSearchParams] = useSearchParams();
  return useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('asset');
      return next;
    });
  }, [setSearchParams]);
}
