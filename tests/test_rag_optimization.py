import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.rag_service import RAGService


class FakeCollection:
    def __init__(self, documents=None):
        self.documents = documents or []
        self.metadatas = [{"source": "legacy.pdf"} for _ in self.documents]
        self.upsert_calls = []

    def count(self):
        return len(self.documents)

    def get(self, include=None):
        return {"documents": self.documents, "metadatas": self.metadatas}

    def query(self, query_texts, n_results, include=None):
        documents = self.documents[:n_results]
        return {
            "documents": [documents],
            "distances": [[float(index) for index in range(len(documents))]],
            "metadatas": [self.metadatas[:n_results]],
        }

    def upsert(self, **kwargs):
        self.upsert_calls.append(kwargs)


def make_service(collection):
    client = MagicMock()
    client.get_or_create_collection.return_value = collection
    temporary_directory = tempfile.TemporaryDirectory()
    with patch(
        "app.services.rag_service.chromadb.PersistentClient", return_value=client
    ), patch(
        "app.services.rag_service.embedding_functions.DefaultEmbeddingFunction",
        return_value=object(),
    ):
        service = RAGService(db_folder=temporary_directory.name)
    service._temporary_directory = temporary_directory
    return service


class HybridRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.legacy_documents = [
            "RATE OF GST ON SERVICES",
            "Q: Is GST applicable on milk transport? A: No, transport of milk is exempt from GST. "
            "Q: Is healthcare taxed under GST? A: No, healthcare services are exempt from GST.",
            "Central Goods and Services Tax Rules. Application in FORM GST PCT-01 through the common portal.",
            "Restaurants without AC are taxed at 12%. Restaurants with AC are taxed at 18%.",
        ]
        self.service = make_service(FakeCollection(self.legacy_documents))

    def tearDown(self):
        self.service._temporary_directory.cleanup()

    def test_authoritative_healthcare_fact_outranks_legacy_dense_result(self):
        documents = self.service.query("Are healthcare services exempt from GST?", n_results=3)
        self.assertTrue(documents[0].startswith("Q: Are healthcare services exempt"))

        answer = self.service.build_concise_answer(
            "Are healthcare services exempt from GST?", documents
        )
        self.assertIn("clinical establishment", answer)
        self.assertNotIn("transport of milk", answer)
        self.assertFalse(answer.lower().startswith("no,"))

    def test_exact_entity_and_intent_select_mobile_rate(self):
        documents = self.service.query("What is the GST rate on mobile phones?", n_results=3)
        answer = self.service.build_concise_answer(
            "What is the GST rate on mobile phones?", documents
        )
        self.assertEqual(
            answer,
            "Mobile phones classified under heading 8517 generally attract 18% GST.",
        )

    def test_unrelated_query_is_rejected(self):
        self.assertEqual(self.service.query("How do I bake sourdough bread?"), [])

    def test_other_tax_domains_are_rejected(self):
        for question in (
            "What is income tax?",
            "How does French value-added tax work?",
            "How is municipal property tax calculated?",
        ):
            with self.subTest(question=question):
                self.assertEqual(self.service.query(question), [])

    def test_common_gst_name_variant_is_normalized(self):
        self.assertEqual(
            self.service._normalize_query("Explain Goods & Services Tax"),
            "explain gst",
        )

    def test_expected_fact_is_selected_for_each_evaluation_topic(self):
        expectations = {
            "What is GST?": "destination-based indirect tax levied",
            "What are the main GST rate slabs in India now?": "5% merit rate",
            "What is the difference between CGST and SGST?": "intra-State supply",
            "When is IGST charged?": "inter-State supplies",
            "Are educational services exempt from GST?": "eligible educational institution",
            "What GST applies to restaurant services?": "5% GST without input tax credit",
        }
        for question, expected in expectations.items():
            with self.subTest(question=question):
                documents = self.service.query(question, n_results=3)
                answer = self.service.build_concise_answer(question, documents)
                self.assertIn(expected, answer)

    def test_paraphrased_questions_select_the_same_authoritative_topics(self):
        expectations = {
            "Explain state GST versus central GST on a local sale": "CGST is collected",
            "What tax percentage applies to a smartphone?": "18% GST",
            "Is hospital treatment GST-free?": "clinical establishment",
            "What GST applies when dining at a standalone restaurant?": "5% GST",
            "Do schools charge GST on teaching services?": "eligible educational institution",
        }
        for question, expected in expectations.items():
            with self.subTest(question=question):
                documents = self.service.query(question, n_results=3)
                answer = self.service.build_concise_answer(question, documents)
                self.assertIn(expected, answer)


class IngestionTests(unittest.TestCase):
    def test_ingestion_creates_atomic_qa_chunks_with_metadata_and_upsert(self):
        collection = FakeCollection()
        service = make_service(collection)
        loader = MagicMock()
        loader.load.return_value = [
            SimpleNamespace(
                page_content=(
                    "Q: What is CGST? A: CGST is the central component. "
                    "Q: What is SGST? A: SGST is the state component."
                )
            )
        ]
        try:
            with patch("app.services.rag_service.os.path.exists", return_value=True), patch(
                "app.services.rag_service.PyPDFLoader", return_value=loader
            ):
                count = service.ingest_pdf("gst-guide.pdf")
        finally:
            service._temporary_directory.cleanup()

        self.assertEqual(count, 2)
        self.assertEqual(len(collection.upsert_calls), 1)
        call = collection.upsert_calls[0]
        self.assertEqual(len(call["ids"]), 2)
        self.assertEqual(call["metadatas"][0]["source"], "gst-guide.pdf")
        self.assertEqual(call["metadatas"][0]["page"], 1)
        self.assertTrue(call["documents"][0].startswith("Q: What is CGST?"))


if __name__ == "__main__":
    unittest.main()
