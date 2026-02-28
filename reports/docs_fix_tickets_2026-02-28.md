# docs fix tickets 2026-02-28

## T1 (high) 現行スコープの正本固定
- title: 現行スコープを実験運用API中心に固定する
- impact: RQ/BD/DD/OPSREL の整合性
- target files:
  - `docs/1.要求(RQ)/02.プロジェクトのスコープ(SC)/RQ-SC-001.md`
  - `docs/index.md`
  - `docs/1.要求(RQ)/81.ドキュメント更新フローと受け入れ基準(DG)/RQ-DG-001.md`
- done: yes

## T2 (high) 旧BD-APP文脈の隔離
- title: 旧UI/運用API文脈を「参考/凍結」扱いに統一する
- impact: `docs/2.基本設計(BD)/03.アプリ(APP)` 配下全体
- target files:
  - `docs/2.基本設計(BD)/03.アプリ(APP)/31.API(API)/BD-APP-API-001.md`
  - `docs/2.基本設計(BD)/03.アプリ(APP)/41.UI(UI)/BD-APP-UI-001.md`
  - `docs/2.基本設計(BD)/03.アプリ(APP)/21.データ(DATA)/BD-APP-DATA-001.md`
  - `docs/2.基本設計(BD)/03.アプリ(APP)/11.品質特性(QUAL)/BD-APP-QUAL-001.md`
- done: yes

## T3 (high) 用語リンクの誤対応解消
- title: GLリンクと表示語の不整合を解消する
- impact: GLとBD-APP文書の語彙追跡性
- examples:
  - `RQ-GL-001`: `llm-temp-introspection` vs `diopside`
  - `RQ-GL-005`: `manifest` vs `タグ辞書`
  - `RQ-GL-008`: `within-model` vs `タグマスター`
  - `RQ-GL-010`: `blind` vs `段階ロード`
  - `RQ-GL-011`: `wrong-label` vs `再収集`
- done: mostly complete (`docs/2.基本設計(BD)/03.アプリ(APP)` 配下で主要な誤リンクを除去。`[[RQ-GL-002|収集実行]]` は運用上の別名として維持)

## T4 (high) 欠落ID参照の棚卸し
- title: 参照先が存在しないIDを解消する
- impact: トレーサビリティ、レビュー/自動検証
- representative missing IDs:
  - `RQ-FR-015` 以降
  - `RQ-UC-006` 以降
  - `DD-APP-UI-*`（現時点で実体なし）
- done: complete (`docs/2.基本設計(BD)/03.アプリ(APP)` 配下の欠落ID参照を旧参照表現へ置換し、未解決ID参照を解消)

## T5 (medium) API命名と状態語彙の統一
- title: `snake_case` ルールと状態語彙を一本化する
- impact: API契約/DD実装/UTケース
- target:
  - path params (`run_id` vs `runId`)
  - run state (`QUEUED/RUNNING/...` vs `queued/running/...`)
- done: partial (BD-APP-API-001/002 と BD-APP-UI-002 で `run_id`/`video_id` へ統一。状態語彙の全層統一は未完)
