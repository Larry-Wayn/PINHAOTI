from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import json
import re
import shutil

import numpy as np
import pypdfium2 as pdfium
from pypdf import PdfReader


@dataclass(frozen=True)
class Marker:
    number: int
    page: int
    top: float
    left: float


def select_sequence(candidates: list[Marker], expected_count: int = 23) -> list[Marker]:
    selected = []
    next_number = 1
    for marker in sorted(candidates, key=lambda item: (item.page, item.top)):
        if marker.number == next_number:
            selected.append(marker)
            next_number += 1
    if len(selected) != expected_count:
        raise ValueError(f"Expected {expected_count} questions, found {len(selected)}; next missing number is {next_number}")
    return selected


def question_number(text: str) -> int | None:
    match = re.match(r"^\s*[（(]?\s*(\d{1,2})\s*[）)]", text)
    if not match:
        return None
    number = int(match.group(1))
    return number if 1 <= number <= 23 else None


def choose_start(row_counts: np.ndarray, marker_y: float, lower_y: float, blank_threshold: int) -> float:
    height = len(row_counts)
    low = max(0, int(max(lower_y, marker_y - 0.08) * height))
    high = min(height, int((marker_y - 0.004) * height))
    if low >= high:
        return round(max(0.005, marker_y - 0.012), 3)
    blank = row_counts[low:high] < blank_threshold
    runs = []
    begin = None
    for offset, is_blank in enumerate(blank):
        if is_blank and begin is None:
            begin = offset
        elif not is_blank and begin is not None:
            runs.append((begin, offset))
            begin = None
    if begin is not None:
        runs.append((begin, len(blank)))
    runs = [(start, end) for start, end in runs if end - start >= 4]
    if not runs:
        return round(max(lower_y, marker_y - 0.012), 3)
    longest = max(end - start for start, end in runs)
    minimum_length = min(longest, max(7, int(longest * 0.5)))
    eligible = [(start, end) for start, end in runs if end - start >= minimum_length]
    _, end = max(eligible, key=lambda run: run[1])
    return round(max(lower_y, (low + end - 2) / height), 3)


def refine_starts(source: Path, markers: list[Marker], headings: dict[int, list[float]], old_layout: bool) -> dict[int, float]:
    document = pdfium.PdfDocument(str(source))
    rows = {}
    thresholds = {}
    for page_number in range(len(document)):
        image = document[page_number].render(scale=2.2).to_pil().convert("L")
        pixels = np.asarray(image)
        width = pixels.shape[1]
        rows[page_number] = (pixels[:, int(width * 0.03):int(width * 0.97)] < 190).sum(axis=1)
        thresholds[page_number] = max(10, int(width * 0.008))
    starts = {}
    for position, marker in enumerate(markers):
        previous = markers[position - 1] if position else None
        lower = 0.05 if old_layout else 0.005
        if previous and previous.page == marker.page:
            lower = max(lower, previous.top + 0.012)
        earlier_headings = [y for y in headings.get(marker.page, []) if y < marker.top]
        if earlier_headings:
            lower = max(lower, max(earlier_headings) + 0.005)
        starts[marker.number] = choose_start(rows[marker.page], marker.top, lower, thresholds[marker.page])
    return starts


def build_regions(markers: list[Marker], page_count: int, headings: dict[int, list[float]], continuation_top: float = 0.04, starts: dict[int, float] | None = None) -> dict[int, list[dict]]:
    ordered = sorted(markers, key=lambda marker: (marker.page, marker.top))
    regions: dict[int, list[dict]] = {}
    for position, marker in enumerate(ordered):
        following = ordered[position + 1] if position + 1 < len(ordered) else None
        last_page = following.page if following else page_count - 1
        segments = []
        for page in range(marker.page, last_page + 1):
            top = starts.get(marker.number, max(0.01, marker.top - 0.01)) if starts and page == marker.page else max(0.01, marker.top - 0.01) if page == marker.page else continuation_top
            bottom = (starts.get(following.number, following.top - 0.01) - 0.002 if starts else following.top - 0.01) if following and page == following.page else 0.96
            heading_positions = [y for y in headings.get(page, []) if top < y < bottom]
            if heading_positions:
                bottom = min(heading_positions) - 0.01
            if bottom > top + 0.005:
                segments.append({"page": page, "top": round(top, 3), "bottom": round(bottom, 3), "left": marker.left if page == marker.page else None, "marker_y": marker.top if page == marker.page else None})
        regions[marker.number] = segments
    return regions


