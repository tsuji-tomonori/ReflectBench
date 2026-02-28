---
id: BD-APP-API-002
title: 収集API設計
doc_type: API設計
phase: BD
version: 1.1.10
status: 下書き
owner: RQ-SH-001
created: 2026-01-31
updated: '2026-02-28'
up:
- '[[RQ-SC-001]]'
- '[[RQ-FR-001]]'
- '[[RQ-FR-003]]'
- '[[RQ-FR-004]]'
- '旧参照'
related:
- '旧参照'
- '旧参照'
- '旧参照'
- '旧参照'
- '[[BD-APP-API-005]]'
- '旧参照'
- '旧参照'
- '旧参照'
- '[[BD-APP-DATA-001]]'
- '[[DD-APP-API-001]]'
- '旧参照'
- '旧参照'
- '旧参照'
tags:
- llm-temp-introspection
- BD
- API
---

## スコープ注記
- 本文書は `docs/2.基本設計(BD)/03.アプリ(APP)` の旧文脈文書を保持する参考文書であり、現行スコープの正本ではない。
- 現行スコープの正本は `[[RQ-SC-001]]` と DD-INF/DD-APP 系列を優先する。



## 設計方針
- 収集APIは、運用制御API（実行受付・状態確認）として定義し、取得実装のライブラリや実行基盤には依存しない。
- 収集要求は 旧参照 に従い「公式取り込み」「出演補完取り込み」「差分更新」の3モードを共通契約で扱う。
- 配信前後再確認実行は 旧参照 の責務として同一[[RQ-GL-002|run]]体系で追跡可能にする。
- 本APIは管理画面の更新系契約を担い、利用者（旧定義）向け検索参照契約（静的JSON）と混在させない。
- バッチ一覧/バッチイベント/バッチ実行制約の正本は本書で管理し、システムコンテキストでは実行境界のみを扱う。
- 実処理は単一のBackend API（Hono）内で完結し、別デプロイのworkerサービスを持たない。
- 定期実行は外部スケジューラが同一運用APIを呼び出して開始し、処理本体は同一Backend API内で実行する。
- HTTPメソッド/ステータス/ページング/エラー表現/互換性は [[BD-APP-API-005]] を共通規約として適用する。
- 実装時の入力検証・例外集約（Hono + Zod）は [[BD-APP-API-005]] と 旧参照 の規約に従う。
- 具体的な入出力スキーマ、閾値パラメータ、エラーコード詳細の正本は DD（`DD-APP-API-*`）で管理し、本書は契約境界と運用ルールを正本とする。

## 契約対象
| 契約 | 用途 | 対応要求 |
|---|---|---|
| 実行受付契約 | [[RQ-GL-002|収集実行]]起動とモード指定 | [[RQ-FR-001]], [[RQ-FR-003]] |
| 実行状態契約 | [[RQ-GL-002|run]]状態・件数・失敗理由確認 | [[RQ-FR-001]], 旧参照 |
| 実行結果契約 | 更新種別と取得元区分の出力 | [[RQ-FR-004]], 旧参照 |
| タグ提案入力契約 | LLM貼り付け用の提案入力を生成 | 旧参照 |
| タグ提案取込契約 | LLM出力JSONを検証してDB反映 | 旧参照, [[RQ-FR-005]] |
| タグ更新契約 | タグ辞書の追加/更新/無効化 | [[RQ-FR-005]], [[RQ-FR-009]] |
| 配信反映契約 | DB正本から配信JSON再生成を起動 | 旧参照, 旧参照 |

## バッチ仕様正本
- バッチ一覧、バッチイベント一覧、バッチ実行制約、補助データ生成バッチ入出力契約、同時実行制御の正本は本書とする。
- システム全体の責務境界・配置境界は 旧参照 を参照する。

