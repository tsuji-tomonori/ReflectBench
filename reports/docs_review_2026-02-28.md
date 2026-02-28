# docs review 2026-02-28

## scope
- target: `docs/` (RQ/BD/DD/UT/OPSREL)
- viewpoints: contradiction, undefined terms, notation drift

## critical findings

### 1) project context conflict (high)
- `llm-temp-introspection` experiment scope is declared in `docs/1.要求(RQ)/01.プロジェクトの目的(PP)/RQ-PP-001.md:37` and `docs/1.要求(RQ)/02.プロジェクトのスコープ(SC)/RQ-SC-001.md:29`.
- `BD-APP-*` documents still define a different UI/ops domain (e.g. archive explorer and admin publishing flows) in `docs/2.基本設計(BD)/03.アプリ(APP)/41.UI(UI)/BD-APP-UI-001.md:50` and `docs/2.基本設計(BD)/03.アプリ(APP)/31.API(API)/BD-APP-API-001.md:70`.
- impact: RQ -> BD -> DD traceability is no longer single-system consistent.

### 2) scope mismatch (high)
- Out of scope says no new UI app development: `docs/1.要求(RQ)/02.プロジェクトのスコープ(SC)/RQ-SC-001.md:38`.
- But UI architecture/catalog/components are specified in detail: `docs/2.基本設計(BD)/03.アプリ(APP)/41.UI(UI)/BD-APP-UI-001.md:60`.
- impact: decision boundary is contradictory for implementation/testing.

### 3) stakeholder mismatch (high)
- `RQ-SH-002` is marked abolished (`status: 廃止`): `docs/1.要求(RQ)/11.ステークホルダー(SH)/RQ-SH-002.md:7`.
- many BD docs still depend on `[[RQ-SH-002|利用者]]`: e.g. `docs/2.基本設計(BD)/03.アプリ(APP)/41.UI(UI)/BD-APP-UI-001.md:55`.
- impact: actor definitions and use-case ownership are inconsistent.

### 4) API system mismatch (high)
- experiment API baseline: `POST /runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/artifacts` in `docs/3.詳細設計(DD)/03.インフラ(INF)/22.API契約(API)/DD-INF-API-001.md:28`.
- another API family in BD-APP: `/api/v1/ops/...` and `/api/v1/admin/...` in `docs/2.基本設計(BD)/03.アプリ(APP)/31.API(API)/BD-APP-API-001.md:70`.
- impact: external contract naming and test scope cannot be uniquely determined.

### 5) unresolved referenced IDs (high)
- references to missing FR/UC/DD documents exist, e.g. `RQ-FR-015`, `RQ-FR-024`, `RQ-FR-025`, `RQ-UC-006`, `DD-APP-UI-018` in `docs/2.基本設計(BD)/03.アプリ(APP)/41.UI(UI)/BD-APP-UI-001.md:63` and `docs/2.基本設計(BD)/03.アプリ(APP)/31.API(API)/BD-APP-API-001.md:77`.
- existing FR in repo currently ends at `RQ-FR-014` (`docs/1.要求(RQ)/51.機能要求(FR)/03.成果物とデータ契約(DATA)/RQ-FR-014.md:2`).
- impact: trace matrix is incomplete; links are not resolvable.

## terminology issues

### 6) glossary link target mismatch (high)
- `[[RQ-GL-001|diopside]]` while `RQ-GL-001` term is `llm-temp-introspection`: `docs/2.基本設計(BD)/03.アプリ(APP)/41.UI(UI)/BD-APP-UI-001.md:50`, `docs/1.要求(RQ)/21.用語(GL)/RQ-GL-001.md:3`.
- `[[RQ-GL-010|段階ロード]]` while `RQ-GL-010` term is `blind`: `docs/2.基本設計(BD)/03.アプリ(APP)/11.品質特性(QUAL)/BD-APP-QUAL-001.md:31`, `docs/1.要求(RQ)/21.用語(GL)/RQ-GL-010.md:3`.
- `[[RQ-GL-011|再収集]]` while `RQ-GL-011` term is `wrong-label`: `docs/2.基本設計(BD)/03.アプリ(APP)/41.UI(UI)/BD-APP-UI-001.md:56`, `docs/1.要求(RQ)/21.用語(GL)/RQ-GL-011.md:3`.
- `[[RQ-GL-005|タグ辞書]]` while `RQ-GL-005` term is `manifest`: `docs/2.基本設計(BD)/03.アプリ(APP)/31.API(API)/BD-APP-API-001.md:69`, `docs/1.要求(RQ)/21.用語(GL)/RQ-GL-005.md:3`.
- `[[RQ-GL-008|タグマスター]]` while `RQ-GL-008` term is `within-model`: `docs/2.基本設計(BD)/03.アプリ(APP)/31.API(API)/BD-APP-API-002.md:74`, `docs/1.要求(RQ)/21.用語(GL)/RQ-GL-008.md:3`.

## notation drift

### 7) casing drift in API contracts (medium)
- rule says external API keys should be snake_case: `docs/2.基本設計(BD)/03.アプリ(APP)/31.API(API)/BD-APP-API-001.md:56`.
- path parameters still use camelCase (`{runId}` etc.) in same document: `docs/2.基本設計(BD)/03.アプリ(APP)/31.API(API)/BD-APP-API-001.md:71`.

### 8) run state vocabulary drift (medium)
- uppercase states in DD-INF data contract: `docs/3.詳細設計(DD)/03.インフラ(INF)/23.データ契約(DATA)/DD-INF-DATA-001.md:51`.
- lowercase + `cancelled` in BD-APP data contract: `docs/2.基本設計(BD)/03.アプリ(APP)/21.データ(DATA)/BD-APP-DATA-001.md:83`.

### 9) malformed in-text term linking (low)
- mixed link/plain text like `[[RQ-GL-002|run]]ning`: `docs/2.基本設計(BD)/03.アプリ(APP)/41.UI(UI)/BD-APP-UI-001.md:67`.

## recommended fix order
1. choose one canonical system scope (A: keep experiment-only docs, or B: restore full app scope) and declare in `RQ-SC-001`.
2. align stakeholder model (`RQ-SH-001` only vs `RQ-SH-001 + RQ-SH-002`) and update all `up/related` and actor references.
3. normalize API baseline to one family and update BD/DD/UT contracts together.
4. resolve all missing IDs (create missing docs or remove references).
5. rebuild glossary mapping (new GL IDs for domain terms; relink old mismatches).
6. enforce notation rules (`snake_case`, state vocabulary, link style) with one pass.

## quick win checklist (small, low-risk)
- replace malformed link text instances like `[[RQ-GL-002|run]]ning`.
- add lint/check script to fail on unresolved IDs and GL alias mismatch.
- add "active scope" note in `docs/index.md` to prevent mixed-context edits.
