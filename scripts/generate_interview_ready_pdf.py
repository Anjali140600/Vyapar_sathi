from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.generate_chat_summary_pdf import PdfRenderer, parse_markdown

SOURCE = ROOT / "docs" / "interview_ready_diagrams_and_features.md"
OUTPUT = ROOT / "docs" / "interview_ready_diagrams_and_features.pdf"


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    blocks = parse_markdown(markdown)
    renderer = PdfRenderer()
    renderer.render(blocks)
    renderer.save_pdf(OUTPUT)
    print(f"Created PDF: {OUTPUT}")


if __name__ == "__main__":
    main()
