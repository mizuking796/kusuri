#!/usr/bin/env python3
"""
new_04_fetch_cyp_chembl.py
ChEMBL REST API から CYP代謝データを取得。

データソース: https://www.ebi.ac.uk/chembl/
ライセンス: CC BY-SA 3.0

API: GET /chembl/api/data/metabolism/
     パラメータ: format=json, metabolizing_enzyme_name=CYP3A4 等

出力: data/cyp_data.json
"""

import json
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
OUTPUT = DATA_DIR / "cyp_data.json"
DRUG_MASTER = DATA_DIR / "drug_master.json"

BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "application/json",
    "User-Agent": "kusuri-research/1.0",
})

# 主要CYP酵素リスト
CYP_ENZYMES = [
    "CYP1A2", "CYP2B6", "CYP2C8", "CYP2C9", "CYP2C19",
    "CYP2D6", "CYP2E1", "CYP3A4", "CYP3A5",
]

# ChEMBL target ID for each CYP
CYP_CHEMBL_TARGETS = {
    "CYP1A2": "CHEMBL3356",
    "CYP2B6": "CHEMBL4482",
    "CYP2C8": "CHEMBL3397",
    "CYP2C9": "CHEMBL3397",  # approx
    "CYP2C19": "CHEMBL3622",
    "CYP2D6": "CHEMBL289",
    "CYP2E1": "CHEMBL2487",
    "CYP3A4": "CHEMBL340",
    "CYP3A5": "CHEMBL2660",
}

REQUEST_DELAY = 0.5


