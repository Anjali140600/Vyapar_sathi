from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "chat_summary_vyapar_sathi.md"
OUTPUT = ROOT / "docs" / "chat_summary_vyapar_sathi.pdf"

PAGE_W = 1240
PAGE_H = 1754
MARGIN_X = 90
MARGIN_TOP = 95
MARGIN_BOTTOM = 90
CONTENT_W = PAGE_W - (2 * MARGIN_X)

COLORS = {
    "bg": "#f7f4ee",
    "text": "#1f2937",
    "muted": "#6b7280",
    "rule": "#d7d0c4",
    "title": "#0f172a",
    "h1": "#8a5a2b",
    "h2": "#8a5a2b",
    "h3": "#1d4f5f",
    "box_fill": "#fff8e8",
    "box_border": "#d9b35f",
    "table_head_fill": "#e7eef5",
    "table_border": "#b8c3ce",
    "table_alt_fill": "#f9fbfd",
    "code_fill": "#eef2f7",
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/calibrib.ttf",
                "C:/Windows/Fonts/segoeuib.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/calibri.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
            ]
        )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


FONT_TITLE = load_font(30, bold=True)
FONT_H1 = load_font(24, bold=True)
FONT_H2 = load_font(20, bold=True)
FONT_H3 = load_font(17, bold=True)
FONT_BODY = load_font(15, bold=False)
FONT_BOLD = load_font(15, bold=True)
FONT_SMALL = load_font(12, bold=False)
FONT_CODE = load_font(14, bold=False)


@dataclass
class ParagraphBlock:
    text: str
    kind: str = "body"


@dataclass
class HeadingBlock:
    level: int
    text: str


@dataclass
class BulletBlock:
    items: list[str]


@dataclass
class NumberedBlock:
    items: list[str]


@dataclass
class RevisionBoxBlock:
    title: str
    body: list[str]


@dataclass
class TableBlock:
    rows: list[list[str]]


@dataclass
class CodeBlock:
    lines: list[str]


Block = ParagraphBlock | HeadingBlock | BulletBlock | NumberedBlock | RevisionBoxBlock | TableBlock | CodeBlock


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    return int(draw.textlength(text, font=font))


def line_height(font: ImageFont.ImageFont, extra: int = 0) -> int:
    bbox = font.getbbox("Ag")
    return (bbox[3] - bbox[1]) + extra


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if text_width(draw, trial, font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def parse_markdown(markdown: str) -> list[Block]:
    lines = markdown.splitlines()
    blocks: list[Block] = []
    i = 0

    while i < len(lines):
        raw = lines[i].rstrip()
        stripped = raw.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i].rstrip())
                i += 1
            blocks.append(CodeBlock(lines=code_lines))
            i += 1
            continue

        if stripped.startswith("> [Revision Box]"):
            title = stripped.replace("> [Revision Box]", "").strip()
            i += 1
            body: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                body.append(lines[i].strip()[1:].strip())
                i += 1
            blocks.append(RevisionBoxBlock(title=title, body=body))
            continue

        if stripped.startswith("# "):
            blocks.append(HeadingBlock(level=1, text=stripped[2:].strip()))
            i += 1
            continue

        if stripped.startswith("## "):
            blocks.append(HeadingBlock(level=2, text=stripped[3:].strip()))
            i += 1
            continue

        if stripped.startswith("### "):
            blocks.append(HeadingBlock(level=3, text=stripped[4:].strip()))
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                rows.append(row)
                i += 1
            rows = [row for index, row in enumerate(rows) if index != 1]
            blocks.append(TableBlock(rows=rows))
            continue

        if stripped.startswith("- "):
            items: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:].strip())
                i += 1
            blocks.append(BulletBlock(items=items))
            continue

        if stripped[:3].rstrip().endswith(".") and len(stripped) > 3 and stripped[0].isdigit():
            items: list[str] = []
            while i < len(lines):
                current = lines[i].strip()
                if current[:3].rstrip().endswith(".") and len(current) > 3 and current[0].isdigit():
                    items.append(current.split(".", 1)[1].strip())
                    i += 1
                else:
                    break
            blocks.append(NumberedBlock(items=items))
            continue

        para_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt:
                break
            if nxt.startswith(("#", ">", "-", "|", "```")):
                break
            if nxt[:3].rstrip().endswith(".") and len(nxt) > 3 and nxt[0].isdigit():
                break
            para_lines.append(nxt)
            i += 1
        blocks.append(ParagraphBlock(text=" ".join(para_lines)))

    return blocks


