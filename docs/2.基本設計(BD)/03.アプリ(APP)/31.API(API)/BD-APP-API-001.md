---
id: BD-APP-API-001
title: API一覧
doc_type: API設計
phase: BD
version: 1.0.11
status: 下書き
owner: RQ-SH-001
created: 2026-01-31
updated: '2026-02-28'
up:
- '[[RQ-SC-001]]'
- '[[RQ-FR-001]]'
related:
- '[[BD-SYS-ADR-001]]'
- '[[BD-APP-API-005]]'
tags:
- llm-temp-introspection
- BD
- API
---


## スコープ注記
- 本文書は `docs/2.基本設計(BD)/03.アプリ(APP)` の旧文脈API設計を保持する参考文書であり、現行スコープの正本ではない。
- 現行スコープの正本は `[[RQ-SC-001]]` と DD-INF/DD-APP 系列を優先する。

## 設計方針
- 本システムは利用者（旧定義）向け参照を静的配信で提供し、管理画面の更新系APIと責務分離して管理する。
- 原本はDB正本とし、`tag_master.json` を含む配信成果物は生成結果として扱う。
- 旧要件で定義された見どころ導線は、コメント密度波形の静的JSON配信で提供する。
- 旧要件で定義されたワードクラウドは、動的生成APIではなく事前生成済み画像の静的配信で提供する。
- 静的配信契約のHTTPステータス/キャッシュ/エラーフォールバック方針は [[BD-APP-API-005]] の共通規約に従う。

## 設計要点
- 一覧・検索用データは `bootstrap.json` / `tag_master.json` / `archive_index.pN.json` を継続利用する。
- 管理画面の更新系（タグ更新、反映トリガ、再収集）は Backend API で受け、利用者（旧定義）向け参照契約へ直接混在させない。
- 収集後の生成処理は単一Backend API（Hono）内バッチで実行し、別デプロイのworkerサービスを前提にしない。
- 動画詳細の補助表示データ（コメント密度波形）は `highlights/{video_id}.json` 契約で配信する。
- 動画詳細の補助表示データ（ワードクラウド）は `wordcloud/{video_id}.png` 契約で配信する。
- クライアントは静的アセット取得失敗時に代替表示へフォールバックし、詳細モーダルを継続表示する。

## 契約境界
- **利用者（旧定義）向け参照契約**: 静的JSON/静的画像（本書で定義）。
- **管理画面向け更新契約**: [[BD-APP-API-002]] を正本とし、本書では契約名と接続点のみ定義する。
- **将来拡張契約**: API検索エンドポイントは将来追加予定として予約し、現時点で契約詳細は固定しない。

## 契約表記ルール
- 運用APIの外部入出力キーは `snake_case` を正本とし、BD/DDで同一語彙を使う。
- ヘルスチェック経路は `GET /api/v1/ops/diagnostics/health` を正本とする。

## 正本ルール
- 本書（[[BD-APP-API-001]]）は「API一覧の正本」として、契約ID・用途・要求対応・詳細設計参照を管理する。
- 入出力スキーマ、状態遷移、エラーコード、再試行条件の正本は [[BD-APP-API-002]] 以降の個別API設計に集約する。
- バッチ一覧/バッチイベント一覧/バッチ実行制約/同時実行制御の正本は [[BD-APP-API-002]] で管理する。
- 一覧と個別設計に差異がある場合は、個別設計を優先して本書を同一変更で更新する。

## API一覧
| 区分 | パス/契約 | 用途 | 主な利用要求 | 詳細設計 |
|---|---|---|---|---|
| 配信契約 | `bootstrap.json` / `archive_index.p{page}.json` | 初期表示と段階ロード一覧 | [[RQ-FR-006]], [[RQ-FR-007]], 旧要求群（非正本） | 旧DD参照（非正本） |
| 配信契約 | `tag_master.json` / `highlights/{video_id}.json` / `wordcloud/{video_id}.png` | タグ辞書と詳細補助表示（波形/ワードクラウド） | [[RQ-FR-005]], 旧要求群（非正本） | 旧DD参照（非正本） |
| 運用API | `POST /api/v1/ops/ingestion/runs` | [[RQ-GL-002|収集実行]]起動 | [[RQ-FR-001]], [[RQ-FR-003]] | 旧DD参照（非正本） |
| 運用API | `GET /api/v1/ops/ingestion/runs/{run_id}` | 収集[[RQ-GL-002|run]]状態確認 | 旧要求群（非正本） | 旧DD参照（非正本） |
| 運用API | `GET /api/v1/ops/ingestion/runs/{run_id}/items` | 収集結果明細確認 | [[RQ-FR-004]], 旧要求群（非正本） | 旧DD参照（非正本） |
| 運用API | `POST /api/v1/ops/ingestion/runs/{run_id}/retry` | 再収集実行 | 旧要求群（非正本） | 旧DD参照（非正本） |
| 運用API | `GET /api/v1/ops/ingestion/latest` / `GET /api/v1/ops/diagnostics/health` | 最新結果/運用診断確認 | 旧要求群（非正本） | 旧DD参照（非正本） |
| 運用API | `POST /api/v1/ops/rechecks` / `GET /api/v1/ops/rechecks/{recheck_run_id}` | 配信前後再確認 | 旧要求群（非正本） | 旧DD参照（非正本） |
| 運用API | `POST /api/v1/admin/tags` / `PATCH /api/v1/admin/tags/{tag_id}` / `PATCH /api/v1/admin/videos/{video_id}/tags` | タグ更新/手動タグ付け | [[RQ-FR-005]], [[RQ-FR-009]], 旧要求群（非正本） | 旧DD参照（非正本） |
| 運用API | `POST /api/v1/admin/publish/tag-master` / `GET /api/v1/admin/publish/{publish_run_id}` | 配信反映[[RQ-GL-002|run]]監視 | 旧要求群（非正本） | 旧DD参照（非正本） |
| 運用API | `POST /api/v1/admin/docs/publish` / `GET /api/v1/admin/docs/publish/{docs_publish_run_id}` | docs公開[[RQ-GL-002|run]]監視 | 旧要求群（非正本） | 旧DD参照（非正本） |

