"""Index the eight mathematics I practice papers in the supplied 2027 PDF.

Usage: python build_zhangyu_index.py --source /path/to/paper.pdf
The existing real-exam index is preserved. The source PDF stays unmodified.
"""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil

import numpy as np
import pypdfium2 as pdfium

from build_index import Marker, build_regions, choose_start, select_sequence


COLLECTION_KEY = "zhangyu_27"
TARGET_NAME = "张宇八套卷2027数学一.pdf"
# PDFium cannot extract these six printed labels. Coordinates were checked on
# the rendered source pages: (zero-based page, left, top, right, bottom).
MANUAL_LABELS = {
    (1, 11): (5, .112, .450, .139, .468),
    (2, 15): (13, .112, .285, .141, .303),
    (4, 11): (29, .134, .134, .164, .150),
    (5, 11): (37, .134, .714, .164, .733),
    (6, 14): (45, .157, .348, .188, .365),
    (7, 11): (53, .148, .267, .179, .285),
}

# Visual checks of the rendered source pages: keep preceding options/section
# instructions out of the crop, and retain the tall matrix above set 3 Q15.
START_OVERRIDES = {
    (1, 10): .860,
    (2, 17): .476,
    (3, 15): .251,
    (4, 7): .395,
    (5, 10): .493,
    (6, 17): .557,
    (7, 17): .685,
    (8, 15): .123,
}


def _text_markers(document: pdfium.PdfDocument, set_number: int):
    markers = []
    boxes = {}
    headings: dict[int, list[float]] = defaultdict(list)
    first = 3 + (set_number - 1) * 8
    for page_number in range(first, first + 7):
        page = document[page_number]
        textpage = page.get_textpage()
        text = textpage.get_text_range()
        offset = 0
        for line in text.splitlines(keepends=True):
            if "填空题" in line or "解答题" in line or "选择题" in line:
                leading = len(line) - len(line.lstrip())
                box = textpage.get_charbox(offset + leading)
                headings[page_number].append(1 - box[3] / page.get_height())
            match = re.match(r"^\s*(\d{1,2})[.．]", line)
            if match:
                number = int(match.group(1))
                if 1 <= number <= 22:
                    first_char = offset + match.start(1)
                    last_char = offset + match.end()
                    glyphs = [textpage.get_charbox(i) for i in range(first_char, last_char)]
                    left = min(box[0] for box in glyphs) / page.get_width()
                    top = 1 - max(box[3] for box in glyphs) / page.get_height()
                    right = max(box[2] for box in glyphs) / page.get_width()
                    bottom = 1 - min(box[1] for box in glyphs) / page.get_height()
                    if .06 < top < .94 and .07 < left < .22:
                        markers.append(Marker(number, page_number, top, left))
                        boxes[(page_number, number)] = [left, top, right, bottom]
            offset += len(line)
    for (manual_set, number), (page, left, top, right, bottom) in MANUAL_LABELS.items():
        if manual_set == set_number:
            markers.append(Marker(number, page, top, left))
            boxes[(page, number)] = [left, top, right, bottom]
    markers = select_sequence(markers, expected_count=22)
    return markers, boxes, headings


def _starts(document: pdfium.PdfDocument, markers: list[Marker], headings: dict[int, list[float]]) -> dict[int, float]:
    rows = {}
    limits = {}
    for page_number in {marker.page for marker in markers}:
        image = document[page_number].render(scale=2.2).to_pil().convert("L")
        pixels = np.asarray(image)
        width = pixels.shape[1]
        rows[page_number] = (pixels[:, int(width * .07):int(width * .93)] < 190).sum(axis=1)
        limits[page_number] = max(10, int(width * .008))
    starts = {}
    for position, marker in enumerate(markers):
        lower = .065
        if position and markers[position - 1].page == marker.page:
            lower = max(lower, markers[position - 1].top + .012)
        earlier_headings = [value for value in headings.get(marker.page, []) if value < marker.top]
        if earlier_headings:
            lower = max(lower, max(earlier_headings) + .006)
        starts[marker.number] = choose_start(rows[marker.page], marker.top, lower, limits[marker.page])
    return starts


def _has_question_ink(document: pdfium.PdfDocument, segment: dict) -> bool:
    image = document[segment["page"]].render(scale=2.2).to_pil().convert("L")
    pixels = np.asarray(image)
    height, width = pixels.shape
    region = pixels[
        int(height * segment["top"]):int(height * segment["bottom"]),
        int(width * .08):int(width * .91),
    ]
    if region.size == 0:
        return False
    return bool(np.any((region < 190).sum(axis=1) > max(8, int(width * .008))))


def build_zhangyu_index(source: Path, output: Path) -> None:
    document = pdfium.PdfDocument(str(source))
    if len(document) != 66:
        raise ValueError(f"预期 66 页的张宇八套卷试题分册，实际为 {len(document)} 页")
    index = json.loads(output.read_text())
    papers = {}
    for set_number in range(1, 9):
        markers, boxes, headings = _text_markers(document, set_number)
        starts = _starts(document, markers, headings)
        for (paper_number, question_number), top in START_OVERRIDES.items():
            if set_number == paper_number:
                starts[question_number] = top
        first = 3 + (set_number - 1) * 8
        regions = build_regions(markers, first + 7, headings, continuation_top=.073, starts=starts)
        questions = {}
        for number in range(1, 23):
            segments = [
                segment for position, segment in enumerate(regions[number])
                if position == 0 or _has_question_ink(document, segment)
            ]
            for segment in segments:
                if segment["bottom"] == .96:
                    segment["bottom"] = .945
            marker = markers[number - 1]
            segments[0]["label_box"] = [round(value, 5) for value in boxes[(marker.page, number)]]
            kind = "choice" if number <= 10 else "fill" if number <= 16 else "solution"
            questions[str(number)] = {"type": kind, "segments": segments}
        papers[str(set_number)] = {"questions": questions}
    destination = output.parent.parent / "sources" / TARGET_NAME
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    index.setdefault("collections", {})[COLLECTION_KEY] = {
        "title": "张宇八套卷",
        "pdf": TARGET_NAME,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "page_count": len(document),
        "sets": papers,
    }
    output.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/index.json"))
    args = parser.parse_args()
    build_zhangyu_index(args.source, args.output)
