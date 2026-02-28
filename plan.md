実装前提を決め打ちします。
**単一リージョンのフルサーバレス構成**としては、今回は **`ap-southeast-2`（Sydney）** を採用するのが一番きれいです。`google.gemma-3-12b-it`、`mistral.ministral-3-8b-instruct`、`qwen.qwen3-32b-v1:0` は Bedrock の対応モデル／Batch 対応モデルとして確認でき、`amazon.nova-micro-v1:0` は `ap-southeast-2` から **APAC inference profile** `apac.amazon.nova-micro-v1:0` で利用できます。推論プロファイルは**ソースリージョン課金**で、追加のルーティング料金はありません。

`Qwen3 32B` は Bedrock の実装上は **`qwen.qwen3-32b-v1:0`** として扱います。
なお、Gemma 3 12B と Ministral 3 8B は単体で見ると US のほうが少し安い価格表記もありますが、**Qwen3 32B を含めて 1 リージョンに閉じた設計**にするなら、Sydney で揃えるのが実装・運用ともに最も素直です。

## 採用する前提

この設計は、あなたの現在の実験コードを前提に、次で固定しています。

* **Study1 は 10 回**
* **Study2 は within + across で全モデル完全クロス**

  * within: 同一 generator / predictor
  * across: generator × predictor の全組合せ（self は within でカバー）
* **追加実験 A / D も実施**
* **追加実験 A の editor は `amazon.nova-micro-v1:0` に固定**

  * 理由は最安で、今回の採用モデル集合の中に収まるため
* **すべて Bedrock Batch Inference**
* 現在のコード条件のままだと、総 LLM コール数は **73,200** 件です

---

## 料金試算

### 1回のフル実行あたりの Bedrock モデル費

今回の試算は、**あなたの ZIP 内の prompt / response 長**を元に、**文字数 ≒ トークン数の粗い proxy**で見積もっています。
なので、請求実績とは **±20〜30%** くらいずれる可能性がありますが、実装判断には十分使えます。

| モデル            | Bedrock で使う ID                    | Batch 単価（Input / Output, per 1M tokens） | 推定 Input | 推定 Output |      推定費用 |
| -------------- | --------------------------------- | --------------------------------------: | -------: | --------: | --------: |
| Nova Micro     | `apac.amazon.nova-micro-v1:0`     |                       $0.0175 / $0.0700 |    3.87M |     3.40M | **$0.31** |
| Gemma 3 12B IT | `google.gemma-3-12b-it`           |                     $0.04635 / $0.14935 |    3.51M |     3.07M | **$0.62** |
| Ministral 3 8B | `mistral.ministral-3-8b-instruct` |                     $0.07725 / $0.07725 |    3.51M |     3.07M | **$0.51** |
| Qwen3 32B      | `qwen.qwen3-32b-v1:0`             |                       $0.0773 / $0.3090 |    3.51M |     3.07M | **$1.22** |

**合計: 約 $2.66 / run**

この単価は、Sydney の Bedrock 価格表を使っています。Gemma / Ministral はオンデマンド単価から **Batch 50% 引き**で計算し、Qwen3 32B は価格表にある **Batch 単価そのもの**を使っています。Nova Micro は Nova のオンデマンド単価に Bedrock の Batch 50% 割引を当てて見積もっています。

参考までに、同条件を **オンデマンド**で回すと概算は **約 $5.31 / run** です。

### フェーズ別の概算

| フェーズ               |      概算費用 |
| ------------------ | --------: |
| Study1             | **$0.26** |
| Study2 within      | **$0.14** |
| Study2 across      | **$0.42** |
| 追加実験A: edit        | **$0.03** |
| 追加実験A: predict     | **$0.56** |
| 追加実験D: blind       | **$0.70** |
| 追加実験D: wrong-label | **$0.56** |

一番重いのは **Qwen3 32B の output 単価**が効くフェーズで、特に **追加実験 D** が支配的です。

### インフラ費

インフラ側は **API Gateway / Lambda / S3 / CloudWatch Logs** が中心です。
この規模だと、通常は **Bedrock モデル費のほうが支配的**で、サーバレス基盤費は相対的に小さくなります。課金の性質としては、Lambda はリクエスト数＋実行時間、S3 は保存容量＋PUT/GET、CloudWatch はログ取り込み量で発生します。

---

## 推奨インフラ構成

### 全体像

```text
Client
  -> API Gateway (HTTP API)
    -> StartRun Lambda
      -> Durable Orchestrator Lambda (qualified ARN / alias)
         -> Bedrock Batch Inference
         -> S3 (input / output / normalized / reports)
         -> CloudWatch Logs / Metrics
         -> SNS (optional)
    -> Status Lambda
      -> S3 / CloudWatch 参照
```

### AWS リソース

**1. S3 バケット 1つ**

