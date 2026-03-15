# Run Report: `99ac6373-98ad-4ae2-b911-030b05e64450`

## 1. 対象

- run_id: `99ac6373-98ad-4ae2-b911-030b05e64450`
- 作成日時: `2026-03-13T06:43:49+00:00`
- region: `ap-southeast-2`
- models: `NOVA_MICRO`, `GEMMA_3_12B`, `MINISTRAL_3_8B`
- loops: `10`
- full_cross: `true`
- editor_model: `NOVA_MICRO`

このレポートは、`.ai_workspace/llm-temp-introspection/scripts/generate_artifact_blog_report.py` の出力をもとに、日本語で要点を整理したものです。詳細な元レポートは [artifact_blog_report.md](artifact_blog_report.md) を参照してください。

## 2. 成果物検証

- 必須ソース成果物は `8/8` 件そろっており、解析に必要な入力は欠けていません。
- ただし report completeness は `partial` です。対象 phase は `Study 1`, `Study 2 across`, `Experiment A`, `Experiment D` です。
- `run_manifest.json` の `estimated_model_cost_usd` は `2.66` です。
- invalid 件数は、`run_manifest.json` 集計で `13`、スクリプトの再計算で `244` でした。
- partial 判定の主因は、複数 phase で `modelOutput text is not a JSON object` が出ていることです。

phase ごとの valid / invalid は次の通りです。

| Phase | Valid rows | Invalid rows | 備考 |
| --- | ---: | ---: | --- |
| Study 1 | 4,745 | 205 | invalid は主に `MINISTRAL_3_8B` |
| Study 2 within | 2,535 | 0 | 完了 |
| Study 2 across | 5,069 | 3 | 少数の JSON 不正 |
| Experiment A | 7,628 | 23 | JSON 不正あり |
| Experiment D | 19,328 | 13 | JSON 不正あり |

## 3. 主要結果

### Study 1

- 全体の `HIGH rate` は `0.596`、極端温度帯での self-judgment accuracy は `0.519` でした。
- prompt_type ごとの `HIGH rate` は `FACTUAL=0.286`, `NORMAL=0.516`, `CRAZY=0.985` です。
- 一方で extreme accuracy は `FACTUAL=0.526`, `NORMAL=0.558`, `CRAZY=0.473` にとどまり、極端条件でも温度自己判定は強くありません。
- モデル別の安定性では、`GEMMA_3_12B` は invalid `0`、`NOVA_MICRO` は `2`、`MINISTRAL_3_8B` は `203` でした。

解釈:
prompt_type は `HIGH` 判定を大きく動かしていますが、モデル自身がその温度差を安定して自己識別できているとは言いにくい結果です。特に `MINISTRAL_3_8B` は JSON 出力の安定性がボトルネックです。

### Study 2

- within-model は `2,535` 行、accuracy は `0.480` でした。
- prompt_type 別 accuracy は `FACTUAL=0.493`, `NORMAL=0.479`, `CRAZY=0.467` です。
- across-model は `5,069` 行で、元 CSV から再計算した overall accuracy は `0.494` でした。
- across-model の predictor 別 accuracy は `NOVA_MICRO=0.496`, `GEMMA_3_12B=0.493`, `MINISTRAL_3_8B=0.494` です。

解釈:
within / across ともに精度はほぼ 0.5 近辺で、生成文だけから元モデルの temperature を当てる能力は概ねチャンスレベルです。

### Experiment A

- `info_plus` による `P(HIGH)` の上昇量は、`GEMMA_3_12B=+0.270`, `NOVA_MICRO=+0.090`, `MINISTRAL_3_8B=+0.048` でした。
- 95% bootstrap CI はそれぞれ `GEMMA_3_12B=[0.244, 0.295]`, `NOVA_MICRO=[0.061, 0.120]`, `MINISTRAL_3_8B=[0.019, 0.076]` です。
- ただし accuracy は全 predictor で `info_plus` の方が低く、`info_minus - info_plus` は `GEMMA_3_12B=+0.105`, `NOVA_MICRO=+0.041`, `MINISTRAL_3_8B=+0.014` でした。

解釈:
追加情報は正解率を上げるよりも、`HIGH` 方向の判断バイアスを強めています。特に `GEMMA_3_12B` で効果が大きく、情報密度に強く反応していると読めます。

### Experiment D

- `wrong_label` 条件の accuracy は `blind` 条件より全 predictor で悪化しました。
- `accuracy_delta_wrong_label_minus_blind` は `GEMMA_3_12B=-0.084`, `MINISTRAL_3_8B=-0.073`, `NOVA_MICRO=-0.115` です。
- `wrong_label` 条件の `P(HIGH)` は `GEMMA_3_12B=0.912`, `MINISTRAL_3_8B=0.892`, `NOVA_MICRO=0.997` まで上昇しました。
- balanced accuracy は `full / blind / wrong_label` のいずれでもおおむね `0.48-0.53` に収まっています。

解釈:
誤ったラベル情報は識別性能を改善せず、`HIGH` 方向への強い誘導だけを生んでいます。`NOVA_MICRO` はその影響が最も強く、`wrong_label` 条件でほぼ常に `HIGH` を返しています。

## 4. 結論

この run は、成果物の欠落はない一方で、複数 phase に JSON 形式不正が残っているため「解析可能だが完全ではない」状態です。結果としては、temperature 推定そのものは `Study 2` でほぼチャンスレベルに留まりました。一方、`Experiment A` と `Experiment D` では、追加情報や誤ラベルが `HIGH` 判定を強く押し上げることが一貫して観測され、モデルは真の temperature よりも与えられた文脈手掛かりに引っ張られやすいことが示されています。

## 5. 関連成果物

- 元レポート: [artifact_blog_report.md](artifact_blog_report.md)
- phase 集計: [tables/phase_completion.csv](tables/phase_completion.csv)
- Study 1 集計: [tables/study1_prompt_summary.csv](tables/study1_prompt_summary.csv)
- Experiment A 差分: [tables/experiment_a_delta.csv](tables/experiment_a_delta.csv)
- Experiment D 集計: [tables/experiment_d_accuracy.csv](tables/experiment_d_accuracy.csv)
- 図: [figures/study1_high_rate_heatmap.png](figures/study1_high_rate_heatmap.png)
- 図: [figures/experiment_a_delta.png](figures/experiment_a_delta.png)
- 図: [figures/experiment_d_accuracy.png](figures/experiment_d_accuracy.png)
