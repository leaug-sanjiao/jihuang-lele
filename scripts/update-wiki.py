"""Read the Wiki's public tables into a local candidate snapshot (no images or prose)."""

import argparse
import json
import re
import sys
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
WIKI = "https://wiki.biligame.com/jikunhuangye/"
TABLES = {
    "build": ("制造图鉴", ["制造图片", "制造名称", "类别", "制造配方"]),
    "gear": ("装备图鉴", ["装备图片", "装备名称", "类别", "装备配方"]),
    "food": ("食物图鉴", ["食物图片", "名称", "类别", "食物来源&配方", "烹饪需求",
                      "烹饪限制", "烹饪时间(秒)", "腐烂天数"]),
    "items": ("道具图鉴", ["道具图片", "道具名称", "类别", "获取方式", "特殊用途"]),
}
NAME_PATTERN = r"[\u3400-\u9fff·]+"
KNOWN_EXCEPTIONS = {
    "失败料理": "Wiki 将这项列为烹饪失败产物，保留原表示例。",
    "夏日冰沙": "Wiki 示例共 5 份材料，投料方式待核实。",
    "清爽蔬菜汁": "Wiki 示例共 5 份材料，投料方式待核实。",
    "酿茄子": "Wiki 的烹饪限制栏填了数字 40，条件待核实。",
    "素食堡": "Wiki 示例含食材度数，不能当成背包里的具体食材。",
    "蔬菜鸡尾酒": "Wiki 示例含番茄或芦笋等替代写法，保留原表作查询。",
}


def clean(value):
    return " ".join(unicodedata.normalize("NFKC", value).split())


def columns(row):
    return [clean(cell.get_text(" ", strip=True))
            for cell in row.find_all(["th", "td"], recursive=False)]


def read_table(title, expected, html_dir):
    url = WIKI + quote(title)
    try:
        if html_dir:
            html = (html_dir / f"{title}.html").read_bytes()
        else:
            with urlopen(url, timeout=20) as response:
                html = response.read()
        soup = BeautifulSoup(html, "html.parser")
    except OSError as error:
        raise ValueError(f"{title} 读取失败：{error}") from error

    table = soup.select_one(".mw-parser-output table.CardSelect")
    if not table:
        raise ValueError(f"{title} 未找到可识别的图鉴表格")
    header_row, *body_rows = table.select("tr")
    header, rows = columns(header_row), [columns(row) for row in body_rows]
    if header[:len(expected)] != expected or not rows:
        raise ValueError(f"{title} 表头改变或没有数据，请先检查 Wiki")

    revision_link = soup.select_one(".printfooter a[href*='oldid=']")
    date = re.search(r"\b\d{4}-\d{2}-\d{2}\b", soup.select_one(".pc-serve-msg").get_text())
    if not revision_link or not date:
        raise ValueError(f"{title} 未能读取修订号或页面更新时间")
    revision = int(parse_qs(urlsplit(revision_link["href"]).query)["oldid"][0])
    source = {
        "title": title,
        "url": url,
        "revision": revision,
        "updated": date.group(),
        "revisionUrl": f"{WIKI}index.php?title={quote(title)}&oldid={revision}",
    }
    required_columns = 11 if title == "食物图鉴" else len(expected)
    if any(not required_columns <= len(row) <= len(header) for row in rows):
        raise ValueError(f"{title} 存在列数异常的记录，请先检查 Wiki")
    if title == "食物图鉴":
        stat_icons = [image.get("alt") for image in header_row.select("img")]
        if stat_icons != ["生命值.png", "饥饿值.png", "理智值.png"]:
            raise ValueError(f"{title} 的属性列发生变化，请先检查 Wiki")
    return source, rows


def parse_ingredients(raw):
    ingredients = {}
    terms = re.split(r"[+、,]", raw.lstrip("="))
    for term in terms:
        condition = re.fullmatch(rf"\s*({NAME_PATTERN})\s*[*×]\s*([1-9]\d*)\s*", term)
        if not condition or condition[1].endswith("度"):
            return None
        item, amount = condition.groups()
        ingredients[item] = ingredients.get(item, 0) + int(amount)
    return [{"item": item, "quantity": amount} for item, amount in ingredients.items()]


