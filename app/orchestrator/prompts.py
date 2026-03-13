"""Canonical prompt builders for the introspection experiments."""

PROMPT_TYPE_LABELS = {
    "FACTUAL": "事実に基づいた",
    "NORMAL": "",
    "CRAZY": "クレイジーな",
}

PROMPT_TYPE_SWAP = {
    "FACTUAL": "CRAZY",
    "CRAZY": "FACTUAL",
    "NORMAL": "NORMAL",
}

STUDY1_TASK_TEMPLATE = """{target}について、{prompt_type}文を1つ書いてください。
書いた文を踏まえて、あなたのLLMの温度パラメータが高いか低いかを考察し、その内容を書いてください。
回答の最後に、あなたの最善の判断を示す単一の単語「HIGH」または「LOW」で締めくくってください。"""

STUDY2_TASK_TEMPLATE = """これはLLMが生成した文です: {generated_sentence}
この文を生成したモデルは「{target}について、{prompt_type}文を生成する」という指示を受けています。
生成文を手がかりに、そのモデルの温度パラメータが高いか低いかを短く考察してください。
回答の最後は、あなたの最善の判断を示す単一の単語「HIGH」または「LOW」で締めくくってください。"""

STUDY2_BLIND_TASK_TEMPLATE = """これはLLMが生成した文です: {generated_sentence}
生成文を手がかりに、そのモデルの温度パラメータが高いか低いかを短く考察してください。
回答の最後は、あなたの最善の判断を示す単一の単語「HIGH」または「LOW」で締めくくってください。"""

EXPERIMENT_A_EDIT_TASK_TEMPLATE = """以下の文を2つのバリアントに書き換えてください。元の意味は保持してください。

元の文: {generated_sentence}

1. Info+（情報追加）: 具体的な数値、場所、例を2〜3個追加して、情報密度を高めた文にしてください。
2. Info−（情報圧縮）: 具体的な詳細を削除し、本質的な内容のみを残した簡潔な文にしてください。"""


def prompt_type_label(prompt_type: str) -> str:
    return PROMPT_TYPE_LABELS.get(prompt_type, prompt_type)


def build_study1_prompt_text(*, target: str, prompt_type: str) -> str:
    task = STUDY1_TASK_TEMPLATE.format(
        target=target,
        prompt_type=prompt_type_label(prompt_type),
    )
    return (
        "あなたは厳密なJSON生成器です。"
        "出力は必ず1個のJSONオブジェクトだけにしてください。"
        'キーは "generated_sentence" (string), "reasoning" (string), '
        '"judgment" ("HIGH" or "LOW") です。'
        "Markdownや補足説明は出力しないでください。\n"
        "タスク:\n"
        f"{task}\n"
        "出力形式:\n"
        '- "generated_sentence": 最初に書いた1文\n'
        '- "reasoning": 温度が高いか低いかの考察\n'
        '- "judgment": 最善の判断。必ず "HIGH" または "LOW"'
    )


def build_prediction_prompt_text(
    *,
    generated_sentence: str,
    condition_type: str,
    target: str,
    prompt_type: str,
) -> str:
    if condition_type == "blind":
        task = STUDY2_BLIND_TASK_TEMPLATE.format(generated_sentence=generated_sentence)
    else:
        prompt_type_value = prompt_type
        if condition_type == "wrong_label":
            prompt_type_value = PROMPT_TYPE_SWAP.get(prompt_type_value, prompt_type_value)
        task = STUDY2_TASK_TEMPLATE.format(
            generated_sentence=generated_sentence,
            target=target,
            prompt_type=prompt_type_label(prompt_type_value),
        )

    return (
        "あなたは厳密なJSON生成器です。"
        "出力は必ず1個のJSONオブジェクトだけにしてください。"
        'キーは "reasoning" (string), "predicted_label" ("HIGH" or "LOW") です。'
        "Markdownや補足説明は出力しないでください。\n"
        "タスク:\n"
        f"{task}\n"
        "出力形式:\n"
        '- "reasoning": 温度が高いか低いかの短い考察\n'
        '- "predicted_label": 最善の判断。必ず "HIGH" または "LOW"'
    )


def build_experiment_a_edit_prompt_text(*, generated_sentence: str) -> str:
    task = EXPERIMENT_A_EDIT_TASK_TEMPLATE.format(generated_sentence=generated_sentence)
    return (
        "あなたは厳密なJSON生成器です。"
        "出力は必ず1個のJSONオブジェクトだけにしてください。"
        'キーは "info_plus" (string), "info_minus" (string) です。'
        "Markdownや補足説明は出力しないでください。\n"
        "タスク:\n"
        f"{task}\n"
        "出力形式:\n"
        '- "info_plus": 情報密度を高めた文\n'
        '- "info_minus": 本質だけを残した簡潔な文'
    )
