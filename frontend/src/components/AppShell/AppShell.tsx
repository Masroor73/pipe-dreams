import { useEffect, useState } from 'react';
import { Drop } from '@phosphor-icons/react';
import { NavLink, Route, Routes, useNavigate, useSearchParams } from 'react-router';
import { canViewTransition, withViewTransition } from '../../hooks/viewTransition';
import { AssetPanel } from '../AssetPanel/AssetPanel';
import { useAssetClose } from '../../hooks/useAssetLink';
import { HealthGate } from './HealthGate';
import { SyntheticBanner } from './SyntheticBanner';
import { useIsSynthetic } from '../../lib/synthetic';
import { APP_ROUTES } from './routes';
import { VoiceCopilot } from '../../voice/VoiceCopilot';
import styles from './AppShell.module.css';

/** Mounts the asset side panel whenever `?asset=<id>` is present, over any page. */
export function AssetPanelSlot({ assetId, onClose }: { assetId: string | null; onClose: () => void }) {
  // Keep the last id mounted briefly so the panel can slide out.
  const [shown, setShown] = useState<string | null>(assetId);
  useEffect(() => {
    if (assetId) {
      setShown(assetId);
      return;
    }
    const t = setTimeout(() => setShown(null), PANEL_EXIT_MS);
    return () => clearTimeout(t);
  }, [assetId]);
  if (!shown) return null;
  return <AssetPanel assetId={shown} onClose={onClose} open={assetId !== null} />;
}

const PANEL_EXIT_MS = 220;

export function AppShell() {
  const [params] = useSearchParams();
  const closeAsset = useAssetClose();
  const navigate = useNavigate();
  const synthetic = useIsSynthetic();
  // The banner slot only takes space while the synthetic banner is shown; otherwise the nav sits at the top.
  useEffect(() => {
    const root = document.documentElement;
    if (synthetic) root.style.removeProperty('--banner-height');
    else root.style.setProperty('--banner-height', '0px');
    return () => {
      root.style.removeProperty('--banner-height');
    };
  }, [synthetic]);
  // Marks the document so the CSS route-in animation yields to the cross-fade.
  useEffect(() => {
    if (canViewTransition()) document.documentElement.dataset.vt = '';
    return () => {
      delete document.documentElement.dataset.vt;
    };
  }, []);

  return (
    <div className={styles.shell}>
      <header className={styles.chrome}>
        <SyntheticBanner />
        <nav className={styles.nav} aria-label="Primary">
          <span className={styles.brand}>
            <Drop size={26} weight="fill" aria-hidden="true" />
            Pipe Dreams
          </span>
          <ul className={styles.links}>
            {APP_ROUTES.map((r) => (
              <li key={r.path}>
                <NavLink
                  to={r.path}
                  end={r.path === '/'}
                  onClick={(e) => {
                    // Plain left-click only; modified clicks keep native behaviour.
                    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
                    if (!canViewTransition()) return;
                    e.preventDefault();
                    withViewTransition(() => navigate(r.path));
                  }}
                  className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}
                >
                  {r.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main className={styles.main}>
        <HealthGate>
          <Routes>
            {APP_ROUTES.map((r) => (
              <Route
                key={r.path}
                path={r.path}
                element={r.fullBleed ? <div className={styles.fullBleed}>{r.element}</div> : <div className={styles.container}>{r.element}</div>}
              />
            ))}
          </Routes>
          <AssetPanelSlot assetId={params.get('asset')} onClose={closeAsset} />
        </HealthGate>
      </main>
      <VoiceCopilot />
    </div>
  );
}
