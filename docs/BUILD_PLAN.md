# Pipe Dreams — Build Plan

## 1. Work Split

### Teammate — Audit / Engine
Own:
- integrate existing `audit_backtest.py`;
- corrected temporal rules;
- rolling origins;
- 1-km spatial block bootstrap;
- candidate evaluation;
- confidence thresholds from validation only;
- corrected final test;
- final artifacts.

### Frontend / Integration
Own:
- React SPA;
- FastAPI thin API;
- artifact service;
- typed API contracts;
- overview;
- map;
- audit timeline;
- rank-change cards;
- escalation;
- not-covered;
- screenshots/pitch integration.

Both:
- frozen config review;
- final commit/tag before corrected final test;
- demo rehearsal.

---

## 2. Immediate Order

1. create shared GitHub repo;
2. commit documentation + skeleton;
3. both clone same repo;
4. install frontend/backend dependencies;
5. teammate ports existing audit code into top-level `engine/` without rewriting;
6. frontend builds against synthetic/dev artifacts;
7. teammate runs rolling validation;
8. confidence thresholds frozen;
9. config placeholder check → hash → commit/tag;
10. corrected 2023–2025 final test;
11. replace synthetic artifacts with real artifacts;
12. end-to-end demo;
13. screenshots/video/pitch.

---

## 3. Backend Definition of Done

- [ ] `GET /api/health`
- [ ] artifact loader validates required files
- [ ] overview endpoint
- [ ] asset list/detail endpoints
- [ ] audit endpoint
- [ ] escalation endpoint
- [ ] not-covered endpoint
- [ ] data-quality endpoint
- [ ] CORS limited to local frontend origin
- [ ] no model fitting on normal API requests
- [ ] API tests pass

---

## 4. Frontend Definition of Done

- [ ] persistent synthetic-data banner
- [ ] baseline/V1/V2 comparison
- [ ] validation/capture view
- [ ] map
- [ ] agent accept/reject timeline
- [ ] three real rank/action changes
- [ ] asset detail
- [ ] escalation table
- [ ] not-covered view
- [ ] loading/error/empty states
- [ ] no domain score calculated client-side

---

## 5. Engine Definition of Done

- [ ] temporal rules corrected
- [ ] rolling validation 2013/2016/2019
- [ ] match/reachable share per origin
- [ ] 1/2/5/10% capture
- [ ] block bootstrap
- [ ] V1
- [ ] C1/C2/C3/C4
- [ ] frozen gate
- [ ] confidence thresholds from validation only
- [ ] final config hash/tag
- [ ] corrected 2023–2025 test
- [ ] no tuning afterward
- [ ] final artifacts match schemas

---

## 6. MVP Completion Gate

Core is done only when:
1. real baseline works;
2. V1 exists;
3. historical self-evaluation exists;
4. at least one candidate is genuinely accepted or rejected by gate;
5. V2 exists or correctly equals V1;
6. evidence confidence and priority are distinct;
7. React/FastAPI demo exposes the full decision loop.

---

## 7. Post-Core Only

After MVP:
- ElevenLabs TTS;
- deployment;
- UI polish;
- additional scenario controls.

Do not add before core:
- database;
- Docker;
- auth;
- GraphQL;
- WebSockets;
- LLM ranking;
- new models;
- new datasets.
