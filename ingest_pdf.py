import sys
import os
from modules.module_1_rag.rag_processor import RAGModule


def ingest():
    if len(sys.argv) < 2:
        print("Usage: python ingest_pdf.py <path_to_pdf>")
        print("Example: python ingest_pdf.py modules/module_1_rag/data/sample.pdf")
        return

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    print(f"Ingesting PDF: {pdf_path}...")

    module = RAGModule()
    result = module.load_pdf(pdf_path)

    print(result)


if __name__ == "__main__":
    ingest()