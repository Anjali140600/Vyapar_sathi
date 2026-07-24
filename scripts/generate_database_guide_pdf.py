from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "project_database_interview_guide.md"
OUTPUT = ROOT / "docs" / "project_database_interview_guide.pdf"


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 50
MARGIN_TOP = 52
MARGIN_BOTTOM = 50
FONT_SIZE = 11
LEADING = 15
MAX_TEXT_WIDTH = 92


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def markdown_to_lines(markdown: str) -> list[str]:
    lines: list[str] = []
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            lines.append("")
            continue
        if line.startswith("# "):
            lines.append(line[2:].strip().upper())
            lines.append("")
            continue
        if line.startswith("## "):
            lines.append(line[3:].strip())
            lines.append("")
            continue
        if line.startswith("### "):
            lines.append(line[4:].strip())
            continue
        if line.startswith("- "):
            wrapped = textwrap.wrap("• " + line[2:].strip(), width=MAX_TEXT_WIDTH)
            lines.extend(wrapped or ["•"])
            continue
        if line[0].isdigit() and ". " in line[:4]:
            wrapped = textwrap.wrap(line.strip(), width=MAX_TEXT_WIDTH)
            lines.extend(wrapped or [line.strip()])
            continue
        wrapped = textwrap.wrap(line.strip(), width=MAX_TEXT_WIDTH)
        lines.extend(wrapped or [""])
    return lines


def paginate(lines: list[str]) -> list[list[str]]:
    max_lines = int((PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM) / LEADING)
    pages: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        current.append(line)
        if len(current) >= max_lines:
            pages.append(current)
            current = []
    if current:
        pages.append(current)
    return pages


def build_content_stream(page_lines: list[str]) -> bytes:
    y_start = PAGE_HEIGHT - MARGIN_TOP
    commands = ["BT", f"/F1 {FONT_SIZE} Tf", f"{MARGIN_X} {y_start} Td"]
    first_line = True
    for line in page_lines:
        safe = escape_pdf_text(line)
        if first_line:
            commands.append(f"({safe}) Tj")
            first_line = False
        else:
            commands.append(f"0 -{LEADING} Td")
            commands.append(f"({safe}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def build_pdf(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = []

    def add_object(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    content_ids = []
    page_ids = []
    for page_lines in pages:
        stream = build_content_stream(page_lines)
        content_obj = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream"
        )
        content_ids.append(add_object(content_obj))

    placeholder_page_ids = []
    for _ in pages:
        placeholder_page_ids.append(0)

    kids_placeholder = " ".join(f"{pid} 0 R" for pid in placeholder_page_ids)
    pages_tree_id = add_object(
        f"<< /Type /Pages /Kids [{kids_placeholder}] /Count {len(pages)} >>".encode("latin-1")
    )

    page_ids = []
    for content_id in content_ids:
        page_obj = (
            f"<< /Type /Page /Parent {pages_tree_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("latin-1")
        page_ids.append(add_object(page_obj))

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_tree_id - 1] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("latin-1")
    )

    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_tree_id} 0 R >>".encode("latin-1"))

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{i} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("latin-1")
    )
    return bytes(pdf)


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    lines = markdown_to_lines(markdown)
    pages = paginate(lines)
    OUTPUT.write_bytes(build_pdf(pages))
    print(f"Created PDF: {OUTPUT}")


if __name__ == "__main__":
    main()
