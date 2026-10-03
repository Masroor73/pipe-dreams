import type { ReactElement } from 'react';
import OverviewPage from '../../pages/OverviewPage';
import MapPage from '../../pages/MapPage';
import AuditPage from '../../pages/AuditPage';
import EscalationPage from '../../pages/EscalationPage';
import LimitsPage from '../../pages/LimitsPage';

export interface AppRoute {
  path: string;
  label: string;
  element: ReactElement;
  /** true: the page fills the viewport below the nav (no centred max-width container). */
  fullBleed?: boolean;
}

/** Single source for routes and top-nav links. */
export const APP_ROUTES: AppRoute[] = [
  { path: '/', label: 'Overview', element: <OverviewPage /> },
  { path: '/map', label: 'Map', element: <MapPage />, fullBleed: true },
  { path: '/audit', label: 'Agent audit', element: <AuditPage /> },
  { path: '/escalation', label: 'Escalation', element: <EscalationPage /> },
  { path: '/limits', label: 'Limits', element: <LimitsPage /> },
];
