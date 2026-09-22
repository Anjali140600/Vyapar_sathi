"""Ingest the official CBIC GST goods-rate table into the local Chroma database."""

import hashlib
import re
from html.parser import HTMLParser

import requests

from backend.app.services.rag_service import RAGService


CBIC_GOODS_RATES_URL = (
    "https://cbic-gst.gov.in/hindi/gst-goods-services-rates.html"
)
BATCH_SIZE = 100


class GoodsTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.table_depth = 0
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if tag == "table" and attributes.get("id") == "goods_table":
            self.in_table = True
            self.table_depth = 1
            return

        if not self.in_table:
            return

        if tag == "table":
            self.table_depth += 1
        elif tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_table and self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.in_table:
            return

        if tag in {"td", "th"} and self.in_cell:
            clean_cell = " ".join(" ".join(self.cell_parts).split())
            self.row.append(clean_cell)
            self.in_cell = False
        elif tag == "tr" and self.row:
            self.rows.append(self.row)
            self.row = []
        elif tag == "table":
            self.table_depth -= 1
            if self.table_depth == 0:
                self.in_table = False


def fetch_goods_rows() -> list[list[str]]:
    response = requests.get(CBIC_GOODS_RATES_URL, timeout=90)
    response.raise_for_status()

    parser = GoodsTableParser()
    parser.feed(response.text)
    rows = [row for row in parser.rows if len(row) >= 7]
    if not rows:
        raise RuntimeError("The CBIC goods-rate table was not found on the page.")
    return rows


def build_record(row: list[str]):
    schedule, serial_number, hsn, description, cgst, sgst, igst = row[:7]
    if not description or description.lower() == "description of goods":
        return None

    total_rate = igst or _combined_rate(cgst, sgst)
    document = (
        f"Official CBIC GST goods rate: {description} "
        f"HSN or tariff heading: {hsn or 'not specified'}. "
        f"Total GST or IGST rate: {total_rate or 'not specified'}. "
        f"CGST rate: {cgst or 'not specified'}; "
        f"SGST or UTGST rate: {sgst or 'not specified'}. "
        f"Schedule: {schedule}; serial number: {serial_number}."
    )
    digest = hashlib.sha256("|".join(row).encode("utf-8")).hexdigest()[:24]
    metadata = {
        "source": "CBIC GST Goods and Services Rates",
        "source_url": CBIC_GOODS_RATES_URL,
        "schedule": schedule or "not specified",
        "serial_number": serial_number or "not specified",
        "hsn": hsn or "not specified",
    }
    return f"cbic-goods-{digest}", document, metadata


def _combined_rate(cgst: str, sgst: str) -> str:
    def parse_rate(value: str):
        match = re.search(r"\d+(?:\.\d+)?", value or "")
        return float(match.group()) if match else None

    cgst_value = parse_rate(cgst)
    sgst_value = parse_rate(sgst)
    if cgst_value is None or sgst_value is None:
        return ""
    combined = cgst_value + sgst_value
    return f"{combined:g}%"


def ingest() -> int:
    rows = fetch_goods_rows()
    records_by_id = {}
    for row in rows:
        record = build_record(row)
        if record:
            records_by_id[record[0]] = record
    records = list(records_by_id.values())
    rag = RAGService()

    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start:start + BATCH_SIZE]
        rag.collection.upsert(
            ids=[record[0] for record in batch],
            documents=[record[1] for record in batch],
            metadatas=[record[2] for record in batch],
        )
        print(f"Ingested {min(start + BATCH_SIZE, len(records))}/{len(records)}")

    return len(records)


if __name__ == "__main__":
    count = ingest()
    print(f"Finished ingesting {count} official CBIC goods-rate entries.")
