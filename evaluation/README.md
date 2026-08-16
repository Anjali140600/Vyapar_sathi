# RAGAS evaluation module

This directory evaluates the GST retrieval path independently from the production API. It calls the same `RAGService.query()` and `RAGService.build_concise_answer()` methods used by the chat orchestrator, captures the ordered ChromaDB contexts and final answer, validates them as a RAGAS `EvaluationDataset`, and scores every case.

The default retrieval depth is three contexts, matching the production
`RAGService.query()` default. Override `--n-results` only for an explicit retrieval
experiment.

## Metrics

| Metric | What it diagnoses |
| --- | --- |
| Context precision | Whether relevant chunks are ranked ahead of irrelevant chunks |
| Context recall | Whether the retrieved chunks contain the claims required by the reference answer |
| Faithfulness | Whether the application answer is supported by its retrieved chunks |
| Answer relevancy | Whether the answer directly addresses the user's question |
| Factual correctness | Whether the answer's claims agree with the curated reference answer |

RAGAS uses an evaluator LLM for all five metrics and an embedding model for answer relevancy. These judge models are deliberately independent from TinyLlama, which prevents the application from grading itself.

## Setup

Use a supported Python environment (Python 3.10-3.13 is recommended), activate it, and install the self-contained evaluation dependencies:

```powershell
python -m pip install -r .\evaluation\requirements.txt
```

Choose `RAGAS_PROVIDER=openai` with `OPENAI_API_KEY`, or
`RAGAS_PROVIDER=google` with `GOOGLE_API_KEY`, in `.env`. The Google provider uses
Gemini's OpenAI-compatible endpoint, so the same Google key covers the evaluator
and embedding requests without requiring the Google SDK. Optional settings are
shown in the root `.env.example`:

- `RAGAS_PROVIDER` (`openai` or `google`; default `openai`)
- `RAGAS_EVALUATOR_MODEL` (for example `gpt-4o-mini` or an available Gemini Flash model)
- `RAGAS_EMBEDDING_MODEL` (for example `text-embedding-3-small` or `gemini-embedding-001`)
- `RAGAS_MAX_CONCURRENCY` (default `2`)
- `OPENAI_BASE_URL` for a compatible endpoint
- `RAGAS_GOOGLE_BASE_URL` only when overriding Google's default compatibility endpoint

The local ChromaDB collection must already contain the GST PDFs. If needed, ingest them using the application's existing ingestion command before evaluation.

## Run

First verify collection and answer capture without incurring judge-model usage:

```powershell
python -m evaluation.ragas_eval --collect-only --limit 2
```

Run the full evaluation:

```powershell
python -m evaluation.ragas_eval
```

For a controlled comparison with the 9 August pre-optimization report, keep the
original dataset and retrieval depth unchanged:

```powershell
python -m evaluation.ragas_eval `
  --dataset evaluation/datasets/gst_rag_eval_baseline_20260809.jsonl `
  --provider google --n-results 5 --max-concurrency 1 --no-gate
```

Do not compare reports when metric coverage is incomplete. The baseline report
`20260809T133320Z` contains quota failures and scored only 5-6 of 8 cases per
metric, so its aggregate values are provisional rather than a complete baseline.

The provider can also be selected explicitly:

```powershell
python -m evaluation.ragas_eval --provider google
```

Override gates or retrieval depth when testing a change:

```powershell
python -m evaluation.ragas_eval --n-results 3 `
  --evaluator-model gpt-4o-mini `
  --threshold faithfulness=0.80 `
  --threshold context_precision=0.75
```

Exit codes are `0` for success, `1` for configuration/runtime failure, and `2` when a quality gate fails. Use `--no-gate` for exploratory runs that should always exit successfully after producing scores.

Each run writes an ignored timestamped directory under `evaluation/results/` containing:

- `report.json`: configuration, aggregate scores, gates, every retrieved context, per-case scores, judge reasons, and errors
- `scores.csv`: flat per-case scores for analysis or CI artifacts
- `latest_attempt.json`: the latest run, including quota-limited or partial attempts
- `latest.json`: the latest RAGAS report with complete metric coverage
- `latest_collection.json`: the latest collect-only application-output report

## Dataset maintenance

The starter set is `datasets/gst_rag_eval.jsonl`. Each non-comment line must contain a unique `case_id`, `user_input`, and human-reviewed `reference`; `category` and `source` are optional. References should be checked against both the indexed material and current authoritative sources. A current reference that is absent from an old indexed PDF is a useful test: low recall/correctness exposes knowledge-base staleness. Add cases from real user failures and keep a balanced mix of concepts, rates, exemptions, paraphrases, and hard retrieval cases.

Do not silently update references to match a poor application answer. A knowledge-base or tax-law update should instead be reviewed as a versioned dataset change.

Useful authoritative references:

- [RAGAS metric catalog](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/)
- [RAGAS v0.4 migration and collections API](https://docs.ragas.io/en/latest/howtos/migrations/migrate_from_v03_to_v04/)
- [GST Council 56th meeting rate-rationalisation recommendations](https://gstcouncil.gov.in/recommendations-56th-meeting-gst-council-held-new-delhi-today)
