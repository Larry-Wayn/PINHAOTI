from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Selection:
    year: int
    number: int
    kind: str
    output_number: int


def parse_selections(text: str, index: dict) -> list[Selection]:
    entries = [part.strip() for part in re.split(r"[\n,，;；]+", text) if part.strip()]
    if not entries:
        raise ValueError("请输入至少一道题，格式如 2009年数学一第9题")
    selected: list[tuple[int, int, str]] = []
    seen: set[tuple[int, int]] = set()
    for position, entry in enumerate(entries, start=1):
        compact = re.sub(r"\s+", "", entry)
        match = re.fullmatch(r"(20\d{2})[-—_:](\d{1,2})", compact)
        if not match:
            match = re.fullmatch(r"(20\d{2})年?(?:考研)?(?:数学[（(]?一[）)]?|数一)?第?(\d{1,2})题?", compact)
        if not match:
            raise ValueError(f"第{position}项无法识别：{entry}。请写成 2009年数学一第9题 或 2009-9")
        year, number = int(match.group(1)), int(match.group(2))
        paper = index["years"].get(str(year))
        if paper is None or str(number) not in paper["questions"]:
            raise ValueError(f"第{position}项没有对应的数学一真题：{entry}")
        key = (year, number)
        if key not in seen:
            seen.add(key)
            selected.append((year, number, paper["questions"][str(number)]["type"]))
    kind_order = {"choice": 0, "fill": 1, "solution": 2}
    selected.sort(key=lambda item: kind_order[item[2]])
    return [Selection(year, number, kind, output_number) for output_number, (year, number, kind) in enumerate(selected, start=1)]
