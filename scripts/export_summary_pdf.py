from __future__ import annotations

import re
import sys
from pathlib import Path


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT_MARGIN = 50
TOP_MARGIN = 50
BOTTOM_MARGIN = 50
FONT_SIZE = 11
LINE_HEIGHT = 16
MAX_CHARS = 88


def strip_markdown(line: str) -> str:
    line = re.sub(r"^#{1,6}\s*", "", line)
    line = re.sub(r"^\-\s+", "- ", line)
    line = re.sub(r"`([^`]*)`", r"\1", line)
    line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
    line = re.sub(r"\*([^*]+)\*", r"\1", line)
    return line.rstrip()


def wrap_text(text: str, width: int = MAX_CHARS) -> list[str]:
    if not text:
        return [""]
    words = text.split()
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def paginate(lines: list[str]) -> list[list[str]]:
    max_lines = (PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) // LINE_HEIGHT
    pages: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if len(current) >= max_lines:
            pages.append(current)
            current = []
        current.append(line)
    if current:
        pages.append(current)
    return pages


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_content_stream(page_lines: list[str]) -> bytes:
    y = PAGE_HEIGHT - TOP_MARGIN
    parts = ["BT", f"/F1 {FONT_SIZE} Tf"]
    for line in page_lines:
        safe = pdf_escape(line)
        parts.append(f"1 0 0 1 {LEFT_MARGIN} {y} Tm ({safe}) Tj")
        y -= LINE_HEIGHT
    parts.append("ET")
    content = "\n".join(parts).encode("latin-1", errors="replace")
    return content


def build_pdf(pages: list[list[str]], output_path: Path) -> None:
    objects: list[bytes] = []

    def add_object(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    font_obj = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    content_ids: list[int] = []
    page_ids: list[int] = []

    for page_lines in pages:
        stream = build_content_stream(page_lines)
        content_obj = add_object(
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"
        )
        content_ids.append(content_obj)
        page_obj = add_object(b"")
        page_ids.append(page_obj)

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    pages_obj = add_object(
        f"<< /Type /Pages /Count {len(page_ids)} /Kids [ {kids} ] >>".encode("latin-1")
    )

    for idx, page_obj in enumerate(page_ids):
        page_data = (
            f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> /Contents {content_ids[idx]} 0 R >>"
        ).encode("latin-1")
        objects[page_obj - 1] = page_data

    catalog_obj = add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("latin-1"))

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode(
            "latin-1"
        )
    )
    output_path.write_bytes(pdf)


def markdown_to_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        cleaned = strip_markdown(raw)
        if not cleaned.strip():
            lines.append("")
            continue
        if raw.lstrip().startswith("#"):
            lines.append(cleaned.upper())
            lines.append("")
            continue
        lines.extend(wrap_text(cleaned))
    return lines


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/export_summary_pdf.py <input.md> <output.pdf>")
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    text = input_path.read_text(encoding="utf-8")
    lines = markdown_to_lines(text)
    pages = paginate(lines)
    build_pdf(pages, output_path)
    print(f"PDF created: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
