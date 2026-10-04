# Pipe Dreams — Tech Stack

This document is authoritative for MVP technology choices.

## 1. Principles

Choose technology for:
1. team familiarity;
2. implementation speed;
3. demo reliability;
4. methodological transparency;
5. low operational overhead.

Do not add technology for résumé optics or architecture complexity.

---

## 2. Frontend

### React
**Choice:** React 19-compatible application architecture.

Why:
- both teammates have extensive React experience;
- component model fits the dashboard;
- easy composition of charts, map, audit timeline, and detail panels.

### TypeScript
**Choice:** strict TypeScript.

Why:
- stable API contracts;
- fewer integration errors;
- good fit with Pydantic/OpenAPI backend.

### Vite
**Choice:** Vite.

Why:
- fast local iteration;
- minimal framework overhead;
- no need for SSR / Next.js for this hackathon.

### Charts
**Choice:** Recharts.

Why:
- familiar React integration;
- enough for capture curves, comparison bars, intervals, and validation charts.

### Map
**Choice:** MapLibre GL via a React wrapper.

Why:
- performant line rendering;
- open ecosystem;
- can render project geometry without coupling the app to a proprietary map platform.

Requirement:
- the app must have a no-basemap/fallback mode in case tile/network access fails.

Package: `maplibre-gl` with `react-map-gl` (`react-map-gl/maplibre` entry point) as the React wrapper. The default map style is an inline offline style (background only, no tiles), with an SVG line-drawing fallback when WebGL is unavailable.

### Routing
**Choice:** `react-router` (v7).
Why: five tabs plus a deep-linkable `?asset=<id>` side panel need URL state; it is the standard React router.

### Icons
**Choice:** `@phosphor-icons/react` (the only icon family).
Why: one consistent, tree-shakable icon set; no hand-drawn SVG icons.

### Typeface
**Choice:** `@fontsource-variable/figtree` (self-hosted).
Why: legible on a projector with tabular numerals, and works offline during the demo (no Google Fonts request).

### Styling
Plain CSS: design tokens in `frontend/src/styles/tokens.css` plus CSS modules. No Tailwind, UI kit, or animation library (CSS transitions only).

### Fixture mode
`VITE_USE_FIXTURES=true` (default in `frontend/.env.development`) serves contract-shaped synthetic JSON from `frontend/src/fixtures/` so the UI can be built before the backend exists. Fixtures always carry `meta.synthetic: true` and `config_hash: "PLACEHOLDER"`, so the synthetic banner is always shown.

---

## 3. Backend

### FastAPI
**Choice:** FastAPI.

Role:
- HTTP API;
- response validation;
- artifact loading;
- light serialization / filtering;
- health endpoint;
- OpenAPI documentation.

Not its role:
- model fitting on request;
- spatial joins on request;
- duplicate ranking logic;
- persistent state.

### Pydantic
Use typed request/response models for every public endpoint.

### Uvicorn
Local ASGI server.

---

## 4. Python Engine

### Python 3.11
Stable target for the team and dependencies.

### pandas / NumPy
Tabular transformations and numerical work.

### GeoPandas / Shapely / PyProj
Projected spatial matching and geometry handling.

### scikit-learn
Logistic regression and retained model comparisons.

### SciPy
Statistical support where needed.

### PyArrow
Parquet interchange.

### PyYAML
Frozen config parsing.

---

## 5. Testing

### Backend
- pytest;
- FastAPI TestClient / httpx where needed.

### Frontend
- Vitest (jsdom);
- React Testing Library (`@testing-library/react`, `jest-dom`, `user-event`) for critical UI states.

### Lint / format
- Ruff for Python.
- ESLint for TypeScript.

Prettier is optional if the team already uses it consistently; do not add competing formatters mid-build.

---

## 6. Artifact Interchange

Use:
- Parquet for table-like high-volume plan data;
- CSV for judge-readable result tables where useful;
- JSON for summaries/config-derived metadata;
- JSONL for append-only agent audit events.

Artifacts are the contract between engine and API.

---

## 7. Environment

### Frontend
Node.js 20+ recommended.

### Backend
Python 3.11 virtual environment.

Keep frontend and backend dependency management separate:
- `frontend/package.json`;
- `backend/pyproject.toml`.

---

## 8. Explicitly Not in MVP

- Next.js;
- Redux unless a concrete state problem appears;
- database;
- Docker;
- Kubernetes;
- GraphQL;
- WebSockets;
- Celery / background queue;
- LangChain / agent frameworks;
- LLM-based ranking;
- Databricks;
- cloud deployment requirement;
- FastAPI write APIs that mutate the frozen audit.

---

## 9. Optional After Core

Only after the core rubric path is complete:

- ElevenLabs TTS;
- deployment of frontend/backend;
- generated TypeScript API types from FastAPI OpenAPI;
- richer map interactions.

---

## 10. Dependency Rule

Any new dependency must answer:

> Which rubric requirement or concrete implementation problem does this solve?

If the answer is unclear, do not add it.
