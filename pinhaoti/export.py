from io import BytesIO
from pathlib import Path

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .crops import render_question


FONT_NAME = "PinhaotiChinese"
FONT_PATH = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
SPACE_HEIGHTS = {"compact": 130, "standard": 220, "spacious": 320}
KIND_LABELS = {"choice": "选择题", "fill": "填空题", "solution": "解答题"}


def _register_font():
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def export_pdf(root: Path, index: dict, selections: list, answer_space: str) -> bytes:
    if answer_space not in SPACE_HEIGHTS:
        raise ValueError("解答题留白只能选紧凑、标准或宽松")
    if not selections:
        raise ValueError("请至少选择一道题")
    _register_font()
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=A4)
    pdf.setTitle("考研数学拼好题")
    page_width, page_height = A4
    margin = 44
    bottom = 44
    content_width = page_width - 2 * margin

    def next_page():
        nonlocal y
        pdf.showPage()
        y = page_height - margin

    y = page_height - 65
    pdf.setFont(FONT_NAME, 18)
    pdf.drawCentredString(page_width / 2, y, "考研数学拼好题")
    y -= 32
    counts = {kind: sum(item.kind == kind for item in selections) for kind in KIND_LABELS}
    summary = f"共 {len(selections)} 题  ·  选择 {counts['choice']} 题  ·  填空 {counts['fill']} 题  ·  解答 {counts['solution']} 题"
    pdf.setFont(FONT_NAME, 10)
    pdf.drawCentredString(page_width / 2, y, summary)
    y -= 29
    pdf.drawString(margin, y, "姓名：________________    日期：________________")
    y -= 29
    pdf.setStrokeColorRGB(0.25, 0.25, 0.25)
    pdf.line(margin, y, page_width - margin, y)
    y -= 27

    for section_number, kind in enumerate(KIND_LABELS, start=1):
        group = [item for item in selections if item.kind == kind]
        if not group:
            continue
        first = group[0]
        first_fragments = render_question(root, index, first.year, first.number, first.output_number)
        if not first_fragments:
            raise ValueError(f"{first.year} 年第 {first.number} 题无法从源 PDF 取得题干")
        first_images_height = sum(image.height * content_width / image.width for image in first_fragments)
        first_blank_height = SPACE_HEIGHTS[answer_space] if kind == "solution" else 28 if kind == "fill" else 12
        first_required = first_images_height + 6 * len(first_fragments) + first_blank_height + 14
        if y < bottom + 72 or (first_required < page_height - 130 - bottom and y - 26 - first_required < bottom):
            next_page()
        pdf.setFont(FONT_NAME, 13)
        section_title = f"{'一二三'[section_number - 1]}、{KIND_LABELS[kind]}（共 {len(group)} 题）"
        pdf.drawString(margin, y, section_title)
        y -= 26
        for item in group:
            fragments = first_fragments if item is first else render_question(root, index, item.year, item.number, item.output_number)
            if not fragments:
                raise ValueError(f"{item.year} 年第 {item.number} 题无法从源 PDF 取得题干")
            scaled_heights = [image.height * content_width / image.width for image in fragments]
            blank_height = SPACE_HEIGHTS[answer_space] if kind == "solution" else 28 if kind == "fill" else 12
            required = sum(scaled_heights) + 6 * len(fragments) + blank_height + 14
            full_capacity = page_height - 100 - bottom
            if required <= full_capacity and y - required < bottom:
                next_page()
            for image in fragments:
                width_px, height_px = image.size
                scale = content_width / width_px
                offset = 0
                while offset < height_px:
                    available = y - bottom - 8
                    if available < 40:
                        next_page()
                        available = y - bottom - 8
                    slice_pixels = min(height_px - offset, max(1, int(available / scale)))
                    part = image.crop((0, offset, width_px, offset + slice_pixels))
                    draw_height = slice_pixels * scale
                    pdf.drawImage(ImageReader(part), margin, y - draw_height, width=content_width, height=draw_height, mask="auto")
                    y -= draw_height
                    offset += slice_pixels
                    if offset < height_px:
                        next_page()
                y -= 6
            if kind == "solution":
                if y - blank_height < bottom:
                    next_page()
                y -= blank_height
            else:
                y -= blank_height
            y -= 14

    next_page()
    pdf.setFont(FONT_NAME, 14)
    pdf.drawString(margin, y, "题目出处")
    y -= 27
    pdf.setFont(FONT_NAME, 10)
    pdf.drawString(margin, y, "按本卷题号列出原试卷位置，便于复盘。")
    y -= 26
    for item in selections:
        if y < bottom + 18:
            next_page()
        pdf.setFont(FONT_NAME, 10)
        pdf.drawString(margin, y, f"第 {item.output_number} 题  ·  {item.year} 年数学一第 {item.number} 题  ·  {KIND_LABELS[item.kind]}")
        y -= 21
    pdf.save()
    return stream.getvalue()
