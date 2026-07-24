import os
import re
import chromadb
from chromadb.utils import embedding_functions
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class RAGService:
    def __init__(self, db_folder="modules/module_1_rag/chroma_db"):
        self.db_folder = db_folder
        os.makedirs(self.db_folder, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.db_folder)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=self.embedding_fn
        )

    def query(self, query_text: str, n_results=3) -> list:
        """Fetches relevant context snippets from the knowledge base."""
        # Simple typo correction for common mistakes
        clean_query = query_text.replace("gsst", "gst").lower()
        
        results = self.collection.query(
            query_texts=[clean_query],
            n_results=n_results
        )
        
        docs = results.get("documents", [[]])[0]
        return docs

    def build_concise_answer(self, query_text: str, docs: list[str], max_lines: int = 3) -> str:
        if not docs:
            return "I could not find a relevant GST answer in the knowledge base."

        keywords = self._keywords(query_text)
        qa_answers = self._extract_qa_answers(docs, keywords)
        if qa_answers:
            return "\n".join(qa_answers[:max_lines])

        candidates = []
        seen = set()

        for doc in docs:
            for sentence in self._split_sentences(doc):
                normalized = self._normalize_candidate(sentence)
                lower = normalized.lower()
                if not normalized or len(normalized) < 20:
                    continue
                if normalized in seen:
                    continue
                seen.add(normalized)
                score = self._score_candidate(normalized, keywords)
                candidates.append((score, normalized))

        if not candidates:
            return "I found GST documents, but not a clean short answer."

        if any(word in keywords for word in ("mobile", "phone", "phones")):
            direct_hits = [text for _, text in candidates if any(word in text.lower() for word in ("mobile", "phone", "phones"))]
            if not direct_hits:
                rate_fallback = self._rate_fallback(docs, max_lines)
                if rate_fallback:
                    return rate_fallback

        best = [text for _, text in sorted(candidates, key=lambda item: item[0], reverse=True)[:max_lines]]
        return "\n".join(best)

    @staticmethod
    def _keywords(query_text: str) -> list[str]:
        tokens = re.findall(r"[a-z0-9]+", (query_text or "").lower())
        stopwords = {"what", "is", "the", "on", "for", "a", "an", "and", "of", "to", "my", "tell", "me", "about"}
        keywords = [token for token in tokens if len(token) > 2 and token not in stopwords]
        specific_keywords = [token for token in keywords if token not in {"gst", "tax", "rules", "rule"}]
        return specific_keywords or keywords

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        raw = (text or "").replace("\r", "\n")
        if not raw.strip():
            return []
        parts = re.split(r"\n+|(?<=[.!?])\s+", raw)
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def _normalize_candidate(text: str) -> str:
        normalized = " ".join((text or "").split()).strip(" -:")
        if not normalized:
            return ""
        if normalized.startswith("A:"):
            normalized = normalized[2:].strip()
        if normalized.startswith("Q:"):
            return ""
        if re.fullmatch(r"[A-Z\s]{6,}", normalized):
            return ""
        if re.match(r"^\d+%?\s+GST\s+SERVICES?$", normalized, flags=re.IGNORECASE):
            return ""
        if len(normalized.split()) < 4:
            return ""
        if normalized.lower().startswith(("chapter ", "rule ", "section ", "form ")):
            return ""
        if len(normalized) > 180:
            normalized = normalized[:177].rstrip(",;:") + "..."
        return normalized

    def _extract_qa_answers(self, docs: list[str], keywords: list[str]) -> list[str]:
        answers = []
        seen = set()

        for doc in docs:
            pairs = re.findall(r"Q:\s*(.*?)\s*A:\s*(.*?)(?=\s*Q:|$)", doc, flags=re.IGNORECASE | re.DOTALL)
            for question, answer in pairs:
                q_text = " ".join(question.split()).lower()
                answer_parts = self._split_sentences(answer)
                a_text = ""
                for part in answer_parts:
                    candidate = self._normalize_candidate(part)
                    if candidate:
                        a_text = candidate
                        break
                if not a_text:
                    continue
                if keywords and not any(word in q_text or word in a_text.lower() for word in keywords):
                    continue
                if a_text in seen:
                    continue
                seen.add(a_text)
                answers.append(a_text)

        return answers

    @staticmethod
    def _score_candidate(text: str, keywords: list[str]) -> int:
        lower = text.lower()
        score = 0

        for keyword in keywords:
            if keyword in lower:
                score += 4

        helpful_terms = ("exempt", "taxed", "applicable", "rate", "%", "services", "goods", "mobile", "phones")
        for term in helpful_terms:
            if term in lower:
                score += 2

        noisy_terms = ("form ", "proper officer", "practitioner", "commissioner", "application", "portal", "citizen of india")
        for term in noisy_terms:
            if term in lower:
                score -= 5

        score -= max(len(text) // 120, 0)
        return score

    def _rate_fallback(self, docs: list[str], max_lines: int) -> str:
        lines = []
        for doc in docs:
            for sentence in self._split_sentences(doc):
                candidate = self._normalize_candidate(sentence)
                if not candidate:
                    continue
                lower = candidate.lower()
                if "gst rates are" in lower or "most common gst rate" in lower:
                    lines.append(candidate)
        return "\n".join(lines[:max_lines])

    def ingest_pdf(self, file_path: str):
        """Loads and splits a PDF into the vector database."""
        if not os.path.exists(file_path):
            return 0
            
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        docs = splitter.split_documents(pages)
        
        documents = []
        ids = []
        base_name = os.path.basename(file_path)
        
        for i, doc in enumerate(docs):
            content = doc.page_content.strip()
            if content:
                documents.append(content)
                ids.append(f"{base_name}_{i}")
        
        if documents:
            self.collection.add(ids=ids, documents=documents)
            
        return len(documents)
