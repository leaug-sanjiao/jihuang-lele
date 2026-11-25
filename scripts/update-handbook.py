"""从 4399 公开图鉴生成待核对的事实数据，不保存原文和图片。"""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from urllib.parse import unquote
from urllib.request import urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://a.4399.cn/starve/tools/collection"
DETAIL = "https://mapi.yxhapi.com/gametool/web/v1.0/pictorialBook/detail?tool=starve_collection&uk="


def main():
    with urlopen(BASE, timeout=30) as response:
        page = BeautifulSoup(response.read(), "html.parser")
    modules = json.loads(page.select_one("#__NEXT_DATA__").string)["props"]["pageProps"]["infoData"]
    options = {module["name"]: module["options"] for module in modules}
    tabs = {tab["id"]: tab["label"] for tab in options["type_tabs"]["types"] if tab["show"]}
    items = options["items"]["items"]
    names = {item["id"]: item["name"].strip() for item in items}
    existing = set()
    for filename in ["wiki.json", "supplement.json"]:
        data = json.loads((ROOT / "src/data" / filename).read_text(encoding="utf-8"))
        existing.update(recipe["name"] for recipe in data["recipes"])

    def detail(item):
        tab = item["category"][0]
        name = names[item["id"]]
        creature = tabs[tab] == "生物"
        url = f"{BASE}?tab={tab}&detail_id={item['id']}"
        with urlopen(DETAIL + item["id"], timeout=30) as response:
            data = json.load(response)
        if data["code"] != 100:
            raise ValueError(f"{name} 详情读取失败")
        for section in data["result"]:
            module = section["module"]
            props = module["props"]
            if module["name"] != "material" or not props.get("show"):
                continue
            label = BeautifulSoup(unquote(props.get("itemRowLabel", "")), "html.parser").get_text(strip=True)
            rows = props.get("itemRowItems") or []
            if creature and label == "掉落物品":
                drops = list(dict.fromkeys(names[r["item_id"]] for r in rows if r.get("item_id") in names))
                if drops:
                    return {"name": name, "sourceUrl": url, "drops": drops}
            if not creature and label in ("制作配方", "装备配方") and rows:
                if any(r.get("item_id") not in names or type(r.get("count")) != int or r["count"] < 1 for r in rows):
                    continue
                ingredients = [{"item": names[r["item_id"]], "quantity": r["count"]} for r in rows]
                if len({r["item"] for r in ingredients}) != len(rows) or any(r["item"] == name for r in ingredients):
                    print(f"跳过材料重复或自引用的条目：{name}")
                    continue
                facts = BeautifulSoup(unquote(props["detail"]), "html.parser").get_text(" ", strip=True)
                category = re.search(r"(?:装备类型|类型)\s*[：:]\s*([\u3400-\u9fff]+)", facts)
                if not category:
                    raise ValueError(f"{name} 缺少用途分类")
                return {"name": name, "kind": "craft", "category": category[1], "source": "handbook-tools",
                        "sourceUrl": url, "ingredients": ingredients}

    visible = [item for item in items if item.get("show") and item["category"][0] in tabs]
    targets = [item for item in visible if tabs[item["category"][0]] == "生物" or (
        tabs[item["category"][0]] in ("制造", "装备") and names[item["id"]] not in existing)]
    recipes, creatures = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for record in pool.map(detail, targets):
            if record:
                (creatures if "drops" in record else recipes).append(record)
    if not recipes or not creatures or len({r["name"] for r in recipes}) != len(recipes):
        raise ValueError("图鉴分类或物品名有变，请核对后更新")
    result = {"checkedAt": date.today().isoformat(), "recipes": recipes, "creatures": creatures}
    candidate = ROOT / ".handbook-candidate.json"
    candidate.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{candidate.name}：{len(recipes)} 条配方、{len(creatures)} 条生物掉落记录")


if __name__ == "__main__":
    main()
