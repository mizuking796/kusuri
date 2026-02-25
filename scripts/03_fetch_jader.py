#!/usr/bin/env python3
"""
Step 3: JADER（副作用報告データ）のダウンロードと処理
PMDAからCSVデータを取得し、初期薬リストの副作用を集計
"""

import csv
import io
import json
import os
import re
import zipfile
from pathlib import Path
from collections import defaultdict, Counter

import pandas as pd
import requests

DATA_DIR = Path(__file__).parent.parent / "data"
JADER_DIR = DATA_DIR / "jader_raw"

# JADERダウンロードURL（PMDA公開データ）
# Note: URLは変更される可能性あり。手動DLが必要な場合もある
JADER_BASE_URL = "https://www.pmda.go.jp/safety/info-services/drugs/adr-info/suspected-adr/0005.html"


def download_jader_csvs():
    """JADERのCSVファイルを取得（PMDAから直接DLできない場合の代替処理）"""
    JADER_DIR.mkdir(exist_ok=True)

    # PMDAのJADERは直接APIダウンロードが難しい場合がある
    # まず手動ダウンロード手順を表示
    print("=" * 60)
    print("JADER データのダウンロード手順:")
    print("=" * 60)
    print()
    print("PMDAのJADERデータは以下のURLから手動ダウンロードが必要です:")
    print("https://www.pmda.go.jp/safety/info-services/drugs/adr-info/suspected-adr/0004.html")
    print()
    print("ダウンロードしたZIPファイルを以下に配置してください:")
    print(f"  {JADER_DIR}/")
    print()
    print("ZIP内に含まれるCSVファイル:")
    print("  - demo.csv (症例情報: 性別, 年齢, 体重)")
    print("  - drug.csv (医薬品情報: 一般名, 販売名)")
    print("  - reac.csv (副作用名)")
    print("  - hist.csv (原疾患等)")
    print()

    # Check if files already exist
    expected_files = ['drug.csv', 'reac.csv']
    existing = [f for f in expected_files if (JADER_DIR / f).exists()]

    if len(existing) == len(expected_files):
        print("全ファイルが見つかりました。処理を続行します。")
        return True

    # Try to download programmatically
    print("自動ダウンロードを試みます...")
    try:
        # Try the direct download link (may not work)
        r = requests.get(
            "https://www.pmda.go.jp/safety/info-services/drugs/adr-info/suspected-adr/0004.html",
            timeout=30
        )
        print(f"PMDAページ取得: status={r.status_code}")

        # Look for download links in the page
        zip_urls = re.findall(r'href="([^"]*\.zip)"', r.text, re.IGNORECASE)
        csv_urls = re.findall(r'href="([^"]*\.csv)"', r.text, re.IGNORECASE)

        print(f"ZIP links found: {len(zip_urls)}")
        print(f"CSV links found: {len(csv_urls)}")

        if zip_urls:
            for url in zip_urls[:3]:
                print(f"  Found: {url}")
        if csv_urls:
            for url in csv_urls[:3]:
                print(f"  Found: {url}")

    except Exception as e:
        print(f"自動ダウンロード失敗: {e}")

    return False


def process_jader_data(drug_list: list[dict]) -> dict:
    """JADERデータを処理して薬→副作用マッピングを作成"""

    drug_file = JADER_DIR / "drug.csv"
    reac_file = JADER_DIR / "reac.csv"

    if not drug_file.exists() or not reac_file.exists():
        print("JADERファイルが見つかりません。代替データを生成します。")
        return generate_fallback_adverse_effects(drug_list)

    print("=== JADER CSVを処理中 ===\n")

    # Read drug.csv (case_id, drug_name_general, drug_name_brand, ...)
    df_drug = pd.read_csv(drug_file, encoding='cp932', low_memory=False)
    print(f"drug.csv: {len(df_drug)} rows")

    # Read reac.csv (case_id, adverse_reaction, ...)
    df_reac = pd.read_csv(reac_file, encoding='cp932', low_memory=False)
    print(f"reac.csv: {len(df_reac)} rows")

    # Create drug name → KEGG ID mapping
    name_to_id = {}
    for d in drug_list:
        name_en = d.get('name_en', '').lower()
        search = d.get('search_name', '').lower()
        kegg_id = d['kegg_id']
        name_to_id[name_en] = kegg_id
        name_to_id[search] = kegg_id

    # Merge drug and reaction data
    # JADER columns vary by year, try common column names
    case_col = None
    for col in ['識別番号', 'case_id', '症例番号']:
        if col in df_drug.columns:
            case_col = col
            break

    if case_col is None:
        print(f"WARNING: Cannot find case ID column. Columns: {list(df_drug.columns)}")
        return {}

    drug_name_col = None
    for col in ['医薬品（一般名）', 'drug_name', '一般名']:
        if col in df_drug.columns:
            drug_name_col = col
            break

    reac_name_col = None
    for col in ['有害事象', 'adverse_reaction', '副作用名']:
        if col in df_reac.columns:
            reac_name_col = col
            break

    print(f"Using columns: case={case_col}, drug={drug_name_col}, reaction={reac_name_col}")

    # Aggregate: drug → [adverse effects with counts]
    # ... (Full JADER processing would go here)

    return {}