## バッチ一覧
| バッチID | バッチ名 | 起動契約 | 主な責務 | 状態遷移 | 詳細設計 |
|---|---|---|---|---|---|
| BAT-001 | 収集[[RQ-GL-002|run]]バッチ | `POST /api/v1/ops/ingestion/runs` | 収集対象解決、[[RQ-GL-002|収集実行]]、[[RQ-GL-002|run]]採番/集計 | `queued -> running -> succeeded\|failed\|partial\|cancelled` | 旧参照, 旧参照, 旧参照 |
| BAT-002 | 再収集[[RQ-GL-002|run]]バッチ | `POST /api/v1/ops/ingestion/runs/{run_id}/retry` | 失敗[[RQ-GL-002|run]]再実行、親[[RQ-GL-002|run]]連結、再実行回数制御 | `queued -> running -> succeeded\|failed\|partial\|cancelled` | 旧参照, 旧参照, 旧参照 |
| BAT-003 | 配信前後再確認実行バッチ | `POST /api/v1/ops/rechecks` | 配信前後メタデータ差分判定、差分集計記録 | `queued -> running -> succeeded\|failed\|partial\|cancelled` | 旧参照, 旧参照 |
| BAT-004 | 配信反映バッチ | `POST /api/v1/admin/publish/tag-master` | DB正本から成果物再生成、公開切替、失敗時ロールバック | `queued -> running -> succeeded\|failed\|rolled_back\|cancelled` | 旧参照, 旧参照 |
| BAT-005 | docs公開バッチ | `POST /api/v1/admin/docs/publish` | docsビルド、配信反映、無効化処理 | `queued -> running -> succeeded\|failed\|rolled_back` | 旧参照, 旧参照 |
| BAT-006 | 補助データ生成バッチ | 収集[[RQ-GL-002|run]]完了トリガ（内部） | コメント密度波形・ワードクラウド生成 | `queued -> running -> succeeded\|failed\|partial` | 旧参照, 旧参照, 旧参照 |
| BAT-007 | タグマスター即時更新バッチ | `POST /api/v1/admin/publish/tag-master`（publishScope=タグマスター） | タグ辞書変更後の即時公開反映 | `queued -> running -> succeeded\|failed\|rolled_back` | 旧参照, 旧参照 |

## バッチイベント一覧
| イベントID | イベント名 | 発火条件 | 対象バッチ | 記録先 | 詳細設計 |
|---|---|---|---|---|---|
| BEV-001 | `queued` | API受理直後に[[RQ-GL-002|run]]作成 | BAT-001〜BAT-005 | `ingestion_runs` / `recheck_runs` / `publish_runs` の `status=queued` | 旧参照, 旧参照, 旧参照 |
| BEV-002 | `running` | 同一Backend API内ジョブ実行モジュールで処理開始 | BAT-001〜BAT-005 | [[RQ-GL-002|run]]テーブル `status=running`、`started_at` | 旧参照, 旧参照, 旧参照, 旧参照 |
| BEV-003 | `succeeded` | 全ステップ成功で正常終了 | BAT-001〜BAT-005 | [[RQ-GL-002|run]]テーブル終端状態、成功件数/公開時刻 | 旧参照, 旧参照, 旧参照, 旧参照 |
| BEV-004 | `failed` | 非復旧エラーで終了 | BAT-001〜BAT-005 | `error_code`/`error_message`、監査ログ | 旧参照, 旧参照, 旧参照, 旧参照 |
| BEV-005 | `partial` | 一部対象のみ成功して終了 | BAT-001〜BAT-003 | 件数差分（`success_count`/`failed_count`/`unchanged_count`） | 旧参照, 旧参照, 旧参照, 旧参照 |
| BEV-006 | `rolled_back` | 公開切替失敗後に旧版へ切戻し完了 | BAT-004〜BAT-005 | `publish_runs.rollback_executed=true` | 旧参照, 旧参照, 旧参照 |
| BEV-007 | `cancelled` | 運用判断または安全停止で中断 | BAT-001〜BAT-004 | [[RQ-GL-002|run]]テーブル終端状態 `cancelled` | 旧参照, 旧参照, 旧参照, 旧参照 |

## バッチ実行制約
| バッチID | 最大実行時間 | Retry回数 | Retry間隔 | 同時実行数 | 備考 |
|---|---|---|---|---|---|
| BAT-001 | 60分 | 3回 | 30秒（指数バックオフ） | 1 | 外部API制限考慮 |
| BAT-002 | 30分 | 2回 | 1分 | 1 | 親[[RQ-GL-002|run]]の制約を継承 |
| BAT-003 | 30分 | 2回 | 30秒 | 1 | - |
| BAT-004 | 15分 | 3回 | 30秒 | 1 | ロールバック時間含む |
| BAT-005 | 30分 | 2回 | 1分 | 1 | ビルド時間含む |
| BAT-006 | 60分 | 3回 | 30秒 | 3 | 動画単位で並列可 |
| BAT-007 | 10分 | 3回 | 15秒 | 1 | - |

