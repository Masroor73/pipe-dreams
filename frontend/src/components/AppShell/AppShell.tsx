import { Drop } from '@phosphor-icons/react';
import { NavLink, Route, Routes, useSearchParams } from 'react-router';
import { AssetPanel } from '../AssetPanel/AssetPanel';
import { useAssetClose } from '../../hooks/useAssetLink';
import { HealthGate } from './HealthGate';
import { SyntheticBanner } from './SyntheticBanner';
import { APP_ROUTES } from './routes';
import styles from './AppShell.module.css';

/** Mounts the asset side panel whenever `?asset=<id>` is present, over any page. */
export function AssetPanelSlot({ assetId, onClose }: { assetId: string | null; onClose: () => void }) {
  if (!assetId) return null;
  return <AssetPanel assetId={assetId} onClose={onClose} />;
}

export function AppShell() {
  const [params] = useSearchParams();
  const closeAsset = useAssetClose();

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
    </div>
  );
}
