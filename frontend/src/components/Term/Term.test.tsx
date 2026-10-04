import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { GLOSSARY, GLOSSARY_BY_ID } from '../../config/glossary';
import GlossaryPage from '../../pages/GlossaryPage';
import { Term } from './Term';

describe('glossary', () => {
  it('has unique ids and a definition and source for every entry', () => {
    expect(new Set(GLOSSARY.map((g) => g.id)).size).toBe(GLOSSARY.length);
    for (const g of GLOSSARY) {
      expect(g.short.length).toBeGreaterThan(20);
      expect(g.source).toMatch(/\.md/);
    }
  });

  it('covers the terms judges see', () => {
    for (const id of ['hl10', 'bootstrap_se', 'capture', 'length_budget', 'count_only', 'organizer_cell', 'v1', 'v2', 'candidates', 'verify_escalate', 'evidence_confidence', 'consequence_tier', 'reachable_share', 'synthetic'] as const) {
      expect(GLOSSARY_BY_ID[id]).toBeDefined();
    }
  });

  it('never calls evidence confidence or priority a failure probability', () => {
    expect(GLOSSARY_BY_ID.evidence_confidence.short).toMatch(/not a failure probability/);
    expect(GLOSSARY_BY_ID.priority.short).toMatch(/not a probability of failure/);
  });

  it('Term toggles its definition on click and closes on Escape', () => {
    render(
      <MemoryRouter>
        <p>
          Uses <Term id="hl10" /> weighting.
        </p>
      </MemoryRouter>,
    );
    const btn = screen.getByRole('button', { name: 'hl10' });
    expect(btn).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('tooltip', { hidden: true })).toHaveTextContent(GLOSSARY_BY_ID.hl10.short);
    fireEvent.click(btn);
    expect(btn).toHaveAttribute('aria-expanded', 'true');
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(btn).toHaveAttribute('aria-expanded', 'false');
  });

  it('glossary page lists every entry with an anchor', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/glossary']}>
        <GlossaryPage />
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { level: 1, name: 'Glossary' })).toBeInTheDocument();
    for (const g of GLOSSARY) expect(container.querySelector(`#${g.id}`)).toHaveTextContent(g.term);
  });
});
