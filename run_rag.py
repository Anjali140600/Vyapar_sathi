import sys
from modules.module_1_rag.rag_processor import RAGModule

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"RAG MODULE OUTPUT:\n{RAGModule().process(query)}")
    else:
        print("Usage: python run_rag.py <keywords>")
        print("Example: python run_rag.py milk, gst")