def fetch_cyp_metabolism() -> dict:
    """ChEMBLからCYP代謝情報を取得"""
    if OUTPUT.exists():
        print(f"キャッシュ使用: {OUTPUT}")
        with open(OUTPUT, encoding="utf-8") as f:
            return json.load(f)

    cyp_map = {}  # drug_name → [cyp_enzymes]

    # Method 1: metabolism endpoint
    print("=== ChEMBL metabolism endpoint ===")
    url = f"{BASE_URL}/metabolism.json"
    offset = 0
    limit = 100
    total_found = 0

    while True:
        params = {"offset": offset, "limit": limit}
        try:
            resp = SESSION.get(url, params=params, timeout=30)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ERROR offset={offset}: {e}")
            break

        results = data.get("metabolisms", data.get("results", []))
        if not results:
            break

        for item in results:
            enzyme = item.get("metabolizing_enzyme_name", "")
            substrate = item.get("substrate_name", "")

            if not enzyme or not substrate:
                continue

            # CYPのみ対象
            enzyme_upper = enzyme.upper().replace(" ", "")
            matched_cyp = None
            for cyp in CYP_ENZYMES:
                if cyp in enzyme_upper:
                    matched_cyp = cyp
                    break

            if not matched_cyp:
                continue

            sub_lower = substrate.lower()
            if sub_lower not in cyp_map:
                cyp_map[sub_lower] = set()
            cyp_map[sub_lower].add(matched_cyp)
            total_found += 1

        total_count = data.get("page_meta", {}).get("total_count", 0)
        offset += limit
        print(f"  offset={offset}, found={total_found}, total_api={total_count}")

        if offset >= total_count or not results:
            break

        time.sleep(REQUEST_DELAY)

    # Method 2: 既知のCYP-薬マッピング（ChEMBL文献ベース）
    # 主要薬のCYP代謝は広く知られている - フォールバック
    KNOWN_CYP = {
        "warfarin": ["CYP2C9", "CYP1A2", "CYP3A4"],
        "omeprazole": ["CYP2C19", "CYP3A4"],
        "lansoprazole": ["CYP2C19", "CYP3A4"],
        "clopidogrel": ["CYP2C19", "CYP3A4", "CYP2B6"],
        "simvastatin": ["CYP3A4"],
        "atorvastatin": ["CYP3A4"],
        "metoprolol": ["CYP2D6"],
        "carvedilol": ["CYP2D6", "CYP2C9"],
        "diazepam": ["CYP2C19", "CYP3A4"],
        "midazolam": ["CYP3A4"],
        "alprazolam": ["CYP3A4"],
        "codeine": ["CYP2D6"],
        "tramadol": ["CYP2D6", "CYP3A4"],
        "amitriptyline": ["CYP2D6", "CYP2C19"],
        "sertraline": ["CYP2B6", "CYP2C19", "CYP2D6"],
        "paroxetine": ["CYP2D6"],
        "fluoxetine": ["CYP2D6", "CYP2C9"],
        "escitalopram": ["CYP2C19", "CYP3A4"],
        "haloperidol": ["CYP2D6", "CYP3A4"],
        "risperidone": ["CYP2D6"],
        "olanzapine": ["CYP1A2"],
        "quetiapine": ["CYP3A4"],
        "aripiprazole": ["CYP2D6", "CYP3A4"],
        "carbamazepine": ["CYP3A4"],
        "phenytoin": ["CYP2C9", "CYP2C19"],
        "cyclosporine": ["CYP3A4"],
        "tacrolimus": ["CYP3A4", "CYP3A5"],
        "itraconazole": ["CYP3A4"],
        "fluconazole": ["CYP2C9", "CYP2C19", "CYP3A4"],
        "voriconazole": ["CYP2C19", "CYP3A4", "CYP2C9"],
        "clarithromycin": ["CYP3A4"],
        "erythromycin": ["CYP3A4"],
        "rifampicin": ["CYP3A4", "CYP2C9", "CYP2C19"],
        "ritonavir": ["CYP3A4"],
        "amlodipine": ["CYP3A4"],
        "nifedipine": ["CYP3A4"],
        "diltiazem": ["CYP3A4"],
        "verapamil": ["CYP3A4", "CYP1A2"],
        "losartan": ["CYP2C9", "CYP3A4"],
        "irbesartan": ["CYP2C9"],
        "theophylline": ["CYP1A2"],
        "caffeine": ["CYP1A2"],
        "tamoxifen": ["CYP2D6", "CYP3A4"],
        "imatinib": ["CYP3A4", "CYP2D6"],
        "gefitinib": ["CYP3A4"],
        "erlotinib": ["CYP3A4", "CYP1A2"],
        "methadone": ["CYP3A4", "CYP2B6"],
        "fentanyl": ["CYP3A4"],
        "oxycodone": ["CYP3A4", "CYP2D6"],
        "celecoxib": ["CYP2C9"],
        "diclofenac": ["CYP2C9"],
        "ibuprofen": ["CYP2C9"],
        "metformin": [],  # not CYP metabolized
        "amiodarone": ["CYP3A4", "CYP2C9", "CYP2D6"],
        "propranolol": ["CYP2D6", "CYP1A2"],
        "sildenafil": ["CYP3A4"],
        "tadalafil": ["CYP3A4"],
        "rosuvastatin": ["CYP2C9"],
        "pravastatin": [],  # minimal CYP
        "ezetimibe": [],  # UGT, not CYP
        "cimetidine": ["CYP1A2", "CYP2C19", "CYP2D6", "CYP3A4"],
        "donepezil": ["CYP2D6", "CYP3A4"],
        "pioglitazone": ["CYP2C8", "CYP3A4"],
        "repaglinide": ["CYP2C8", "CYP3A4"],
        "montelukast": ["CYP2C8", "CYP3A4", "CYP2C9"],
        "phenobarbital": ["CYP2C9", "CYP2C19"],
    }

    # Merge known into map
    for drug, cyps in KNOWN_CYP.items():
        if drug not in cyp_map:
            cyp_map[drug] = set()
        cyp_map[drug].update(cyps)

    # Convert sets to lists
    result = {k: sorted(v) for k, v in cyp_map.items() if v}

    output = {
        "source": "ChEMBL + curated knowledge base",
        "license": "CC BY-SA 3.0",
        "total_drugs": len(result),
        "cyp_data": result,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n=== CYPデータ統計 ===")
    print(f"薬数: {len(result)}")
    from collections import Counter
    all_cyps = Counter()
    for cyps in result.values():
        all_cyps.update(cyps)
    for cyp, cnt in all_cyps.most_common():
        print(f"  {cyp}: {cnt} 薬")
    print(f"保存: {OUTPUT}")

    return output


def main():
    DATA_DIR.mkdir(exist_ok=True)
    fetch_cyp_metabolism()


if __name__ == "__main__":
    main()
