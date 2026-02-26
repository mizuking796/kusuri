#!/usr/bin/env python3
"""
new_01_fetch_yakka_drugs.py
厚生労働省 薬価基準収載品目リストから成分一覧を抽出。

データソース: https://www.mhlw.go.jp/topics/2025/04/tp20250401-01.html
ライセンス: 政府標準利用規約（CC-BY 4.0互換）

出力: data/yakka_ingredients.json
"""

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
OUTPUT = DATA_DIR / "yakka_ingredients.json"

# 既に抽出済みの厚労省データ
YAKKA_SOURCE = Path("/tmp/yakka_drugs.json")


def normalize_ingredient(name: str) -> str:
    """成分名を正規化"""
    name = name.strip()
    # 全角→半角の基本変換
    name = name.replace("（", "(").replace("）", ")")
    name = name.replace("　", " ")
    # 括弧内の補足を除去（遺伝子組換え等）
    name = re.sub(r"\(遺伝子組換え\)", "", name).strip()
    name = re.sub(r"\(バイオ後続品\)", "", name).strip()
    return name


def main():
    if not YAKKA_SOURCE.exists():
        print(f"ERROR: {YAKKA_SOURCE} が見つかりません。")
        print("先に厚労省薬価データを取得してください。")
        return

    with open(YAKKA_SOURCE, encoding="utf-8") as f:
        raw = json.load(f)

    print(f"ソース: {raw['source']}")
    print(f"取得日: {raw['download_date']}")
    print(f"総品目数: {raw['total_items']}")
    print(f"ユニーク成分数: {raw['unique_ingredients']}")

    ingredients = []
    seen = set()

    for name in raw["ingredients"]:
        norm = normalize_ingredient(name)
        if norm and norm not in seen:
            seen.add(norm)
            ingredients.append({
                "name_ja": norm,
                "original_name": name,
                "category": "general",
            })

    # カテゴリ付与
    by_cat = raw.get("ingredients_by_category", {})
    kampo_set = set(by_cat.get("kampo", []))
    bio_set = set(by_cat.get("biologics", []))
    haigo_set = set(by_cat.get("haigo", []))

    for item in ingredients:
        orig = item["original_name"]
        if orig in kampo_set:
            item["category"] = "kampo"
        elif orig in bio_set:
            item["category"] = "biologics"
        elif orig in haigo_set:
            item["category"] = "haigo"

    output = {
        "source": raw["source"],
        "source_url": raw["source_url"],
        "download_date": raw["download_date"],
        "total_ingredients": len(ingredients),
        "ingredients": ingredients,
    }

    DATA_DIR.mkdir(exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 統計
    cats = {}
    for item in ingredients:
        c = item["category"]
        cats[c] = cats.get(c, 0) + 1

    print(f"\n=== 出力 ===")
    print(f"成分数: {len(ingredients)}")
    for c, n in sorted(cats.items()):
        print(f"  {c}: {n}")
    print(f"保存先: {OUTPUT}")


if __name__ == "__main__":
    main()
