# Python services

These services contain the standalone AI pipeline used by Vyapar Sathi.

- `rag`: GST document retrieval, source PDFs, and persistent ChromaDB data
- `llm`: shared Groq/Ollama model client
- `routing`: intent classification between RAG, database, and calculation input
- `database_humanizer`: converts database results into concise responses
- `calculator_humanizer`: converts calculation results into concise responses
- `cli.py`: combines all services into an interactive command-line assistant
- `ingest_pdf.py`: loads a PDF into the RAG store

Run modules from the repository root so imports and the shared `.env` resolve consistently:

```powershell
.\venv\Scripts\python.exe -m python_services.cli
.\venv\Scripts\python.exe -m python_services.run_rag "milk, gst"
.\venv\Scripts\python.exe -m python_services.run_db "total amount, 21000"
.\venv\Scripts\python.exe -m python_services.run_calc "profit, 34000"
```