## BAT-006 入出力契約
- **起動イベント**: `S3 ObjectCreated` または収集[[RQ-GL-002|run]]完了イベント。
- **入力スキーマ（必須）**: `video_id`, `channel_id`, `meta_type`, `message_text`。
- **波形生成入力条件**: `meta_type=textMessageEvent` の行のみ対象とし、検出パターン初期値は `草|w|くさ|kusa`。
- **ワードクラウド入力条件**: 形態素抽出対象は `message_text`。公開チャット由来以外は処理対象外。
- **出力契約**: `highlights/{video_id}.json` と `wordcloud/{video_id}.png` を動画ID単位で再生成し、同一キー上書きで冪等性を担保する。
- **障害時挙動**: 波形/ワードクラウドの片系失敗は `partial` とし、失敗成果物のみ前回確定版を維持する。

## 同時実行制御
- BAT-001〜BAT-005 は同時実行数1を維持し、実行中は同種[[RQ-GL-002|run]]を受け付けない。
- BAT-006 は動画IDハッシュで最大3並列まで許容し、同一動画IDの重複実行は禁止する。
- 同時実行判定は [[RQ-GL-002|run]]作成時にロックを取得し、失敗時は `409 RUN_ALREADY_ACTIVE` を返す。

## 実行受付契約
- **必須入力**: `trigger_mode`, `run_kind`, `target_types`。
- **trigger_mode定義**:
  - `manual`: 管理画面からの手動起動。
  - `scheduled`: 外部スケジューラからの定期起動。
- **[[RQ-GL-002|run]]_kind定義**:
  - `official_ingestion`: 公式投稿の公開動画取り込み。
  - `appearance_supplement`: 出演判定 + 補完入力を併用した取り込み。
  - `incremental_update`: 既存データとの差分更新。
- **条件付き入力**:
  - `candidate_source_ref`: 出演補完入力の参照ID（モードが `appearance_supplement` のときのみ必須）。
  - `time_window`: 差分更新の対象期間（モードが `incremental_update` のとき任意）。
- **受付応答**: `run_id`, `accepted_at`, `trigger_mode`, `run_kind`, `requested_by` を返す。

## 契約キー命名ルール
- 運用APIの外部入出力キーは `snake_case` を正本とする。
- 内部実装（変数/関数名）の命名規約はDD実装規約（`camelCase`）に従うが、外部契約へ透過しない。

## 実行状態契約
- **状態遷移**: `queued -> running -> succeeded|failed|partial|cancelled`。
- **必須出力**:
  - 件数: `target_count`, `success_count`, `failure_count`。
  - 更新種別件数: `new_count`, `existing_count`, `backfill_count`, `recheck_count`。
  - 取得元区分件数: `official_count`, `supplement_count`, `incremental_count`。
- **失敗情報**: `failure_reason_code`, `failure_scope`, `retryable`。

## 実行結果契約
- 正規化対象は [[RQ-FR-004]] で定義した必須/任意属性へ写像できる形式で返す。
- 結果レコードは、動画ごとに `source_type`（公式/出演補完/差分更新）と `update_type`（新規/既存/補完/再確認）を保持する。
- 追跡性を担保するため、結果レコードは `run_id` と対応付ける。

## タグ提案入力契約
- **用途**: 収集結果と再確認差分から、[[RQ-SH-001|管理者]]が外部LLMへ貼り付ける入力を生成する。
- **入力例**: `run_id`, `video_ids[]`, `include_fields`（title/description/existing_tags/diff_summary）。
- **応答例**: `prompt_text`, `prompt_version`, `video_count`, `generated_at`。
- **制約**: 個人情報や秘密情報を含む拡張フィールドは出力対象外に固定する。

## タグ提案取込契約
- **用途**: 外部LLM出力JSONを管理画面から取込み、DB正本へ反映する。
- **入力例**: `import_payload`（`items[].video_id`, `items[].tags[]`, `items[].reason`）, `source`（`chatgpt`）, `requested_by`。
- **応答例**: `import_run_id`, `validated_count`, `applied_count`, `rejected_count`, `errors[]`。
- **検証**: 必須キー、型、重複、未知動画ID、未知タグID、無効タグIDを検証し、エラー明細を返す。
- **反映条件**: 検証成功レコードのみ反映し、失敗レコードは未反映で保持する。

## タグ提案取込のフォールバック
- LLM API障害（タイムアウト/レート制限/不正応答）時は、提案取込を中断して手動タグ更新へ縮退する。
- フォールバック時の応答は `degraded=true`, `fallback=manual_tagging` を返し、管理画面へ再実行導線を表示する。
- フォールバック発生時でも既存タグ正本は変更しない。

