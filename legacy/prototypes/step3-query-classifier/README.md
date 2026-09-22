# Step 3 — Query type classifier (CLI only)

Separate from Step 1 and Step 2. **No web server** — run from the terminal.

Classifies text into:

| Type | Meaning |
|------|---------|
| **sql** | Answerable from your transaction database |
| **general** | GST / general knowledge (RAG), not your ledger |
| **mixed** | Needs both — e.g. “how much I spent on milk products” (DB) **and** “what GST applies” (rules) |

Mixed is detected when **ledger/purchase** words (`brought`, `bought`, `how much total`, etc.) appear together with **GST/tax** words, or when scores for both sides are strong enough.

## Usage

cd step3-query-classifier

One-line query:
node cli.js "What is my total expense this month?"

Interactive:
node cli.js

Pipe:
echo "What is GST on milk in India?" | node cli.js

Help:
node cli.js --help

## Output

JSON on stdout: queryType, normalizedQuery, keywords, scores, signals.

## Code

- cli.js — entry point  
- server/classifier.js — classification logic  
- server/stopwords.js — filler words removed from keywords