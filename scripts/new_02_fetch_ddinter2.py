#!/usr/bin/env python3
"""
new_02_fetch_ddinter2.py
DDinter 2.0 から全薬リスト + DDI（薬物相互作用）を取得。

データソース: https://ddinter2.scbdd.com/
ライセンス: CC-BY-NC-SA 4.0

API (jQuery DataTables Server-Side Processing):
  POST /server/drug-source/              → draw,start,length形式
  POST /server/interaction-source/       → DDI一覧
  GET  /server/grapher-datasource/{ID}/  → 個別薬DDI
  CSV一括DL: /static/media/download/ddinter_downloads_code_{ATC}.csv

出力:
  data/ddinter_drugs.json         — DDinter2の全薬リスト
  data/ddinter_interactions.json  — 全DDIペア
"""

import csv
import io
import json
import time
from pathlib import Path
from collections import Counter

import requests

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DRUGS_OUTPUT = DATA_DIR / "ddinter_drugs.json"
DDI_OUTPUT = DATA_DIR / "ddinter_interactions.json"

BASE_URL = "https://ddinter2.scbdd.com"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (kusuri-research/1.0; academic use)",
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
})

REQUEST_DELAY = 0.3

# ATCコード別CSV（DDinter2ダウンロードページ提供分）
DDI_CSV_CODES = ["A", "B", "D", "H", "L", "P", "R", "V"]
DDI_CSV_URL = f"{BASE_URL}/static/media/download/ddinter_downloads_code_{{code}}.csv"


