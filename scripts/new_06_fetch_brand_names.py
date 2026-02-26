#!/usr/bin/env python3
"""
new_06_fetch_brand_names.py
SSK薬価基準マスターから商品名（ブランド名）を取得。
既存 11_ssk_brand_names.py のロジックを再利用。

データソース: 社会保険診療報酬支払基金 薬価基準マスター
ライセンス: 政府標準利用規約

出力: data/brand_names_new.json
"""

import csv
import json
import os
import re
import zipfile
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DRUG_MASTER = DATA_DIR / "drug_master.json"
OUTPUT = DATA_DIR / "brand_names_new.json"

SSK_ZIP_URL = "https://www.ssk.or.jp/seikyushiharai/tensuhyo/kihonmasta/r06/kihonmasta_04.files/y_ALL20260219.zip"
SSK_CACHE = DATA_DIR / "ssk_yakka_master.csv"

DOSAGE_FORMS = [
    "ドライシロップ", "シロップ", "カプセル", "ローション",
    "エアゾール", "パッチ", "フィルム", "ペースト", "リキッド",
    "スプレー", "クリーム", "テープ", "パップ", "吸入", "点眼",
    "点鼻", "経口", "口腔", "腸溶", "配合", "注射", "軟膏",
    "顆粒", "細粒", "散", "錠", "液", "丸", "坐剤", "ゼリー",
    "ゲル", "粉末",
]


def download_ssk_master() -> Path:
    """SSK薬価マスターをダウンロード"""
    if SSK_CACHE.exists():
        print(f"キャッシュ使用: {SSK_CACHE}")
        return SSK_CACHE

    print(f"SSKマスターダウンロード: {SSK_ZIP_URL}")
    zip_path = str(SSK_CACHE) + ".zip"
    urllib.request.urlretrieve(SSK_ZIP_URL, zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        csv_name = [n for n in names if n.endswith(".csv")][0]
        with zf.open(csv_name) as src, open(SSK_CACHE, "wb") as dst:
            dst.write(src.read())

    os.remove(zip_path)
    print(f"保存: {SSK_CACHE}")
    return SSK_CACHE


def extract_base_name(full_name: str) -> str:
    """商品名から剤形・含量を除去"""
    name = full_name.strip()
    for form in sorted(DOSAGE_FORMS, key=len, reverse=True):
        idx = name.find(form)
        if idx > 0:
            name = name[:idx]
            break
    name = re.sub(r"[\d０-９．・％%ｍｇμＬｋｇｍＬ]+$", "", name).strip()
    name = re.sub(r"[　\s]+$", "", name)
    name = re.sub(r"（.*?）$", "", name).strip()
    return name


def extract_ingredient_name(generic_str: str) -> str:
    """【般】ファモチジン散２％ → ファモチジン"""
    name = generic_str.replace("【般】", "").strip()
    return extract_base_name(name)


def parse_ssk_master(csv_path: Path) -> dict:
    """SSKマスターから 一般名→商品名 マッピング構築"""
    with open(csv_path, encoding="shift_jis", errors="replace") as f:
        rows = list(csv.reader(f))

    ingredient_brands = {}
    for r in rows:
        if len(r) < 38:
            continue
        brand_full = r[4].strip()
        generic_raw = r[37].strip()

        if not generic_raw.startswith("【般】"):
            continue

        ingredient = extract_ingredient_name(generic_raw)
        if len(ingredient) < 2:
            continue

        brand_base = extract_base_name(brand_full)
        if len(brand_base) < 2:
            continue

        if ingredient not in ingredient_brands:
            ingredient_brands[ingredient] = set()

        if brand_base != ingredient and not brand_base.startswith(ingredient):
            ingredient_brands[ingredient].add(brand_base)

    return ingredient_brands


def match_brands(drugs: list[dict], ingredient_brands: dict) -> dict:
    """Drug masterの各薬とSSK商品名をマッチ"""
    brand_map = {}  # drug_id → [brand_names]

    for drug in drugs:
        drug_id = drug["id"]
        name_ja = drug.get("name_ja", "")
        if not name_ja:
            continue

        matched_brands = set()

        for ingredient, brands in ingredient_brands.items():
            if (ingredient == name_ja or
                ingredient in name_ja or
                name_ja in ingredient or
                (len(ingredient) >= 4 and len(name_ja) >= 4 and
                 ingredient[:4] == name_ja[:4])):
                matched_brands.update(brands)

        if matched_brands:
            brand_map[drug_id] = sorted(matched_brands)

    return brand_map


def main():
    DATA_DIR.mkdir(exist_ok=True)

    if not DRUG_MASTER.exists():
        print(f"ERROR: {DRUG_MASTER} not found. Run new_03 first.")
        return

    with open(DRUG_MASTER, encoding="utf-8") as f:
        master = json.load(f)

    drugs = master["drugs"]
    print(f"Drug master: {len(drugs)} 薬")

    # Download SSK
    csv_path = download_ssk_master()

    # Parse
    ingredient_brands = parse_ssk_master(csv_path)
    total_brands = sum(len(v) for v in ingredient_brands.values())
    print(f"SSK: {len(ingredient_brands)} 成分, {total_brands} ユニーク商品名")

    # Match
    brand_map = match_brands(drugs, ingredient_brands)

    output = {
        "source": "SSK 薬価基準マスター",
        "license": "政府標準利用規約",
        "total_matched": len(brand_map),
        "total_brands": sum(len(v) for v in brand_map.values()),
        "brand_names": brand_map,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n=== 商品名統計 ===")
    print(f"マッチ薬数: {len(brand_map)}/{len(drugs)}")
    print(f"商品名総数: {output['total_brands']}")
    print(f"保存: {OUTPUT}")


if __name__ == "__main__":
    main()