def generate_fallback_adverse_effects(drug_list: list[dict]) -> list[dict]:
    """
    JADERが手元にない場合の代替：
    KEGG DRUGの情報と一般的な医学知識から主要副作用を構造化
    本番データが入手できたら差し替える
    """
    print("=== 代替副作用データを生成 ===")
    print("注意: これはKEGG情報ベースの推定データです。")
    print("JADERデータ入手後に差し替えてください。\n")

    # Drug class → common adverse effects mapping
    class_adverse_effects = {
        "NSAID": [
            {"name": "胃腸障害", "name_en": "Gastrointestinal disorder", "frequency": "high"},
            {"name": "腎機能障害", "name_en": "Renal impairment", "frequency": "medium"},
            {"name": "出血傾向", "name_en": "Bleeding tendency", "frequency": "medium"},
            {"name": "肝機能障害", "name_en": "Hepatic impairment", "frequency": "low"},
        ],
        "Statin": [
            {"name": "横紋筋融解症", "name_en": "Rhabdomyolysis", "frequency": "rare"},
            {"name": "肝機能障害", "name_en": "Hepatic impairment", "frequency": "medium"},
            {"name": "筋肉痛", "name_en": "Myalgia", "frequency": "high"},
            {"name": "消化器症状", "name_en": "GI symptoms", "frequency": "medium"},
        ],
        "ACE inhibitor": [
            {"name": "空咳", "name_en": "Dry cough", "frequency": "high"},
            {"name": "高カリウム血症", "name_en": "Hyperkalemia", "frequency": "medium"},
            {"name": "血管浮腫", "name_en": "Angioedema", "frequency": "rare"},
            {"name": "腎機能障害", "name_en": "Renal impairment", "frequency": "medium"},
        ],
        "ARB": [
            {"name": "高カリウム血症", "name_en": "Hyperkalemia", "frequency": "medium"},
            {"name": "めまい", "name_en": "Dizziness", "frequency": "medium"},
            {"name": "腎機能障害", "name_en": "Renal impairment", "frequency": "low"},
        ],
        "CCB": [
            {"name": "浮腫", "name_en": "Edema", "frequency": "high"},
            {"name": "頭痛", "name_en": "Headache", "frequency": "medium"},
            {"name": "便秘", "name_en": "Constipation", "frequency": "medium"},
            {"name": "歯肉肥厚", "name_en": "Gingival hyperplasia", "frequency": "low"},
        ],
        "Beta blocker": [
            {"name": "徐脈", "name_en": "Bradycardia", "frequency": "high"},
            {"name": "低血圧", "name_en": "Hypotension", "frequency": "medium"},
            {"name": "気管支痙攣", "name_en": "Bronchospasm", "frequency": "medium"},
            {"name": "倦怠感", "name_en": "Fatigue", "frequency": "medium"},
        ],
        "DPP-4 inhibitor": [
            {"name": "低血糖", "name_en": "Hypoglycemia", "frequency": "medium"},
            {"name": "腸閉塞", "name_en": "Ileus", "frequency": "rare"},
            {"name": "膵炎", "name_en": "Pancreatitis", "frequency": "rare"},
        ],
        "SGLT2 inhibitor": [
            {"name": "尿路感染症", "name_en": "Urinary tract infection", "frequency": "high"},
            {"name": "性器感染症", "name_en": "Genital infection", "frequency": "high"},
            {"name": "ケトアシドーシス", "name_en": "Ketoacidosis", "frequency": "rare"},
            {"name": "脱水", "name_en": "Dehydration", "frequency": "medium"},
        ],
        "Biguanide": [
            {"name": "乳酸アシドーシス", "name_en": "Lactic acidosis", "frequency": "rare"},
            {"name": "消化器症状", "name_en": "GI symptoms", "frequency": "high"},
            {"name": "ビタミンB12低下", "name_en": "Vitamin B12 deficiency", "frequency": "medium"},
        ],
        "PPI": [
            {"name": "低マグネシウム血症", "name_en": "Hypomagnesemia", "frequency": "medium"},
            {"name": "骨折リスク増加", "name_en": "Fracture risk", "frequency": "low"},
            {"name": "Clostridioides difficile感染", "name_en": "C. difficile infection", "frequency": "low"},
            {"name": "消化器症状", "name_en": "GI symptoms", "frequency": "medium"},
        ],
        "Anticoagulant": [
            {"name": "出血", "name_en": "Hemorrhage", "frequency": "high"},
            {"name": "貧血", "name_en": "Anemia", "frequency": "medium"},
            {"name": "消化器症状", "name_en": "GI symptoms", "frequency": "medium"},
        ],
        "Benzodiazepine": [
            {"name": "眠気", "name_en": "Somnolence", "frequency": "high"},
            {"name": "依存性", "name_en": "Dependence", "frequency": "high"},
            {"name": "ふらつき", "name_en": "Unsteadiness", "frequency": "high"},
            {"name": "記憶障害", "name_en": "Memory impairment", "frequency": "medium"},
        ],
        "SSRI": [
            {"name": "悪心", "name_en": "Nausea", "frequency": "high"},
            {"name": "性機能障害", "name_en": "Sexual dysfunction", "frequency": "high"},
            {"name": "不眠", "name_en": "Insomnia", "frequency": "medium"},
            {"name": "セロトニン症候群", "name_en": "Serotonin syndrome", "frequency": "rare"},
        ],
        "Fluoroquinolone": [
            {"name": "腱障害", "name_en": "Tendon disorder", "frequency": "low"},
            {"name": "QT延長", "name_en": "QT prolongation", "frequency": "low"},
            {"name": "消化器症状", "name_en": "GI symptoms", "frequency": "medium"},
            {"name": "光線過敏症", "name_en": "Photosensitivity", "frequency": "medium"},
        ],
        "Macrolide": [
            {"name": "消化器症状", "name_en": "GI symptoms", "frequency": "high"},
            {"name": "QT延長", "name_en": "QT prolongation", "frequency": "low"},
            {"name": "肝機能障害", "name_en": "Hepatic impairment", "frequency": "low"},
        ],
        "Antipsychotic": [
            {"name": "体重増加", "name_en": "Weight gain", "frequency": "high"},
            {"name": "代謝異常", "name_en": "Metabolic disorder", "frequency": "high"},
            {"name": "錐体外路症状", "name_en": "Extrapyramidal symptoms", "frequency": "medium"},
            {"name": "QT延長", "name_en": "QT prolongation", "frequency": "low"},
        ],
        "Opioid": [
            {"name": "便秘", "name_en": "Constipation", "frequency": "high"},
            {"name": "悪心・嘔吐", "name_en": "Nausea/vomiting", "frequency": "high"},
            {"name": "眠気", "name_en": "Somnolence", "frequency": "high"},
            {"name": "呼吸抑制", "name_en": "Respiratory depression", "frequency": "medium"},
            {"name": "依存性", "name_en": "Dependence", "frequency": "high"},
        ],
    }

    # Map drug → class based on KEGG drug_class info
    drug_adverse = []
    for drug in drug_list:
        drug_classes = ' '.join(drug.get('drug_class', []))
        efficacy = drug.get('efficacy', '')
        combined = (drug_classes + ' ' + efficacy).lower()

        matched_effects = []
        for cls, effects in class_adverse_effects.items():
            if cls.lower() in combined:
                matched_effects.extend(effects)

        # Deduplicate
        seen = set()
        unique_effects = []
        for e in matched_effects:
            if e['name'] not in seen:
                seen.add(e['name'])
                unique_effects.append(e)

        drug_adverse.append({
            'kegg_id': drug['kegg_id'],
            'name': drug.get('search_name', drug.get('name_en', '')),
            'adverse_effects': unique_effects,
        })

    # Save
    output = DATA_DIR / "adverse_effects.json"
    with open(output, "w", encoding='utf-8') as f:
        json.dump(drug_adverse, f, ensure_ascii=False, indent=2)

    total_effects = sum(len(d['adverse_effects']) for d in drug_adverse)
    with_effects = sum(1 for d in drug_adverse if d['adverse_effects'])
    print(f"Drugs with adverse effects: {with_effects}/{len(drug_adverse)}")
    print(f"Total adverse effect entries: {total_effects}")
    print(f"Saved to: {output}")

    return drug_adverse


def main():
    # Load initial drug list
    drugs_file = DATA_DIR / "initial_drugs.json"
    if not drugs_file.exists():
        print("ERROR: initial_drugs.json not found. Run 01_build_drug_list.py first.")
        return

    with open(drugs_file) as f:
        drugs = json.load(f)

    print(f"Loaded {len(drugs)} drugs\n")

    # Try to download JADER
    has_jader = download_jader_csvs()

    if has_jader:
        process_jader_data(drugs)
    else:
        print("\nJADERデータが未取得のため、代替データで進めます。")
        print("後でJADERデータを取得して差し替え可能です。\n")
        generate_fallback_adverse_effects(drugs)


if __name__ == '__main__':
    main()