def fetch_all_drugs() -> list[dict]:
    """DDinter2から全薬リストを取得（DataTables形式）"""
    if DRUGS_OUTPUT.exists():
        print(f"キャッシュ使用: {DRUGS_OUTPUT}")
        with open(DRUGS_OUTPUT, encoding="utf-8") as f:
            data = json.load(f)
        return data["drugs"]

    all_drugs = []
    start = 0
    page_size = 200
    draw = 1

    print("薬リスト取得中...")
    while True:
        payload = {
            "draw": str(draw),
            "start": str(start),
            "length": str(page_size),
        }

        try:
            resp = SESSION.post(f"{BASE_URL}/server/drug-source/",
                                data=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ERROR start={start}: {e}")
            # Try to parse as text
            print(f"  Response: {resp.text[:200] if resp else 'N/A'}")
            break

        items = data.get("data", [])
        total = data.get("recordsTotal", 0)

        if not items:
            break

        for item in items:
            # DataTablesレスポンスの各行をパース
            # item は dict or list
            if isinstance(item, dict):
                drug = {
                    "DDInter_id": item.get("internalID", ""),
                    "Drug_Name": item.get("name", ""),
                    "DrugBank_ID": item.get("drugbank_id", ""),
                }
            elif isinstance(item, list):
                # リスト形式の場合: [name, display, internalID, smiles, structure, drugbank_id, exist]
                drug = {
                    "DDInter_id": item[2] if len(item) > 2 else "",
                    "Drug_Name": item[0] if len(item) > 0 else "",
                    "DrugBank_ID": item[5] if len(item) > 5 else "",
                }
            else:
                continue

            if drug["DDInter_id"]:
                all_drugs.append(drug)

        print(f"  start={start}: +{len(items)} (total: {len(all_drugs)}/{total})")

        start += page_size
        draw += 1

        if start >= total or len(items) < page_size:
            break

        time.sleep(REQUEST_DELAY)

    # Save
    output = {
        "source": "DDinter 2.0",
        "source_url": "https://ddinter2.scbdd.com/",
        "license": "CC-BY-NC-SA 4.0",
        "total_drugs": len(all_drugs),
        "drugs": all_drugs,
    }
    with open(DRUGS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"薬リスト保存: {len(all_drugs)} 薬 → {DRUGS_OUTPUT}")
    return all_drugs


def fetch_ddis_from_csv() -> list[dict]:
    """DDinter2のCSV一括ダウンロードからDDIを取得"""
    all_ddis = []
    seen_pairs = set()

    for code in DDI_CSV_CODES:
        url = DDI_CSV_URL.format(code=code)
        print(f"  ATC code {code}: {url}")

        try:
            resp = SESSION.get(url, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            print(f"    ERROR: {e}")
            continue

        # Parse CSV
        text = resp.text
        reader = csv.reader(io.StringIO(text))
        header = next(reader, None)
        print(f"    Header: {header}")

        count = 0
        for row in reader:
            if len(row) < 5:
                continue

            # DDInterID_A, Drug_A, DDInterID_B, Drug_B, Level
            dd_id_a = row[0].strip()
            drug_a = row[1].strip()
            dd_id_b = row[2].strip()
            drug_b = row[3].strip()
            level = row[4].strip()

            pair_key = tuple(sorted([dd_id_a, dd_id_b]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Level → numeric: Major=3, Moderate=2, Minor=1
            level_num = "2"  # default
            if "major" in level.lower():
                level_num = "3"
            elif "moderate" in level.lower():
                level_num = "2"
            elif "minor" in level.lower():
                level_num = "1"

            all_ddis.append({
                "drug_a": dd_id_a,
                "drug_b": dd_id_b,
                "drug_a_name": drug_a,
                "drug_b_name": drug_b,
                "level": level_num,
                "mechanism": "",
            })
            count += 1

        print(f"    DDI取得: {count}")
        time.sleep(REQUEST_DELAY)

    return all_ddis


def fetch_ddis_from_api(drugs: list[dict]) -> list[dict]:
    """API (interaction-source) からDDI一覧を取得"""
    all_ddis = []
    seen_pairs = set()
    start = 0
    page_size = 500
    draw = 1

    print("DDI一覧取得中 (interaction-source API)...")
    while True:
        payload = {
            "draw": str(draw),
            "start": str(start),
            "length": str(page_size),
        }

        try:
            resp = SESSION.post(f"{BASE_URL}/server/interaction-source/",
                                data=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ERROR start={start}: {e}")
            break

        items = data.get("data", [])
        total = data.get("recordsTotal", 0)

        if not items:
            break

        for item in items:
            if isinstance(item, dict):
                # interaction-source のレスポンス形式
                ix_id = item.get("id", "")
                level = str(item.get("level", ""))
                # この endpoint は interaction group なので個別ペアではない
                # grapher-datasource を使うか CSV を使うべき
                pass

        print(f"  start={start}: +{len(items)} (total: {len(all_ddis)}/{total})")
        start += page_size
        draw += 1

        if start >= total or len(items) < page_size:
            break

        time.sleep(REQUEST_DELAY)

    return all_ddis


def fetch_ddis_per_drug(drugs: list[dict]) -> list[dict]:
    """各薬のDDI情報を個別取得（grapher-datasource）"""
    all_ddis = []
    seen_pairs = set()
    errors = 0

    for i, drug in enumerate(drugs):
        dd_id = drug.get("DDInter_id", "")
        if not dd_id:
            continue

        url = f"{BASE_URL}/server/grapher-datasource/{dd_id}/"

        try:
            resp = SESSION.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  ERROR {dd_id}: {e}")
            continue

        # grapher-datasource format: {info: {id, Name}, interactions: [{id, name, level[], actions[]}, ...]}
        interactions = data.get("interactions", [])

        for ix in interactions:
            partner_id = ix.get("id", "")
            partner_name = ix.get("name", "")
            levels = ix.get("level", [])
            # level is array like [3] or [2, 1] → take max
            level = str(max(levels)) if levels else "2"

            if not partner_id:
                continue

            pair_key = tuple(sorted([dd_id, partner_id]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            all_ddis.append({
                "drug_a": dd_id,
                "drug_b": partner_id,
                "drug_a_name": drug.get("Drug_Name", ""),
                "drug_b_name": partner_name,
                "level": level,
                "mechanism": "",
            })

        if (i + 1) % 100 == 0:
            print(f"  進捗: {i+1}/{len(drugs)}, DDI: {len(all_ddis)}, err: {errors}")

        time.sleep(REQUEST_DELAY)

    print(f"DDI取得完了: {len(all_ddis)} ペア, エラー: {errors}")
    return all_ddis


def main():
    DATA_DIR.mkdir(exist_ok=True)

    # === Phase 1: Drug list ===
    print("=== Phase 1: DDinter2 薬リスト取得 ===")
    drugs = fetch_all_drugs()

    print(f"\n薬リスト統計:")
    print(f"  総数: {len(drugs)}")
    has_drugbank = sum(1 for d in drugs if d.get("DrugBank_ID"))
    print(f"  DrugBank ID あり: {has_drugbank}")
    for d in drugs[:3]:
        print(f"  Sample: {json.dumps(d, ensure_ascii=False)[:200]}")

    # === Phase 2: DDI ===
    if DDI_OUTPUT.exists():
        print(f"\nキャッシュ使用: {DDI_OUTPUT}")
        with open(DDI_OUTPUT, encoding="utf-8") as f:
            ddi_data = json.load(f)
        all_ddis = ddi_data["interactions"]
    else:
        print(f"\n=== Phase 2: DDI取得 ===")

        # Strategy 1: CSV一括ダウンロード（高速、ただし一部ATCのみ）
        print("\n--- CSV一括ダウンロード ---")
        csv_ddis = fetch_ddis_from_csv()
        print(f"CSV DDI: {len(csv_ddis)}")

        # Strategy 2: 残りは per-drug API
        if len(csv_ddis) > 0:
            all_ddis = csv_ddis
            print("CSV DDIで十分なデータ取得。per-drug APIはスキップ。")
        else:
            print("\nCSV取得失敗。per-drug APIで取得...")
            all_ddis = fetch_ddis_per_drug(drugs)

        # Save
        output = {
            "source": "DDinter 2.0",
            "license": "CC-BY-NC-SA 4.0",
            "total_interactions": len(all_ddis),
            "interactions": all_ddis,
        }
        with open(DDI_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"保存: {DDI_OUTPUT}")

    # Stats
    levels = Counter(d["level"] for d in all_ddis)
    print(f"\n=== DDI統計 ===")
    print(f"総DDIペア: {len(all_ddis)}")
    for lv, cnt in levels.most_common():
        label = {"3": "Major", "2": "Moderate", "1": "Minor"}.get(lv, lv)
        print(f"  Level {lv} ({label}): {cnt}")


if __name__ == "__main__":
    main()
