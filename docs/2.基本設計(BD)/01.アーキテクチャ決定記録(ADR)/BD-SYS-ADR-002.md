---
id: BD-SYS-ADR-002
title: invalid再処理は親run不変のrepair run方式を採用
doc_type: アーキテクチャ決定記録
phase: BD
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-03-11
updated: '2026-03-11'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[RQ-RDR-003]]'
  - '[[RQ-FR-015]]'
  - '[[RQ-FR-016]]'
  - '[[BD-SYS-ADR-001]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[DD-APP-ERR-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - BD
  - ADR
---

## 決定
- invalid 再処理は `POST /runs/{parent_run_id}/repairs` の別APIで起動する。
- repair は親runの `normalized/invalid/reports` を上書きせず、child repair run を新規採番して実行する。
- 初期実装は `study1` の `invalid_only` に限定し、`renormalize` と `rerun` を切り替え可能にする。
- repair 受付時に対象 invalid を child run 配下の `repair/seed.jsonl` へ固定化し、以降の durable 実行はその seed を正本入力にする。
- repair run は `parent_run_id` と repair 条件を状態/設定/成果物索引へ保持する。
- `rebuild_downstream=true` の場合だけ、repair 後の Study1 結果を基準に Study2/Experiment/report を repair run 側で再生成する。

## 根拠
- `study2` 以降の manifest は Study1 normalized から派生するため、親runを途中更新すると成果物の因果関係が崩れる。
- parse failure の修復では、成功済み shard の再投入より、invalid のみの再処理の方がコストと待機時間を抑えやすい。
- parent/child run を分けると、元runの `PARTIAL` 記録と repair 後の完了結果を並行に保持できる。

## トレードオフ
- run 数と成果物数が増え、一覧UIと運用手順がやや複雑になる。
- `rebuild_downstream` を有効化した repair run は、下流 phase を再実行する分だけ時間とコストが増える。
- 初期スコープを `study1` に限定するため、他 phase の invalid 再処理は後続拡張になる。

## 影響
- projection/status/list/artifacts の run メタデータに lineage 項目を追加する。
- repair API で重複要求、親run未終端、対象 invalid 不在を検証し、受付前に拒否する。
- Orchestrator に repair workflow と Study1 merge/downstream rebuild 分岐を追加する。
- `invalid/` を参照する repair API の入力検証と冪等制御を追加する。
- 運用ランブックに repair 実行条件と parent run 不変ルールを追記する。

## 変更履歴
- 2026-03-11: repair seed 固定化と metadata 露出範囲（status/list/artifacts）を追記 [[RQ-RDR-003]]
- 2026-03-11: 初版作成（invalid再処理の child repair run 方式を記録） [[BD-SYS-ADR-002]]
