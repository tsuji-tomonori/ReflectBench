---
id: BD-APP-API-004
title: OpenAPI配布とAPIバージョン境界
doc_type: API設計
phase: BD
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-11
updated: '2026-02-28'
up:
- '旧参照'
related:
- '旧参照'
- '[[BD-APP-API-005]]'
- '旧参照'
tags:
- llm-temp-introspection
- BD
- API
---

## スコープ注記
- 本文書は `docs/2.基本設計(BD)/03.アプリ(APP)` の旧文脈文書を保持する参考文書であり、現行スコープの正本ではない。
- 現行スコープの正本は `[[RQ-SC-001]]` と DD-INF/DD-APP 系列を優先する。
- 本文中の「旧参照」は、現行リポジトリに存在しない旧要求/旧設計IDを示す。


## 設計方針
- APIの公開経路は `/api/v1/*` に統一し、OpenAPI仕様は `/openapi/v1/openapi.json` で配布する。
- OpenAPI UIは `/openapi/` 配下に配置し、仕様参照先を `/openapi/v1/openapi.json` に固定する。
- API版とOpenAPI版は同一バージョンで管理する。
- バージョン互換性、廃止通知、CI契約検証は [[BD-APP-API-005]] の共通規約に従う。

## 契約一覧
| 種別 | パス | 用途 | 認証 |
|---|---|---|---|
| OpenAPI JSON | `/openapi/v1/openapi.json` | 機械可読仕様 | 必須 |
| OpenAPI UI | `/openapi/` | 人向け仕様閲覧 | 必須 |
| 業務API | `/api/v1/*` | 運用・業務処理 | 必須 |

## バージョニング
- v1は以下を対応付ける。
  - `/openapi/v1/openapi.json`
  - `/api/v1/*`
- 破壊的変更時は v2 を新設し、v1は互換期間終了後に廃止する。
- OpenAPI `info.version` は SemVer で管理し、MAJORを経路版（`v1`/`v2`）変更判断に利用する。

## 廃止運用
- 廃止対象のAPI/スキーマは OpenAPI へ `deprecated: true` を明記する。
- 廃止時は移行先、移行手順、サンセット日を仕様へ記載する。
- 可能な範囲で `Deprecation` と `Sunset` ヘッダを返し、利用者（旧定義）が検知可能な状態を維持する。

## 認証境界
- `/openapi/*` と `/api/*` は Cognito JWT を必須とする。
- 未認証時は仕様閲覧・API実行のいずれも拒否する。

## 契約検証
- CIで OpenAPI Lint、破壊的変更検知、コントラクトテストを実行する。
- 破壊的変更が検出された場合は、並行提供計画または新経路版の設計完了まで配信を停止する。

## 変更履歴
- 2026-02-11: バージョニング/廃止/CI契約検証の運用規約を追加 旧参照
- 2026-02-11: 新規作成 旧参照