def material_fact(key, row):
    _, name, category, origin, *rest = row
    if key == "food" and (category == "料理" or "*" in origin or name == "食人花肉"):
        return None
    if key not in ("items", "food"):
        return None
    fact = {"source": key}
    if origin not in ("", "/"):
        fact["origin"] = origin.replace(",", "，")
    use = rest[0] if key == "items" else ""
    # 仅提取已有图鉴中的事实，保留概率、地点和条件。
    if key == "items" and use in ("", "/"):
        use = {"木头": "可用作燃料", "树枝": "部分料理可用作填料",
               "元素精华": "家园建筑升级材料"}.get(name, "")
    if use not in ("", "/"):
        fact["use"] = use.replace(",", "，")
    return fact if len(fact) > 1 else None


def build_snapshot(html_dir):
    sources = {}
    recipes = []
    gaps = {}
    material_facts = {}
    for key, (title, header) in TABLES.items():
        sources[key], rows = read_table(title, header, html_dir)
        sources[key]["rowCount"] = len(rows)
        for row in rows:
            _, name, category, raw, *_ = row
            fact = material_fact(key, row)
            if fact:
                material_facts[name] = fact
            if key == "items":
                if re.search(r"合成获得|(?:使用|用).{1,20}合成", raw):
                    gaps[name] = {"source": key}
                continue
            if key == "food" and category != "料理":
                continue

            ingredients = parse_ingredients(raw)
            recipe = {
                "name": name,
                "kind": "cook" if key == "food" else "craft",
                "category": category,
                "ingredients": ingredients,
                "source": key,
            }
            if key == "food":
                conditions = dict(zip(
                    ["criteria", "restriction", "seconds", "shelfLife"],
                    row[4:8],
                ))
                stats = dict(zip(["health", "hunger", "sanity"], row[8:11]))
                recipe["food"] = {
                    field: value for field, value in (conditions | stats).items()
                    if value and value != "/"
                }
                if name in KNOWN_EXCEPTIONS:
                    recipe["note"] = KNOWN_EXCEPTIONS[name]
                    recipe["ingredients"] = None
                elif ingredients and sum(entry["quantity"] for entry in ingredients) != 4:
                    recipe["note"] = "Wiki 示例的投料份数待核实。"
                    recipe["ingredients"] = None
            if recipe["ingredients"] is None:
                recipe["reference"] = raw
                recipe["mentions"] = list(dict.fromkeys(
                    item for item in re.findall(NAME_PATTERN, raw) if not item.endswith("度")
                ))
                recipe.setdefault("note", "Wiki 未列全具体食材或用量。")
            recipes.append(recipe)
    keys = {(row["kind"], row["name"]) for row in recipes}
    if any(not row["name"] for row in recipes) or len(keys) != len(recipes):
        raise ValueError("图鉴存在空名称或同名条目，请人工核对")
    if not any(recipe["kind"] == "cook" for recipe in recipes):
        raise ValueError("食物图鉴未识别到料理")
    return {
        "checkedAt": datetime.now(timezone(timedelta(hours=8))).date().isoformat(),
        "sources": sources,
        "recipes": recipes,
        "gaps": gaps,
        "materialFacts": material_facts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".wiki-candidate.json")
    parser.add_argument("--html-dir", type=Path, help="从浏览器保存的四份图鉴 HTML 读取")
    args = parser.parse_args()
    try:
        snapshot = build_snapshot(args.html_dir)
        output = args.output.resolve()
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=output.parent, suffix=".tmp", delete=False, mode="w", encoding="utf-8",
            ) as file:
                temp_path = Path(file.name)
                json.dump(snapshot, file, ensure_ascii=False, indent=2)
                file.write("\n")
            temp_path.replace(output)
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)
    except (OSError, ValueError, KeyError, AttributeError, IndexError) as error:
        sys.exit(f"Wiki update failed: {error}")
    print(f"{output}  ({len(snapshot['recipes'])} recipes; {len(snapshot['gaps'])} material gaps)")


if __name__ == "__main__":
    main()