def read_ocr(path: Path) -> tuple[dict[str, list[Marker]], dict[str, dict[str, tuple[int, float]]]]:
    candidates: dict[str, list[Marker]] = defaultdict(list)
    headings: dict[str, dict[str, tuple[int, float]]] = defaultdict(dict)
    year = ""
    page = 0
    for line in path.read_text().splitlines():
        if line.startswith("FILE "):
            filename = line.removeprefix("FILE ").strip()
            year = filename[:4]
            page = int(filename[5:7]) - 1
            continue
        parts = line.split(" ", 2)
        if len(parts) != 3:
            continue
        try:
            strip_x, strip_y = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        text = parts[2]
        y = round(strip_y * 0.96, 3)
        x = round(0.025 + strip_x * 0.205, 3)
        number = question_number(text)
        if number and strip_x < 0.6:
            candidates[year].append(Marker(number, page, y, x))
        if "填空题" in text:
            headings[year]["fill"] = (page, y)
        if "解答题" in text:
            headings[year]["solution"] = (page, y)
        if "选择题" in text:
            headings[year]["choice"] = (page, y)
    candidates["2007"].append(Marker(11, 1, 0.304, 0.045))
    candidates["2012"].append(Marker(10, 1, 0.167, 0.030))
    # Vision reads the left-edge 13, 14, and 15 in the 2021 scan as I3, .4, and .5.
    candidates["2021"].extend((
        Marker(13, 1, 0.785, 0.090),
        Marker(14, 1, 0.808, 0.091),
        Marker(15, 1, 0.872, 0.092),
    ))
    return candidates, headings


def build_index(source_folder: Path, ocr_path: Path, output: Path) -> None:
    candidates, headings = read_ocr(ocr_path)
    source_copy = output.parent.parent / "sources"
    source_copy.mkdir(parents=True, exist_ok=True)
    years = {}
    for year_number in range(2007, 2022):
        year = str(year_number)
        matches = list(source_folder.glob(f"{year}*.pdf"))
        if len(matches) != 1:
            raise ValueError(f"{year}: expected one PDF, found {len(matches)}")
        source = matches[0]
        question_count = 22 if year_number == 2021 else 23
        markers = select_sequence(candidates[year], expected_count=question_count)
        section_starts = {}
        heading_by_page: dict[int, list[float]] = defaultdict(list)
        for kind in ("fill", "solution"):
            if kind not in headings[year]:
                raise ValueError(f"{year}: missing {kind} heading")
            heading_page, heading_y = headings[year][kind]
            heading_by_page[heading_page].append(heading_y)
            later = [marker.number for marker in markers if (marker.page, marker.top) > (heading_page, heading_y)]
            if not later:
                raise ValueError(f"{year}: no question after {kind} heading")
            section_starts[kind] = min(later)
        if "choice" in headings[year]:
            heading_page, heading_y = headings[year]["choice"]
            heading_by_page[heading_page].append(heading_y)
        page_count = len(PdfReader(source).pages)
        starts = refine_starts(source, markers, heading_by_page, old_layout=year_number <= 2009)
        # The tall matrices and integral in these scans rise above the printed question number.
        if year == "2012":
            starts[6] = 0.716
            starts[10] = 0.148
        if year == "2015":
            starts[1] = 0.155
            starts[2] = 0.248
        if year == "2021":
            # The upper limit of the integral rises above the printed 11.
            starts[11] = 0.686
        regions = build_regions(markers, page_count, heading_by_page, continuation_top=0.05 if year_number <= 2009 else 0.01, starts=starts)
        if year == "2015":
            # The right-hand figure for Q1 extends below the start of Q2.
            regions[1][0]["bottom"] = 0.308
            regions[1][0]["masks"] = [{"x0": 0.02, "y0": starts[2], "x1": 0.70, "y1": 0.308}]
            regions[2][0]["masks"] = [{"x0": 0.68, "y0": starts[2], "x1": 0.98, "y1": 0.308}]
        if year == "2021":
            regions[16][1]["top"] = 0.067
        for false_continuation in {"2008": (11,), "2011": (10,), "2020": (12,), "2021": (6, 19)}.get(year, ()):
            regions[false_continuation] = regions[false_continuation][:1]
        target = source_copy / source.name
        if target != source:
            shutil.copy2(source, target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        questions = {}
        for number in range(1, question_count + 1):
            kind = "choice" if number < section_starts["fill"] else "fill" if number < section_starts["solution"] else "solution"
            questions[str(number)] = {"type": kind, "segments": regions[number]}
        years[year] = {
            "pdf": source.name,
            "sha256": digest,
            "page_count": page_count,
            "fill_start": section_starts["fill"],
            "solution_start": section_starts["solution"],
            "questions": questions,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"version": 1, "years": years}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-folder", type=Path, required=True)
    parser.add_argument("--ocr", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_index(args.source_folder, args.ocr, args.output)