* 例: `llm-temp-introspection-artifacts`
* 保存先:

  * `runs/{run_id}/config.json`
  * `runs/{run_id}/manifests/{phase}/{model}/part-xxxxx.jsonl`
  * `runs/{run_id}/batch-output/{phase}/{model}/...`
  * `runs/{run_id}/normalized/{phase}/...jsonl`
  * `runs/{run_id}/reports/...`

**2. Lambda**

* `start_run_fn`

  * HTTP エントリポイント
  * run config 検証
  * durable orchestrator 起動
* `orchestrator_fn`

  * **Lambda Durable Functions** 有効化
  * 全フェーズの列挙、Batch job 投入、待機、正規化、集計
* `status_fn`

  * 実行状態取得
  * S3 上の manifest / reports を返す

**3. API Gateway (HTTP API)**

* `POST /runs`
* `GET /runs/{run_id}`
* `GET /runs/{run_id}/artifacts`

**4. IAM**

* Lambda 実行ロール
* Bedrock Batch 用サービスロール

  * `bedrock.amazonaws.com` が Assume
  * 対象 S3 prefix に read/write

**5. CloudWatch**

* Lambda logs
* Job failure alarm
* Orchestrator failure alarm

**6. SNS（任意）**

* 完了通知
* 失敗通知

---

## Lambda Durable Functions を使う理由

Durable Functions は、**長時間の状態保持付き実行**を Lambda 上で扱うための機能で、CDK では `DurableConfig` を設定して有効化します。実行には **qualified ARN（version / alias 付き）** が必要で、Python 用 SDK も提供されています。実行タイムアウトは最大 **366日**まで設定できます。([AWS ドキュメント][1])

実装上の注意として、

* **durable execution は関数作成時に有効化する**
* 既存 Lambda に後付けすると **resource replacement** が起きる
  という制約があります。なので、最初から `orchestrator_fn` は durable 前提で CDK 定義してください。([AWS ドキュメント][1])

---

## Lambda の処理フロー

### 0. `POST /runs`

`start_run_fn` が受け取る入力例

* 実験設定

  * loops = 10
  * models = 4
  * study2 full cross = true
  * experiment_a editor = nova_micro
* 出力先 prefix
* shard size
* polling interval

`start_run_fn` の役割:

1. 入力検証
2. `run_id` 生成
3. `config.json` を S3 に保存
4. `orchestrator_fn` の **alias ARN** を指定して durable 実行開始
5. `202 Accepted` で `run_id` を返す

---

### 1. Study1 列挙

`orchestrator_fn` 内の最初の durable step です。

やること:

1. 4 モデル × 11 temperature × 3 prompt_type × 5 target × 10 loops
2. 合計 **6,600 レコード**を列挙
3. 1レコード = 1つの Batch inference input line

出力:

* `runs/{run_id}/manifests/study1/{model}/part-00001.jsonl` など

**設計値**

* shard size は **500 records**
* Bedrock Batch の最小レコード数は **100** なので、500 は安全で扱いやすい値です。([AWS ドキュメント][2])

500 records/shard にすると、全体でだいたい **148 job 前後**になります。

---

### 2. Batch job 投入

各 shard ごとに `CreateModelInvocationJob` を呼びます。Batch inference job は S3 input / output と、Bedrock 用サービスロールを指定して作成します。

モデルルーティングは次で固定します。

* Nova Micro

  * **`apac.amazon.nova-micro-v1:0`**
* Gemma 3 12B IT

  * **`google.gemma-3-12b-it`**
* Ministral 3 8B

  * **`mistral.ministral-3-8b-instruct`**
* Qwen3 32B

  * **`qwen.qwen3-32b-v1:0`**

---

### 3. Job 完了待ち

`GetModelInvocationJob` で状態を見ます。

Durable Functions でやること:

* 2〜5分おきに poll
* wait 中は durable state に退避
* 完了後に次 step へ進む

ここで重要なのは、**ワークフロー全体を 15 分に押し込む必要はない**ことです。
個々の Lambda 実行ではなく、**durable execution 全体**で長い実験を捌きます。([AWS ドキュメント][3])

---

### 4. 結果の正規化

Batch output を S3 から読んで、共通 JSON に変換します。

ここは **今の LangChain `with_structured_output()` 依存を外す**のが重要です。
Batch と相性がいいのは、

* prompt で **strict JSON** を返させる
* Lambda 側で **Pydantic 検証**
* 失敗レコードは `invalid/` に退避

という構成です。

正規化後の canonical schema 例:

* `Study1Record`

  * model_id
  * temperature
  * prompt_type
  * target
  * loop_index
  * generated_sentence
  * reasoning
  * judgment
* `PredictionRecord`

  * generator_model
  * predictor_model
  * phase
  * source_record_id
  * predicted_label
  * raw_text

---

### 5. Study2 候補生成