class PdfRenderer:
    def __init__(self) -> None:
        self.pages: list[Image.Image] = []
        self.page_number = 0
        self.image: Image.Image | None = None
        self.draw: ImageDraw.ImageDraw | None = None
        self.cursor_y = MARGIN_TOP
        self.new_page()

    def new_page(self) -> None:
        self.page_number += 1
        self.image = Image.new("RGB", (PAGE_W, PAGE_H), COLORS["bg"])
        self.draw = ImageDraw.Draw(self.image)
        self.cursor_y = MARGIN_TOP
        self.draw_header()
        self.draw_footer()
        self.pages.append(self.image)

    @property
    def canvas(self) -> ImageDraw.ImageDraw:
        assert self.draw is not None
        return self.draw

    def draw_header(self) -> None:
        self.canvas.text((MARGIN_X, 40), "Vyapar Sathi Revision Guide", fill=COLORS["muted"], font=FONT_SMALL)
        self.canvas.line((MARGIN_X, 68, PAGE_W - MARGIN_X, 68), fill=COLORS["rule"], width=2)

    def draw_footer(self) -> None:
        y = PAGE_H - 50
        self.canvas.line((MARGIN_X, y - 18, PAGE_W - MARGIN_X, y - 18), fill=COLORS["rule"], width=1)
        self.canvas.text((MARGIN_X, y), "Prepared as a full replacement study guide", fill=COLORS["muted"], font=FONT_SMALL)
        page_text = f"Page {self.page_number}"
        width = text_width(self.canvas, page_text, FONT_SMALL)
        self.canvas.text((PAGE_W - MARGIN_X - width, y), page_text, fill=COLORS["muted"], font=FONT_SMALL)

    def ensure_space(self, height: int) -> None:
        if self.cursor_y + height > PAGE_H - MARGIN_BOTTOM:
            self.new_page()

    def draw_wrapped_lines(
        self,
        lines: list[str],
        font: ImageFont.ImageFont,
        fill: str,
        x: int,
        max_width: int,
        line_gap: int = 6,
    ) -> int:
        start_y = self.cursor_y
        h = line_height(font)
        for paragraph in lines:
            wrapped = wrap_text(self.canvas, paragraph, font, max_width)
            for line in wrapped:
                self.canvas.text((x, self.cursor_y), line, font=font, fill=fill)
                self.cursor_y += h + line_gap
        return self.cursor_y - start_y

    def render_heading(self, block: HeadingBlock) -> None:
        if block.level == 1:
            font = FONT_TITLE
            fill = COLORS["title"]
            space_before = 12
            space_after = 20
        elif block.level == 2:
            font = FONT_H1
            fill = COLORS["h1"]
            space_before = 18
            space_after = 12
        else:
            font = FONT_H3
            fill = COLORS["h3"]
            space_before = 12
            space_after = 8

        wrapped = wrap_text(self.canvas, block.text, font, CONTENT_W)
        block_height = len(wrapped) * (line_height(font) + 6) + space_before + space_after
        self.ensure_space(block_height)
        self.cursor_y += space_before
        for line in wrapped:
            self.canvas.text((MARGIN_X, self.cursor_y), line, font=font, fill=fill)
            self.cursor_y += line_height(font) + 6
        if block.level in (1, 2):
            self.canvas.line((MARGIN_X, self.cursor_y + 2, PAGE_W - MARGIN_X, self.cursor_y + 2), fill=COLORS["rule"], width=2)
            self.cursor_y += 10
        self.cursor_y += space_after

    def render_paragraph(self, block: ParagraphBlock) -> None:
        wrapped = wrap_text(self.canvas, block.text, FONT_BODY, CONTENT_W)
        height = len(wrapped) * (line_height(FONT_BODY) + 6) + 8
        self.ensure_space(height)
        for line in wrapped:
            self.canvas.text((MARGIN_X, self.cursor_y), line, font=FONT_BODY, fill=COLORS["text"])
            self.cursor_y += line_height(FONT_BODY) + 6
        self.cursor_y += 8

    def render_bullets(self, block: BulletBlock) -> None:
        bullet_indent = 28
        usable_width = CONTENT_W - bullet_indent
        estimated = sum(max(1, len(wrap_text(self.canvas, item, FONT_BODY, usable_width))) for item in block.items)
        self.ensure_space(estimated * (line_height(FONT_BODY) + 6) + 16)
        for item in block.items:
            wrapped = wrap_text(self.canvas, item, FONT_BODY, usable_width)
            self.canvas.text((MARGIN_X, self.cursor_y), "•", font=FONT_BOLD, fill=COLORS["h3"])
            for index, line in enumerate(wrapped):
                x = MARGIN_X + bullet_indent
                y = self.cursor_y + index * (line_height(FONT_BODY) + 6)
                self.canvas.text((x, y), line, font=FONT_BODY, fill=COLORS["text"])
            self.cursor_y += len(wrapped) * (line_height(FONT_BODY) + 6) + 2
        self.cursor_y += 8

    def render_numbered(self, block: NumberedBlock) -> None:
        number_indent = 34
        usable_width = CONTENT_W - number_indent
        estimated = sum(max(1, len(wrap_text(self.canvas, item, FONT_BODY, usable_width))) for item in block.items)
        self.ensure_space(estimated * (line_height(FONT_BODY) + 6) + 16)
        for idx, item in enumerate(block.items, start=1):
            wrapped = wrap_text(self.canvas, item, FONT_BODY, usable_width)
            self.canvas.text((MARGIN_X, self.cursor_y), f"{idx}.", font=FONT_BOLD, fill=COLORS["h3"])
            for line_idx, line in enumerate(wrapped):
                self.canvas.text(
                    (MARGIN_X + number_indent, self.cursor_y + line_idx * (line_height(FONT_BODY) + 6)),
                    line,
                    font=FONT_BODY,
                    fill=COLORS["text"],
                )
            self.cursor_y += len(wrapped) * (line_height(FONT_BODY) + 6) + 2
        self.cursor_y += 8

    def render_revision_box(self, block: RevisionBoxBlock) -> None:
        title_lines = wrap_text(self.canvas, block.title, FONT_BOLD, CONTENT_W - 40)
        body_lines: list[str] = []
        for paragraph in block.body:
            body_lines.extend(wrap_text(self.canvas, paragraph, FONT_BODY, CONTENT_W - 40))
        total_lines = len(title_lines) + len(body_lines)
        box_height = total_lines * (line_height(FONT_BODY) + 6) + 34
        self.ensure_space(box_height + 12)
        top = self.cursor_y
        left = MARGIN_X
        right = PAGE_W - MARGIN_X
        bottom = top + box_height
        self.canvas.rounded_rectangle((left, top, right, bottom), radius=18, fill=COLORS["box_fill"], outline=COLORS["box_border"], width=3)
        self.cursor_y = top + 14
        for line in title_lines:
            self.canvas.text((left + 18, self.cursor_y), line, font=FONT_BOLD, fill=COLORS["h1"])
            self.cursor_y += line_height(FONT_BOLD) + 4
        self.cursor_y += 4
        for line in body_lines:
            self.canvas.text((left + 18, self.cursor_y), line, font=FONT_BODY, fill=COLORS["text"])
            self.cursor_y += line_height(FONT_BODY) + 4
        self.cursor_y = bottom + 14

    def table_column_widths(self, rows: list[list[str]]) -> list[int]:
        cols = max(len(row) for row in rows)
        widths = [CONTENT_W // cols] * cols
        return widths

    def split_table_if_needed(self, rows: list[list[str]]) -> list[list[list[str]]]:
        segments: list[list[list[str]]] = []
        header = rows[0]
        current = [header]
        self.ensure_space(0)
        for row in rows[1:]:
            current.append(row)
            if len(current) >= 9:
                segments.append(current)
                current = [header]
        if current:
            segments.append(current)
        return segments

    def render_table(self, block: TableBlock) -> None:
        segments = self.split_table_if_needed(block.rows)
        for segment in segments:
            widths = self.table_column_widths(segment)
            row_heights = []
            for row in segment:
                max_lines = 1
                for idx, cell in enumerate(row):
                    lines = wrap_text(self.canvas, cell, FONT_BODY, widths[idx] - 16)
                    max_lines = max(max_lines, len(lines))
                row_heights.append(max_lines * (line_height(FONT_BODY) + 4) + 16)
            block_height = sum(row_heights) + 8
            self.ensure_space(block_height + 10)
            x = MARGIN_X
            y = self.cursor_y
            for row_index, row in enumerate(segment):
                row_height = row_heights[row_index]
                fill = COLORS["table_head_fill"] if row_index == 0 else (COLORS["table_alt_fill"] if row_index % 2 == 0 else "#ffffff")
                self.canvas.rectangle((x, y, x + CONTENT_W, y + row_height), fill=fill, outline=COLORS["table_border"], width=2)
                cell_x = x
                for col_index, cell in enumerate(row):
                    if col_index > 0:
                        self.canvas.line((cell_x, y, cell_x, y + row_height), fill=COLORS["table_border"], width=2)
                    lines = wrap_text(self.canvas, cell, FONT_BOLD if row_index == 0 else FONT_BODY, widths[col_index] - 16)
                    ty = y + 8
                    for line in lines:
                        self.canvas.text((cell_x + 8, ty), line, font=FONT_BOLD if row_index == 0 else FONT_BODY, fill=COLORS["text"])
                        ty += line_height(FONT_BODY) + 4
                    cell_x += widths[col_index]
                y += row_height
            self.cursor_y = y + 12

    def render_code(self, block: CodeBlock) -> None:
        line_h = line_height(FONT_CODE, extra=2)
        wrapped_lines: list[str] = []
        for line in block.lines:
            wrapped_lines.extend(textwrap.wrap(line or " ", width=85) or [" "])
        block_height = len(wrapped_lines) * line_h + 24
        self.ensure_space(block_height + 10)
        left = MARGIN_X
        top = self.cursor_y
        right = PAGE_W - MARGIN_X
        bottom = top + block_height
        self.canvas.rounded_rectangle((left, top, right, bottom), radius=14, fill=COLORS["code_fill"], outline=COLORS["table_border"], width=2)
        self.cursor_y = top + 12
        for line in wrapped_lines:
            self.canvas.text((left + 14, self.cursor_y), line, font=FONT_CODE, fill=COLORS["text"])
            self.cursor_y += line_h
        self.cursor_y = bottom + 12

    def render(self, blocks: list[Block]) -> None:
        for block in blocks:
            if isinstance(block, HeadingBlock):
                self.render_heading(block)
            elif isinstance(block, ParagraphBlock):
                self.render_paragraph(block)
            elif isinstance(block, BulletBlock):
                self.render_bullets(block)
            elif isinstance(block, NumberedBlock):
                self.render_numbered(block)
            elif isinstance(block, RevisionBoxBlock):
                self.render_revision_box(block)
            elif isinstance(block, TableBlock):
                self.render_table(block)
            elif isinstance(block, CodeBlock):
                self.render_code(block)

    def save_pdf(self, output_path: Path) -> None:
        converted = [page.convert("RGB") for page in self.pages]
        first, rest = converted[0], converted[1:]
        first.save(output_path, "PDF", resolution=150.0, save_all=True, append_images=rest)


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    blocks = parse_markdown(markdown)
    renderer = PdfRenderer()
    renderer.render(blocks)
    renderer.save_pdf(OUTPUT)
    print(f"Created PDF: {OUTPUT}")


if __name__ == "__main__":
    main()
