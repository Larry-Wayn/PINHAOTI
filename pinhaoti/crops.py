from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont


def trim_ink(image: Image.Image) -> Image.Image | None:
    gray = image.convert("L")
    width, height = gray.size
    threshold = max(8, int(width * 0.008))
    pixels = gray.load()
    significant = []
    for y in range(height):
        dark = sum(pixels[x, y] < 190 for x in range(width))
        if dark >= threshold:
            significant.append(y)
    if not significant:
        return None
    return image.crop((0, 0, width, min(height, significant[-1] + 12)))


def render_question(root: Path, index: dict, year: int, number: int, display_number: int) -> list[Image.Image]:
    paper = index["years"][str(year)]
    source = root / "sources" / paper["pdf"]
    if not source.is_file():
        raise FileNotFoundError(f"找不到 {year} 年真题 PDF：{source}")
    question = paper["questions"][str(number)]
    document = pdfium.PdfDocument(str(source))
    fragments = []
    for segment in question["segments"]:
        page_image = document[segment["page"]].render(scale=2.2).to_pil().convert("RGB")
        page_width, page_height = page_image.size
        x0, x1 = int(page_width * 0.02), int(page_width * 0.98)
        y0, y1 = int(page_height * segment["top"]), int(page_height * segment["bottom"])
        if y1 <= y0:
            continue
        crop = page_image.crop((x0, y0, x1, y1))
        if segment.get("masks"):
            draw = ImageDraw.Draw(crop)
            for mask in segment["masks"]:
                draw.rectangle((
                    int(page_width * mask["x0"]) - x0,
                    int(page_height * mask["y0"]) - y0,
                    int(page_width * mask["x1"]) - x0,
                    int(page_height * mask["y1"]) - y0,
                ), fill="white")
        if segment["left"] is not None:
            marker_x = int(page_width * segment["left"]) - x0
            marker_y = int(page_height * segment.get("marker_y", segment["top"] + 0.01)) - y0
            if year == 2021 and number >= 10:
                patch_width = int(page_width * (0.032 if number <= 16 else 0.043))
                number_x = int(page_width * 0.035) - x0
            else:
                patch_width = int(page_width * (0.034 if number < 10 else 0.050))
                number_x = marker_x
            font_size = max(18, int(page_width * 0.023))
            font_path = Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf")
            font = ImageFont.truetype(str(font_path), font_size) if font_path.exists() else ImageFont.load_default()
            draw = ImageDraw.Draw(crop)
            draw.rectangle((max(0, marker_x - 5), max(0, marker_y - font_size), marker_x + patch_width, marker_y + font_size // 2), fill="white")
            draw.text((number_x, max(0, marker_y - font_size)), f"({display_number})", fill="black", font=font)
        trimmed = trim_ink(crop)
        if trimmed is not None:
            fragments.append(trimmed)
    return fragments