## コメント密度波形静的配信契約
- **命名規約**: `highlights/{video_id}.json`（`video_id` はYouTube動画ID、拡張子は `json` 固定）。
- **データ内容**: 動画ID、生成時刻、波形系列（経過秒/密度値）、盛り上がり区間（開始秒/終了秒/密度指標/コメント件数）を保持する。
- **生成タイミング**: 収集[[RQ-GL-002|run]]完了後にBackend API内バッチで旧要件の生成処理を実行し、Web配信領域へ配置する。
- **HTTPステータス運用**:
  - `200`: 波形表示と区間クリック遷移を有効化。
  - `404`: 未生成扱いとして「盛り上がり区間なし」を表示。
  - `5xx`/ネットワーク失敗: 再試行導線付きの取得失敗表示。
- **フォールバック方針**: 波形データ不正・破損時は波形描画を中断し、モーダル機能（タグ、遷移、閉じる）を維持する。

## ワードクラウド静的配信契約
- **命名規約**: `wordcloud/{video_id}.png`（`video_id` はYouTube動画IDそのまま、拡張子は `png` 固定）。
- **生成タイミング**: 収集/前処理[[RQ-GL-002|run]]完了後にBackend API内バッチで事前生成し、Web配信領域へ配置する。
- **取得方式**: クライアントは詳細モーダル表示時に動画IDからURLを組み立てて取得する。
- **HTTPステータス運用**:
  - `200`: 画像表示。
  - `404`: 未生成扱いとして「ワードクラウドなし」を表示。
  - `5xx`/ネットワーク失敗: 再試行導線付きの取得失敗表示。
- **キャッシュ方針**: 画像は `Cache-Control` を付与して配信し、更新はファイル差し替えで反映する。
- **フォールバック方針**: 画像不正・破損時は表示を中断し、モーダル機能（タグ、遷移、閉じる）を維持する。

## 変更履歴
- 2026-02-28: 旧文脈の参考文書であることを明記し、用語誤リンクとパス変数命名（snake_case）を補正 [[RQ-RDR-002]]
- 2026-02-19: 運用APIの外部入出力キー（`snake_case`）とヘルスチェック経路の正本を明記（旧ADR参照）
- 2026-02-14: バッチ仕様（一覧/イベント/実行制約/同時実行制御）の正本参照を [[BD-APP-API-002]] へ明記（旧ADR参照）
- 2026-02-13: API一覧正本と個別API正本（[[BD-APP-API-002]]）の責務分離ルールを追加（旧ADR参照）
- 2026-02-11: API一覧表へ詳細設計リンク列を追加し、運用API契約を個別API単位で整理（旧ADR参照）
- 2026-02-11: 生成タイミングを「単一Backend API（Hono）内バッチ実行」へ明確化（旧ADR参照）
- 2026-02-11: 利用者向け参照契約にHTTP API共通方針の参照を追加（旧ADR参照）
- 2026-02-11: DB正本前提の契約境界（参照系/更新系分離）を追記（旧ADR参照）
- 2026-02-11: `archive_index.p{page}.json` 契約の用語参照を [[RQ-GL-009]] に統一し、主な利用要求へ [[RQ-FR-006]] を追加
- 2026-02-10: 新規作成
- 2026-02-11: 旧要件対応としてワードクラウド静的配信契約（`wordcloud/{video_id}.png`）を追加
- 2026-02-11: 旧要件変更に合わせ、コメント密度波形の静的配信契約（`highlights/{video_id}.json`）を追加