## タグ更新契約
- **用途**: 管理画面からタグ辞書を更新する。
- **入力例**: `tag_id`, `tag_name`, `tag_type_id`, `synonyms`, `is_active`。
- **応答例**: `tag_id`, `updated_at`, `propagation_state`。
- **制約**: `tag_id` の再利用禁止、重複slug拒否、削除要求は論理無効化へ変換。

## 配信反映契約
- **用途**: DB正本更新後に `tag_master.json` / `archive_index.pN.json` の再生成を起動する。
- **入力例**: `trigger_type`（manual/scheduled）, `scope`（tags/index/all）。
- **応答例**: `publish_run_id`, `started_at`, `target_artifacts`。
- **失敗時**: 再生成失敗は直前公開版を維持し、失敗理由と再試行可否を返す。

## [[BD-APP-API-003|エラーモデル]]（収集系）
- `INVALID_MODE`: 未定義モード指定。
- `MISSING_MODE_INPUT`: モード必須入力不足。
- `CANDIDATE_SOURCE_UNAVAILABLE`: 補完入力参照不能。
- `UPSTREAM_QUOTA_LIMIT`: 上流APIクォータ制限。
- `NORMALIZATION_CONFLICT`: 正規化時の整合不一致。

## 上流APIクォータ制御
- 収集開始前に当日残クォータを確認し、閾値未満（既定 10%）なら `QUOTA_LOW` で起動を拒否する。
- 実行中に `UPSTREAM_QUOTA_LIMIT` を受けた場合は無限リトライせず `partial` または `failed` で終了する。
- `retryable=true` の場合のみ翌日再開候補として記録し、同日内の自動再実行は行わない。
- クォータ関連エラーは `quota_snapshot`（使用量/残量/判定時刻）を[[RQ-GL-002|run]]へ保存する。

## 共通契約適用（要約）
- **メソッド意味論**: 実行受付は `POST`、状態取得は `GET`、更新は `PUT/PATCH`、削除は `DELETE` を原則とし、`GET` にボディを載せない。
- **一覧取得**: [[RQ-GL-002|run]]一覧/結果一覧を返す場合は `limit` + `cursor` を必須とし、`cursor` は opaque 値で返す。
- **エラー形式**: HTTPエラーは `application/problem+json` を標準とし、`type`/`title`/`status`/`detail`/`instance` を必須化する。
- **レート制限**: スロットリング時は `429` + `Retry-After` を返し、運用画面に再試行可能時刻を表示できるようにする。
- **可観測性**: `X-Request-Id` と `traceparent` を受け取り、応答/ログへ引き継ぐ。

## 非対象（本設計で固定しない事項）
- 外部API呼び出しライブラリ、実行言語、ジョブスケジューラ製品。
- 補完入力の具体ファイル形式（TSV/JSON/DB等）。
- 実行基盤のインフラ実装詳細（DD層で定義）。
- 将来追加する高度検索APIの検索アルゴリズムとランキング詳細。

## 変更履歴
- 2026-02-19: 再確認実行 用語を導入し、BDの責務を契約境界中心へ明示 旧参照
- 2026-02-19: 実行受付契約の必須入力を `target_types` へ統一し、外部契約キーの `snake_case` 正本を追記 旧参照
- 2026-02-14: バッチ一覧/イベント/実行制約およびBAT-006入出力契約・同時実行制御の正本を本書へ移管 旧参照
- 2026-02-14: BAT-007名称を `タグマスター（タグマスター）` 表記へ統一 旧参照
- 2026-02-13: 実行起動文脈（`trigger_mode`）と収集種別（`run_kind`）を分離し、[[RQ-GL-002|run]]状態語彙へ `cancelled` を追加 旧参照
- 2026-02-13: LLM提案取込の手動フォールバックと上流APIクォータ制御ルールを追加 旧参照
- 2026-02-11: 単一Backend API（Hono）モノリス前提（手動/定期とも同一API起動）を明記 旧参照
- 2026-02-11: 入力検証/例外集約の実装準拠先（[[BD-APP-API-005]] / 旧参照）を追記 旧参照
- 2026-02-11: HTTP API共通契約（メソッド意味論、Problem Details、ページング、429運用）の適用方針を追加 旧参照
- 2026-02-11: LLM支援タグ運用向けにタグ提案入力契約/タグ提案取込契約を追加 旧参照
- 2026-02-11: 管理画面向け更新契約（タグ更新/配信反映）を追加し参照系と責務分離 旧参照
- 2026-02-11: 取得3モード、実行契約、更新種別/取得元区分の出力契約を追加 旧参照
- 2026-02-10: 新規作成 旧参照