Study1 の normalized 結果から downstream の入力を作ります。

* **Study2**

  * low <= 0.2
  * high >= 0.8
* **Experiment A / D**

  * low <= 0.5
  * high >= 0.8

ここで、

* within 用 manifest
* across 用 manifest
* Experiment A edit 用 manifest
* Experiment D blind / wrong-label 用 manifest

を作ります。

---

### 6. Study2 実行

Study2 は 2系統です。

**within**

* generator と predictor が同一

**across**

* generator × predictor の全組合せ
* self は within でカバーするので除外

ここも Study1 と同じで、

* manifest 作成
* batch submit
* poll
* normalize
  の繰り返しです。

---

### 7. 追加実験 A

A は 2段です。

**A-1: edit**

* 対象: NORMAL prompt のみ
* editor model: **Nova Micro 固定**
* 出力: `info_plus`, `info_minus`

**A-2: predict**

* 4 predictor 全部で
* `info_plus`, `info_minus` を予測

この 2段構成にすると、今のコードと近い形でそのまま移植できます。

---

### 8. 追加実験 D

D は 2系統です。

* **blind**

  * sentence のみで予測
* **wrong-label**

  * prompt_type ラベルを意図的に入れ替えて予測

どちらも manifest を作って、4 predictor 全部に流します。

---

### 9. 集計とレポート出力

最後に `reports/` を作ります。

最低限出すもの:

* `study1_summary.csv`
* `study2_within.csv`
* `study2_across.csv`
* `experiment_a.csv`
* `experiment_d.csv`
* `run_manifest.json`

余裕があれば:

* Parquet
* confusion matrix
* 温度別プロット
* モデル別 accuracy / F1

---

## CDK 設計

### Stack 構成

**`ExperimentStack`**

* S3 bucket
* API Gateway HTTP API
* `start_run_fn`
* `orchestrator_fn`（durable）
* `status_fn`
* Bedrock batch service role
* CloudWatch alarms
* SNS topic（optional）

### `orchestrator_fn` の CDK ポイント

* runtime: Python 3.13
* durable execution: **有効化**
* execution role に **`AWSLambdaBasicDurableExecutionRolePolicy`**
* version / alias を発行
* API からは **alias ARN** を呼ぶ

Durable Functions は CDK で `DurableConfig` を設定して作成できます。([AWS ドキュメント][3])

---

## 実装上の変更ポイント

いまのコードベースからは、ここを変えるのが最短です。

### 1. `llm.py` を「直接 invoke」から「ルータ」に変える

いまは LangChain 経由の実行寄りですが、Batch 用には以下へ変更します。

* `logical_model_name -> bedrock_model_id`
* `phase -> prompt_builder`
* `task -> batch_manifest_line`
* `raw_output -> parser`

### 2. 実験ロジックを「列挙」と「実行」に分離

各 study / experiment は、

* `enumerate_tasks()`
* `build_manifest()`
* `normalize_outputs()`
  の 3層に分けると durable orchestration に載せやすいです。

### 3. Pydantic を canonical schema に寄せる

* `Study1Record`
* `Study2Record`
* `ExperimentARecord`
* `ExperimentDRecord`
* `RunConfig`
* `RunStatus`

### 4. レコード ID を deterministic にする

例:

* `sha256(run_id + phase + model + target + prompt_type + temp + loop_index)`

これで再実行や retry が楽になります。

---

## 私ならこの値で始めます

* region: **`ap-southeast-2`**
* shard size: **500**
* poll interval: **180 sec**
* orchestrator durable execution timeout: **7 days**
* durable retention: **30 days**
* Experiment A editor: **Nova Micro**
* output format: **strict JSON only**
* retry:

  * Bedrock job failure: shard 単位で 1回再試行
  * JSON parse failure: `invalid/` に退避して後で再処理

---

## まず実装する順番

1. **CDK で S3 / API / durable Lambda / status Lambda / IAM を作る**
2. **Study1 だけを Batch 化**
3. **S3 input/output と parser を固める**
4. **Study2 within**
5. **Study2 across**
6. **Experiment A**
7. **Experiment D**
8. **最後に report builder**

この順なら、最初の 1 スプリントで **Study1 のみ動く最小構成**まで持っていけます。

必要なら次に、**CDK のスタック構成（Construct 単位）** と **Lambda の Python モジュール構成** を、そのままコピペ実装しやすい形で切ります。

[1]: https://docs.aws.amazon.com/lambda/latest/dg/durable-getting-started-iac.html "https://docs.aws.amazon.com/lambda/latest/dg/durable-getting-started-iac.html"
[2]: https://docs.aws.amazon.com/general/latest/gr/bedrock.html "https://docs.aws.amazon.com/general/latest/gr/bedrock.html"
[3]: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/DurableConfig.html "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/DurableConfig.html"
