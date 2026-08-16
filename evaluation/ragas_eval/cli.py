from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

from .application import RAGApplicationAdapter
from .config import DEFAULT_THRESHOLDS, EvaluationConfig
from .metrics import RagasMetricSuite
from .runner import run_evaluation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Vyapar Sathi's GST RAG pipeline with RAGAS."
    )
    parser.add_argument("--dataset", type=Path, default=EvaluationConfig.dataset_path)
    parser.add_argument("--output-dir", type=Path, default=EvaluationConfig.output_dir)
    parser.add_argument("--db-folder", type=Path, default=EvaluationConfig.db_folder)
    parser.add_argument("--n-results", type=int, default=EvaluationConfig.n_results)
    parser.add_argument("--provider", choices=("openai", "google"), help="Override RAGAS_PROVIDER")
    parser.add_argument("--evaluator-model", help="Override RAGAS_EVALUATOR_MODEL")
    parser.add_argument("--embedding-model", help="Override RAGAS_EMBEDDING_MODEL")
    parser.add_argument("--max-concurrency", type=int, help="Concurrent RAGAS metric calls")
    parser.add_argument("--limit", type=int, help="Run only the first N dataset cases")
    parser.add_argument("--collect-only", action="store_true", help="Capture app outputs without calling judge models")
    parser.add_argument("--no-gate", action="store_true", help="Do not return a failing exit code for thresholds")
    parser.add_argument(
        "--threshold",
        action="append",
        default=[],
        metavar="METRIC=VALUE",
        help="Override an aggregate quality gate; may be repeated",
    )
    return parser


def parse_thresholds(values: list[str]) -> dict[str, float]:
    thresholds = dict(DEFAULT_THRESHOLDS)
    for item in values:
        try:
            name, raw_value = item.split("=", 1)
            value = float(raw_value)
        except ValueError as exc:
            raise ValueError(f"invalid threshold {item!r}; expected METRIC=VALUE") from exc
        name = name.strip()
        if name not in thresholds:
            raise ValueError(f"unknown metric {name!r}; choose from {', '.join(sorted(thresholds))}")
        if not 0 <= value <= 1:
            raise ValueError(f"threshold {item!r} must be between 0 and 1")
        thresholds[name] = value
    return thresholds


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        base_config = EvaluationConfig()
        config = replace(
            base_config,
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            db_folder=args.db_folder,
            n_results=args.n_results,
            provider=args.provider or base_config.provider,
            evaluator_model=args.evaluator_model or base_config.evaluator_model,
            embedding_model=args.embedding_model or base_config.embedding_model,
            max_concurrency=(
                args.max_concurrency
                if args.max_concurrency is not None
                else base_config.max_concurrency
            ),
            thresholds=parse_thresholds(args.threshold),
        )
        application = RAGApplicationAdapter(str(config.db_folder), n_results=config.n_results)
        metric_suite = None if args.collect_only else RagasMetricSuite(
            provider=config.provider,
            evaluator_model=config.evaluator_model,
            embedding_model=config.embedding_model,
            max_concurrency=config.max_concurrency,
        )
        summary, run_dir = run_evaluation(config, application, metric_suite, limit=args.limit)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Report: {run_dir}")
    if args.collect_only:
        print(f"Collected {summary['sample_count']} application outputs (no RAGAS scores).")
        return 0

    for name, value in sorted(summary["aggregates"].items()):
        rendered = "ERROR" if value is None else f"{value:.3f}"
        gate = summary["gates"].get(name)
        threshold = f" (minimum {gate['threshold']:.2f})" if gate else ""
        print(f"{name}: {rendered}{threshold}")
    print("Quality gates: " + ("PASS" if summary["passed"] else "FAIL"))
    return 0 if args.no_gate or summary["passed"] else 2
