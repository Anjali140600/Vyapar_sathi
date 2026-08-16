import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from evaluation.ragas_eval.config import EvaluationConfig
from evaluation.ragas_eval.dataset import load_cases
from evaluation.ragas_eval.models import EvaluationCase, EvaluationRecord
from evaluation.ragas_eval.metrics import METRIC_INPUTS
from evaluation.ragas_eval.reporting import build_summary, write_report
from evaluation.ragas_eval.runner import run_evaluation


class FakeApplication:
    def run(self, case):
        return EvaluationRecord(
            case=case,
            response="GST is an indirect tax.",
            retrieved_contexts=["GST is a destination-based indirect tax."],
            latency_ms=1.25,
        )


class FakeMetricSuite:
    async def score_records(self, records):
        for record in records:
            record.scores = {"faithfulness": 0.8, "context_recall": 0.6}
            record.reasons = {"faithfulness": "grounded", "context_recall": "partial"}
        return records


class DatasetTests(unittest.TestCase):
    def test_load_cases_rejects_duplicate_ids(self):
        path = Path("cases.jsonl")
        row = {"case_id": "same", "user_input": "question", "reference": "answer"}
        contents = json.dumps(row) + "\n" + json.dumps(row) + "\n"
        with patch.object(Path, "is_file", return_value=True), patch.object(
            Path, "open", mock_open(read_data=contents)
        ):
            with self.assertRaisesRegex(ValueError, "duplicate case_id"):
                load_cases(path)

    def test_load_cases_supports_comments_and_limit(self):
        path = Path("cases.jsonl")
        rows = [
            {"case_id": "one", "user_input": "q1", "reference": "a1"},
            {"case_id": "two", "user_input": "q2", "reference": "a2"},
        ]
        contents = "# note\n" + "\n".join(json.dumps(row) for row in rows)
        with patch.object(Path, "is_file", return_value=True), patch.object(
            Path, "open", mock_open(read_data=contents)
        ):
            cases = load_cases(path, limit=1)
        self.assertEqual([case.case_id for case in cases], ["one"])


class ReportingTests(unittest.TestCase):
    def test_config_rejects_unknown_provider(self):
        with self.assertRaisesRegex(ValueError, "RAGAS_PROVIDER"):
            EvaluationConfig(provider="unknown")

    def test_faithfulness_receives_current_ragas_inputs(self):
        self.assertEqual(
            METRIC_INPUTS["faithfulness"],
            ("user_input", "response", "retrieved_contexts"),
        )

    def test_missing_metric_score_fails_gate(self):
        case = EvaluationCase("case", "question", "reference")
        record = EvaluationRecord(case, "answer", ["context"], 1.0)
        record.scores = {"faithfulness": None}
        summary = build_summary([record], {"faithfulness": 0.7})
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["coverage"]["faithfulness"]["scored"], 0)

    def test_aggregate_gate(self):
        case = EvaluationCase("case", "question", "reference")
        record = EvaluationRecord(case, "answer", ["context"], 1.0)
        record.scores = {"faithfulness": 0.8}
        summary = build_summary([record], {"faithfulness": 0.7})
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["aggregates"]["faithfulness"], 0.8)

    def test_partial_attempt_does_not_replace_latest_complete_report(self):
        case = EvaluationCase("case", "question", "reference")
        record = EvaluationRecord(case, "answer", ["context"], 1.0)
        record.scores = {"faithfulness": None}
        record.errors = {"faithfulness": "quota"}
        summary = build_summary([record], {"faithfulness": 0.7})
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            existing = {"complete": True}
            (output_dir / "latest.json").write_text(json.dumps(existing), encoding="utf-8")
            write_report([record], summary, output_dir, {"mode": "ragas"})
            latest = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(latest, existing)
            self.assertTrue((output_dir / "latest_attempt.json").is_file())


class RunnerTests(unittest.TestCase):
    def test_collect_only_writes_reproducible_report(self):
        case = EvaluationCase("gst", "What is GST?", "An indirect tax.")
        config = EvaluationConfig(
            dataset_path=Path("cases.jsonl"),
            output_dir=Path("results"),
            db_folder=Path("db"),
            thresholds={},
        )
        with patch("evaluation.ragas_eval.runner.load_cases", return_value=[case]), patch(
            "evaluation.ragas_eval.runner._sha256", return_value="abc123"
        ), patch(
            "evaluation.ragas_eval.runner.write_report", return_value=Path("results/run")
        ) as write_report:
            summary, run_dir = run_evaluation(config, FakeApplication(), None)
        self.assertEqual(summary["sample_count"], 1)
        self.assertEqual(run_dir, Path("results/run"))
        self.assertEqual(write_report.call_args.args[3]["mode"], "collect-only")
        self.assertEqual(write_report.call_args.args[0][0].case.case_id, "gst")


if __name__ == "__main__":
    unittest.main()
