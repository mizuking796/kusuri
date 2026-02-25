#!/usr/bin/env python3
"""
11_ssk_brand_names.py — 厚労省SSK薬価基準マスターから商品名を追加

データソース: 社会保険診療報酬支払基金 薬価基準収載品目リスト（政府オープンデータ）
https://www.ssk.or.jp/seikyushiharai/tensuhyo/kihonmasta/

graph-light.json の各薬ノードに、SSK薬価マスターから抽出した
日本語商品名を names_alt に追加する。

冪等: 何度実行しても同じ結果
"""

import csv, re, json, os, zipfile, urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH_LIGHT = os.path.join(BASE, 'data', 'graph', 'graph-light.json')
SSK_ZIP_URL = "https://www.ssk.or.jp/seikyushiharai/tensuhyo/kihonmasta/r06/kihonmasta_04.files/y_ALL20260219.zip"
SSK_CACHE = os.path.join(BASE, 'data', 'ssk_yakka_master.csv')

DOSAGE_FORMS = [
    'ドライシロップ', 'シロップ', 'カプセル', 'ローション',
    'エアゾール', 'パッチ', 'フィルム', 'ペースト', 'リキッド',
    'スプレー', 'クリーム', 'テープ', 'パップ', '吸入', '点眼',
    '点鼻', '経口', '口腔', '腸溶', '配合', '注射', '軟膏',
    '顆粒', '細粒', '散', '錠', '液', '丸', '坐剤', 'ゼリー',
    'ゲル', '粉末',
]


def download_ssk_master():
    """SSK薬価マスターをダウンロード（キャッシュ使用）"""
    if os.path.exists(SSK_CACHE):
        print(f"Using cached SSK master: {SSK_CACHE}")
        return SSK_CACHE

    print(f"Downloading SSK master from {SSK_ZIP_URL} ...")
    zip_path = SSK_CACHE + '.zip'
    urllib.request.urlretrieve(SSK_ZIP_URL, zip_path)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = zf.namelist()
        csv_name = [n for n in names if n.endswith('.csv')][0]
        with zf.open(csv_name) as src, open(SSK_CACHE, 'wb') as dst:
            dst.write(src.read())

    os.remove(zip_path)
    print(f"Saved to {SSK_CACHE}")
    return SSK_CACHE


def extract_base_name(full_name):
    """商品名から剤形・含量を除去して基本名を抽出"""
    name = full_name.strip()
    # Remove dosage forms
    for form in sorted(DOSAGE_FORMS, key=len, reverse=True):
        idx = name.find(form)
        if idx > 0:
            name = name[:idx]
            break
    # Remove trailing numbers, percentages, spaces
    name = re.sub(r'[\d０-９．・％%ｍｇμＬｋｇｍＬ]+$', '', name).strip()
    name = re.sub(r'[　\s]+$', '', name)
    # Remove full-width parens content
    name = re.sub(r'（.*?）$', '', name).strip()
    return name


def extract_ingredient_name(generic_str):
    """【般】ファモチジン散２％ → ファモチジン"""
    name = generic_str.replace('【般】', '').strip()
    return extract_base_name(name)


def parse_ssk_master(csv_path):
    """SSKマスターCSVから 一般名→商品名 マッピングを構築"""
    with open(csv_path, encoding='shift_jis', errors='replace') as f:
        rows = list(csv.reader(f))

    # Col4=商品名, Col37=【般】一般名
    ingredient_brands = {}

    for r in rows:
        if len(r) < 38:
            continue
        brand_full = r[4].strip()
        generic_raw = r[37].strip()

        if not generic_raw.startswith('【般】'):
            continue

        ingredient = extract_ingredient_name(generic_raw)
        if len(ingredient) < 2:
            continue

        brand_base = extract_base_name(brand_full)
        if len(brand_base) < 2:
            continue

        if ingredient not in ingredient_brands:
            ingredient_brands[ingredient] = set()

        # Only add if different from ingredient name
        if brand_base != ingredient and not brand_base.startswith(ingredient):
            ingredient_brands[ingredient].add(brand_base)

    return ingredient_brands


def match_and_patch(ingredient_brands):
    """graph-light.json の薬ノードとマッチして商品名を追加"""
    with open(GRAPH_LIGHT, 'r') as f:
        graph = json.load(f)

    drug_nodes = {n['id']: n for n in graph['nodes'] if n['type'] == 'drug'}

    stats = {'matched': 0, 'brands_added': 0, 'drugs_updated': 0}

    for kegg_id, node in drug_nodes.items():
        name_ja = node.get('name_ja', '')
        if not name_ja:
            continue

        # Try to match with SSK ingredients
        matched_brands = set()

        for ingredient, brands in ingredient_brands.items():
            # Exact match or substring match
            if (ingredient == name_ja or
                ingredient in name_ja or
                name_ja in ingredient or
                # Handle salt form differences: ロキソプロフェンナトリウム水和物 vs ロキソプロフェンナトリウム
                (len(ingredient) >= 4 and len(name_ja) >= 4 and
                 (ingredient[:4] == name_ja[:4]))):
                matched_brands.update(brands)

        if not matched_brands:
            # Try matching via names_alt
            for alt in node.get('names_alt', []):
                if '(TN)' in alt:
                    continue  # Skip English trade names
                for ingredient, brands in ingredient_brands.items():
                    if ingredient in alt or alt in ingredient:
                        matched_brands.update(brands)

        if matched_brands:
            stats['matched'] += 1
            existing_alt = set(node.get('names_alt', []))
            new_brands = matched_brands - existing_alt
            if new_brands:
                if 'names_alt' not in node:
                    node['names_alt'] = []
                node['names_alt'].extend(sorted(new_brands))
                stats['brands_added'] += len(new_brands)
                stats['drugs_updated'] += 1

    # Save
    with open(GRAPH_LIGHT, 'w') as f:
        json.dump(graph, f, ensure_ascii=False, separators=(',', ':'))

    return stats, graph


def main():
    # 1. Download SSK master
    csv_path = download_ssk_master()

    # 2. Parse
    ingredient_brands = parse_ssk_master(csv_path)
    total_brands = sum(len(v) for v in ingredient_brands.values())
    print(f"SSK: {len(ingredient_brands)} ingredients, {total_brands} unique brand names")

    # 3. Match and patch
    stats, graph = match_and_patch(ingredient_brands)

    # 4. Stats
    drugs = [n for n in graph['nodes'] if n['type'] == 'drug']
    has_alt = sum(1 for n in drugs if n.get('names_alt'))
    has_ja_brand = sum(1 for n in drugs if any(
        not a.endswith('(TN)') and not a.startswith(n.get('name_en', '').split()[0][:3])
        for a in n.get('names_alt', [])
    ))

    print(f"\n=== Results ===")
    print(f"Matched drugs: {stats['matched']}")
    print(f"Drugs updated: {stats['drugs_updated']}")
    print(f"Brand names added: {stats['brands_added']}")
    print(f"names_alt coverage: {has_alt}/{len(drugs)}")


if __name__ == '__main__':
    main()
