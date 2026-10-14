from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Selection:
    year: int | None
    number: int
    kind: str
    output_number: int
    set_number: int | None = None

    @property
    def origin(self) -> str:
        if self.set_number is not None:
            return f"张宇八套卷第 {self.set_number} 套第 {self.number} 题"
        return f"{self.year} 年数学一第 {self.number} 题"


def parse_selections(text: str, index: dict, source: str = "exam") -> list[Selection]:
    if source not in ("exam", "zhangyu"):
        raise ValueError("请选择历年真题或张宇八套卷题库")
    entries = [part.strip() for part in re.split(r"[\n,，;；]+", text) if part.strip()]
    if not entries:
        example = "2009年数学一第9题" if source == "exam" else "张宇八套卷第1套第9题"
        raise ValueError(f"请输入至少一道题，格式如 {example}")
    selected: list[tuple[int | None, int | None, int, str]] = []
    seen: set[tuple[int | None, int | None, int]] = set()
    for position, entry in enumerate(entries, start=1):
        compact = re.sub(r"\s+", "", entry)
        if source == "exam":
            match = re.fullmatch(r"(20\d{2})[-—_:](\d{1,2})", compact)
            if not match:
                match = re.fullmatch(r"(20\d{2})年?(?:考研)?(?:数学[（(]?一[）)]?|数一)?第?(\d{1,2})题?", compact)
            if not match:
                raise ValueError(f"第{position}项无法识别：{entry}。请写成 2009年数学一第9题 或 2009-9")
            year, number = int(match.group(1)), int(match.group(2))
            set_number = None
            paper = index["years"].get(str(year))
            if paper is None or str(number) not in paper["questions"]:
                raise ValueError(f"第{position}项没有对应的数学一真题：{entry}")
        else:
            match = re.fullmatch(r"ZY([1-8])[-—_:](\d{1,2})", compact, flags=re.IGNORECASE)
            if not match:
                match = re.fullmatch(r"张宇(?:八|8)套卷第?([1-8一二三四五六七八])(?:套|卷)?第?(\d{1,2})题?", compact)
            if not match:
                raise ValueError(f"第{position}项无法识别：{entry}。请写成 张宇八套卷第1套第9题 或 ZY1-9")
            set_text = match.group(1)
            set_number = "一二三四五六七八".index(set_text) + 1 if set_text in "一二三四五六七八" else int(set_text)
            number = int(match.group(2))
            year = None
            paper = index.get("collections", {}).get("zhangyu_27", {}).get("sets", {}).get(str(set_number))
            if paper is None or str(number) not in paper["questions"]:
                raise ValueError(f"第{position}项没有对应的张宇八套卷题目：{entry}")
        key = (year, set_number, number)
        if key not in seen:
            seen.add(key)
            selected.append((year, set_number, number, paper["questions"][str(number)]["type"]))
    kind_order = {"choice": 0, "fill": 1, "solution": 2}
    selected.sort(key=lambda item: kind_order[item[3]])
    return [
        Selection(year, number, kind, output_number, set_number)
        for output_number, (year, set_number, number, kind) in enumerate(selected, start=1)
    ]
