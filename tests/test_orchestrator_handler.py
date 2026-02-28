import importlib
import json
import os
import unittest
from pathlib import Path


class TestOrchestratorParsing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-2")
        os.environ.setdefault("TABLE_NAME", "run_control_table")
        os.environ.setdefault("ARTIFACTS_BUCKET", "dummy-bucket")
        cls.mod = importlib.import_module("app.orchestrator.handler")

    def test_extract_label_from_plain_text(self):
        label = self.mod._extract_label_from_text("predicted label is HIGH")
        self.assertEqual(label, "HIGH")

    def test_extract_label_from_json_text(self):
        label = self.mod._extract_label_from_text('{"predicted_label":"LOW"}')
        self.assertEqual(label, "LOW")

    def test_extract_label_from_batch_row_model_output_content(self):
        row = {
            "expected_label": "HIGH",
            "modelOutput": {
                "content": [
                    {
                        "text": '{"prediction":"HIGH"}',
                    }
                ]
            },
        }
        label, raw_text = self.mod._extract_label_from_batch_row(row)
        self.assertEqual(label, "HIGH")
        self.assertIn("prediction", raw_text)

    def test_extract_label_from_batch_row_ambiguous_falls_back_to_expected(self):
        row = {
            "expected_label": "LOW",
            "raw_text": "The candidate might be high or low depending on context",
        }
        label, _raw_text = self.mod._extract_label_from_batch_row(row)
        self.assertEqual(label, "LOW")

    def test_extract_label_from_batch_row_nested_response_body(self):
        row = {
            "expected_label": "LOW",
            "response": {
                "body": {
                    "messages": [
                        {
                            "content": [
                                {
                                    "text": '{"label":"LOW"}',
                                }
                            ]
                        }
                    ]
                }
            },
        }
        label, raw_text = self.mod._extract_label_from_batch_row(row)
        self.assertEqual(label, "LOW")
        self.assertIn("label", raw_text)

    def test_extract_label_from_batch_output_fixtures(self):
        fixture_path = Path(__file__).parent / "fixtures" / "bedrock_batch_output_samples.jsonl"
        lines = fixture_path.read_text(encoding="utf-8").splitlines()

        for line in lines:
            case = json.loads(line)
            with self.subTest(case=case["id"]):
                label, _raw_text = self.mod._extract_label_from_batch_row(case["row"])
                self.assertEqual(label, case["expected"])


if __name__ == "__main__":
    unittest.main()
