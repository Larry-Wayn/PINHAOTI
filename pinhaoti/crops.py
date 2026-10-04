from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont, ImageOps


NUMBER_GUTTER = 0.065


def _closing_parenthesis_right(band: Image.Image, left: int, right: int, expected: int, min_height: float) -> int | None:
    """Locate the label's closing bracket, including scans printed as '9)'."""
    region = band.crop((left, 0, right, band.height))
    pixels = region.load()
    visited = set()
    candidates = []
    for y in range(region.height):
        for x in range(region.width):
            if not pixels[x, y] or (x, y) in visited:
                continue
            pending = [(x, y)]
            visited.add((x, y))
            points = []
            while pending:
                px, py = pending.pop()
                points.append((px, py))
                for nx in range(max(0, px - 1), min(region.width, px + 2)):
                    for ny in range(max(0, py - 1), min(region.height, py + 2)):
                        if pixels[nx, ny] and (nx, ny) not in visited:
                            visited.add((nx, ny))
                            pending.append((nx, ny))
            if len(points) < 4:
                continue
            x0, x1 = min(p[0] for p in points), max(p[0] for p in points)
            y0, y1 = min(p[1] for p in points), max(p[1] for p in points)
            glyph_width, glyph_height = x1 - x0 + 1, y1 - y0 + 1
            if glyph_height < min_height or glyph_width > glyph_height * 0.7:
                continue
            centres = []
            for low, high in ((0.1, 0.3), (0.4, 0.6), (0.7, 0.9)):
                xs = [px for px, py in points if y0 + low * (glyph_height - 1) <= py <= y0 + high * (glyph_height - 1)]
                if not xs:
                    break
                centres.append(sum(xs) / len(xs))
            # A ')' bends to the right at its middle; '(' and straight digits do not.
            if len(centres) == 3 and centres[1] > max(centres[0], centres[2]) + max(0.5, glyph_width * 0.12):
                candidates.append(left + x1 + 1)
    return min(candidates, key=lambda edge: abs(edge - expected)) if candidates else None


def _erase_number(image: Image.Image, marker_x: int, marker_y: int, page_width: int, estimated_width: int) -> float:
    """Erase only the old label and return its actual ink centre."""
    height = max(18, round(page_width * 0.023))
    top = max(0, marker_y - round(height * 0.75))
    bottom = min(image.height, marker_y + round(height * 0.75) + 1)
    left = max(0, marker_x - 5)
    expected_right = marker_x + estimated_width
    ink = ImageOps.invert(image.convert("L")).point(lambda p: 255 if p > 65 else 0)
    band = ink.crop((0, top, image.width, bottom))
    low = max(left + 1, expected_right - round(page_width * 0.013))
    high = min(image.width, expected_right + round(page_width * 0.013))
    gaps = []
    start = None
    for x in range(low, high):
        blank = band.crop((x, 0, x + 1, band.height)).getbbox() is None
        if blank and start is None:
            start = x
        elif not blank and start is not None:
            if x - start >= 2:
                gaps.append((start, x))
            start = None
    if start is not None and high - start >= 2:
        gaps.append((start, high))
    right = min(image.width, expected_right)
    if gaps:
        start, end = min(gaps, key=lambda gap: max(gap[0] - expected_right, expected_right - gap[1], 0))
        right = (start + end) // 2
    bracket_right = _closing_parenthesis_right(
        band, left, min(image.width, expected_right + round(page_width * 0.022)),
        expected_right, max(6, height * 0.35),
    )
    if bracket_right is not None:
        right = min(image.width, bracket_right + 1)
    box = band.crop((left, 0, right, band.height)).getbbox()
    centre = top + (box[1] + box[3]) / 2 if box else marker_y
    ImageDraw.Draw(image).rectangle((left, top, right - 1, bottom - 1), fill="white")
    return centre


def _align_fragments(fragments: list[Image.Image], number: int, marker_y: float) -> list[Image.Image]:
    """Reserve one fixed number column, preserving the source layout beside it."""
    if not fragments:
        return []
    width = fragments[0].width
    fragments = [
        image if image.width == width else image.resize(
            (width, max(1, round(image.height * width / image.width))), Image.Resampling.LANCZOS,
        )
        for image in fragments
    ]
    content_left = width
    for image in fragments:
        ink = ImageOps.invert(image.convert("L")).point(lambda p: 255 if p > 65 else 0)
        threshold = max(3, round(image.height * 0.002))
        for x in range(min(content_left, image.width)):
            if ink.crop((x, 0, x + 1, image.height)).histogram()[255] >= threshold:
                content_left = min(content_left, max(0, x - 4))
                break
    content_left = min(content_left, width - 1)
    gutter = round(width * NUMBER_GUTTER)
    scale = min(1.0, (width - gutter) / (width - content_left))
    font_size = max(18, round(width * 0.024))
    font_path = Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf")
    font = ImageFont.truetype(str(font_path), font_size) if font_path.exists() else ImageFont.load_default()
    label = f"({number})"
    bounds = font.getbbox(label)
    label_top = round(marker_y * scale - (bounds[3] - bounds[1]) / 2)
    padding = max(0, 2 - label_top)
    result = []
    for position, image in enumerate(fragments):
        content = image.crop((content_left, 0, image.width, image.height))
        if scale < 1:
            content = content.resize((round(content.width * scale), max(1, round(content.height * scale))), Image.Resampling.LANCZOS)
        top = padding if position == 0 else 0
        height = content.height + top
        if position == 0:
            height = max(height, padding + label_top + bounds[3] - bounds[1] + 2)
        canvas = Image.new("RGB", (width, height), "white")
        canvas.paste(content, (gutter, top))
        if position == 0:
            right = gutter - round(width * 0.012)
            ImageDraw.Draw(canvas).text((right - bounds[2], padding + label_top - bounds[1]), label, fill="black", font=font)
        result.append(canvas)
    return result


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
    label_y = 0
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
            else:
                patch_width = int(page_width * (0.034 if number < 10 else 0.050))
            label_y = _erase_number(crop, marker_x, marker_y, page_width, patch_width)
        trimmed = trim_ink(crop)
        if trimmed is not None:
            fragments.append(trimmed)
    return _align_fragments(fragments, display_number, label_y)
