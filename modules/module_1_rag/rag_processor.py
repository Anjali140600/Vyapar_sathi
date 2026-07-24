import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from chromadb.utils import embedding_functions
from llm.tinyllama_client import TinyLlamaClient


class RAGModule:
    def __init__(
        self,
        data_folder="modules/module_1_rag/data",
        db_folder="modules/module_1_rag/chroma_db"
    ):
        self.data_folder = data_folder
        self.db_folder = db_folder

        os.makedirs(self.data_folder, exist_ok=True)
        os.makedirs(self.db_folder, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.db_folder)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        self.collection_name = "knowledge_base"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )

        self.llm = TinyLlamaClient()

    def process(self, keywords: str) -> str:
        keywords = keywords.replace("gsst", "gst")
        parts = [w.strip().lower() for w in keywords.split(",") if w.strip()]
        query = " ".join(parts)

        results = self.collection.query(
            query_texts=[query],
            n_results=5
        )

        context_chunks = results.get("documents", [[]])[0]

        if not context_chunks:
            return "I could not find enough related information in the knowledge base."

        useful_chunks = []
        for chunk in context_chunks:
            chunk_lower = chunk.lower()

            if any(x in chunk_lower for x in [
                "form gst", "ewb", "part b", "rate of gst on services"
            ]):
                continue

            useful_chunks.append(chunk)

        if not useful_chunks:
            useful_chunks = context_chunks

        best_chunk = ""
        max_score = 0

        for chunk in useful_chunks:
            score = sum(1 for w in parts if w in chunk.lower())
            if score > max_score:
                max_score = score
                best_chunk = chunk

        if not best_chunk:
            best_chunk = useful_chunks[0]

        prompt = f"""
Answer in ONE short sentence.

Question: {keywords}

Context:
{best_chunk}

Answer:
"""

        response = self.llm.generate(prompt)
        clean = " ".join(response.strip().split())

        if "." in clean:
            clean = clean.split(".")[0] + "."

        if len(clean.split()) > 20:
            clean = best_chunk.split(".")[0].strip() + "."

        return clean

    def load_pdf(self, file_path: str):
        if not os.path.exists(file_path):
            return f"Error: {file_path} not found."

        loader = PyPDFLoader(file_path)
        pages = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150
        )

        docs = text_splitter.split_documents(pages)

        documents = []
        metadatas = []
        ids = []

        base = os.path.basename(file_path)

        for i, doc in enumerate(docs):
            text = doc.page_content.strip()
            if not text:
                continue

            documents.append(text)
            metadatas.append({
                "source": base,
                "page": doc.metadata.get("page", None),
            })
            ids.append(f"{base}_chunk_{i}")

        if documents:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

        return f"Successfully loaded {len(documents)} chunks from {file_path}"