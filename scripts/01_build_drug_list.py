#!/usr/bin/env python3
"""
Step 1: 初期薬リスト（~300品目）の作成
KEGG BRITE hierarchy + 手動キュレーションで主要薬を選定し、
KEGG REST APIから詳細情報を取得
"""

import json
import re
import time
import requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
KEGG_BASE = "https://rest.kegg.jp"
RATE_LIMIT = 0.35  # 3 requests/sec max

# === 主要薬リスト（日本で頻用される一般名 → KEGG IDマッピング用） ===
# NDB処方データ + 臨床使用頻度ベースで選定

PRIORITY_DRUGS_EN = [
    # --- 鎮痛・解熱・抗炎症 ---
    "Loxoprofen", "Acetaminophen", "Ibuprofen", "Diclofenac", "Celecoxib",
    "Aspirin", "Indomethacin", "Naproxen", "Etodolac", "Meloxicam",
    # --- 降圧薬 ---
    "Amlodipine", "Nifedipine", "Valsartan", "Candesartan", "Olmesartan",
    "Telmisartan", "Losartan", "Azilsartan", "Enalapril", "Lisinopril",
    "Atenolol", "Bisoprolol", "Carvedilol", "Doxazosin", "Diltiazem",
    # --- スタチン・脂質 ---
    "Atorvastatin", "Rosuvastatin", "Pravastatin", "Pitavastatin", "Simvastatin",
    "Ezetimibe", "Bezafibrate", "Fenofibrate",
    # --- 糖尿病 ---
    "Metformin", "Glimepiride", "Glibenclamide", "Pioglitazone", "Sitagliptin",
    "Vildagliptin", "Alogliptin", "Linagliptin", "Teneligliptin", "Empagliflozin",
    "Dapagliflozin", "Canagliflozin", "Luseogliflozin",
    "Insulin glargine", "Insulin aspart", "Liraglutide", "Dulaglutide",
    # --- 消化器 ---
    "Omeprazole", "Lansoprazole", "Rabeprazole", "Esomeprazole", "Vonoprazan",
    "Famotidine", "Ranitidine", "Teprenone", "Rebamipide", "Mosapride",
    "Metoclopramide", "Domperidone", "Sennoside",
    # --- 抗血栓 ---
    "Warfarin", "Clopidogrel", "Prasugrel", "Apixaban", "Rivaroxaban",
    "Edoxaban", "Dabigatran", "Cilostazol", "Ticlopidine",
    # --- 抗菌薬 ---
    "Amoxicillin", "Ampicillin", "Cefcapene pivoxil", "Cefditoren pivoxil",
    "Cephalexin", "Azithromycin", "Clarithromycin", "Erythromycin",
    "Levofloxacin", "Ciprofloxacin", "Moxifloxacin",
    "Minocycline", "Doxycycline", "Sulfamethoxazole",
    "Vancomycin", "Meropenem", "Metronidazole",
    # --- 精神・神経 ---
    "Diazepam", "Etizolam", "Alprazolam", "Lorazepam", "Clonazepam",
    "Zolpidem", "Zopiclone", "Eszopiclone", "Suvorexant", "Lemborexant",
    "Ramelteon",
    "Sertraline", "Paroxetine", "Escitalopram", "Fluvoxamine",
    "Duloxetine", "Venlafaxine", "Mirtazapine", "Amitriptyline",
    "Aripiprazole", "Olanzapine", "Quetiapine", "Risperidone", "Haloperidol",
    "Lithium carbonate", "Valproic acid", "Carbamazepine", "Lamotrigine",
    "Levodopa", "Pramipexole", "Ropinirole", "Donepezil",
    # --- 呼吸器 ---
    "Montelukast", "Pranlukast", "Theophylline",
    "Budesonide", "Fluticasone", "Beclomethasone",
    "Tiotropium", "Salmeterol", "Formoterol",
    "Codeine", "Dextromethorphan",
    # --- アレルギー ---
    "Fexofenadine", "Cetirizine", "Loratadine", "Desloratadine",
    "Olopatadine", "Bepotastine", "Bilastine", "Epinastine",
    "Prednisolone", "Dexamethasone", "Betamethasone",
    # --- 泌尿器 ---
    "Tamsulosin", "Silodosin", "Naftopidil", "Dutasteride", "Finasteride",
    "Mirabegron", "Solifenacin", "Tadalafil",
    # --- 骨粗鬆症 ---
    "Alendronate", "Risedronate", "Denosumab", "Eldecalcitol", "Alfacalcidol",
    # --- 甲状腺 ---
    "Levothyroxine", "Thiamazole",
    # --- 痛風 ---
    "Allopurinol", "Febuxostat", "Colchicine", "Benzbromarone",
    # --- 抗ウイルス ---
    "Acyclovir", "Valacyclovir", "Oseltamivir", "Baloxavir marboxil",
    # --- 抗真菌 ---
    "Fluconazole", "Itraconazole", "Terbinafine",
    # --- 免疫抑制 ---
    "Tacrolimus", "Cyclosporine", "Mycophenolate mofetil",
    # --- 主要OTC ---
    "Diphenhydramine", "Chlorpheniramine", "Caffeine",
    "Loperamide", "Bismuth",
    # --- その他 ---
    "Magnesium oxide", "Potassium chloride", "Furosemide",
    "Hydrochlorothiazide", "Spironolactone", "Eplerenone",
    "Digoxin", "Amiodarone", "Nicorandil",
    "Gabapentin", "Pregabalin", "Tramadol",
    "Morphine", "Fentanyl", "Oxycodone",
]


def search_kegg_drug(name: str) -> list[dict]:
    """KEGGで薬名を検索してIDと名前を返す"""
    time.sleep(RATE_LIMIT)
    url = f"{KEGG_BASE}/find/drug/{name}"
    r = requests.get(url)
    if r.status_code != 200 or not r.text.strip():
        return []
    results = []
    for line in r.text.strip().split('\n'):
        parts = line.split('\t', 1)
        if len(parts) == 2:
            drug_id = parts[0].replace('dr:', '')
            drug_name = parts[1]
            results.append({'kegg_id': drug_id, 'name': drug_name})
    return results


def get_drug_detail(kegg_id: str) -> dict:
    """KEGGから薬の詳細情報を取得"""
    time.sleep(RATE_LIMIT)
    url = f"{KEGG_BASE}/get/{kegg_id}"
    r = requests.get(url)
    if r.status_code != 200:
        return {}

    info = {'kegg_id': kegg_id}
    current_field = ''
    current_value = []

    for line in r.text.split('\n'):
        if line.startswith('///'):
            break
        if line and not line[0].isspace():
            # Save previous field
            if current_field and current_value:
                info[current_field] = '\n'.join(current_value)
            # New field
            parts = line.split(None, 1)
            current_field = parts[0].lower()
            current_value = [parts[1]] if len(parts) > 1 else []
        elif line.startswith(' ') and current_field:
            current_value.append(line.strip())

    # Save last field
    if current_field and current_value:
        info[current_field] = '\n'.join(current_value)

    return info


def parse_drug_info(raw: dict) -> dict:
    """生のKEGGデータを構造化"""
    info = {
        'kegg_id': raw.get('kegg_id', ''),
        'name_en': '',
        'name_ja': '',
        'names_alt': [],
        'formula': raw.get('formula', ''),
        'efficacy': raw.get('efficacy', ''),
        'target': raw.get('target', ''),
        'metabolism': raw.get('metabolism', ''),
        'therapeutic_category': '',
        'atc_code': '',
        'drug_class': [],
        'cyp_enzymes': [],
    }

    # Parse NAME field
    name_raw = raw.get('name', '')
    if name_raw:
        names = [n.strip() for n in name_raw.split(';')]
        info['name_en'] = names[0] if names else ''
        info['names_alt'] = names[1:] if len(names) > 1 else []

    # Parse REMARK for therapeutic category and ATC code
    remark = raw.get('remark', '')
    tc_match = re.search(r'Therapeutic category:\s*(\d+)', remark)
    if tc_match:
        info['therapeutic_category'] = tc_match.group(1)
    atc_match = re.search(r'ATC code:\s*(\S+)', remark)
    if atc_match:
        info['atc_code'] = atc_match.group(1)

    # Parse CLASS for drug groups
    class_raw = raw.get('class', '')
    if class_raw:
        for line in class_raw.split('\n'):
            line = line.strip()
            if line.startswith('DG'):
                # Drug group code
                m = re.match(r'DG\d+\s+(.+)', line)
                if m:
                    info['drug_class'].append(m.group(1).strip())
            elif line and not line.startswith('DG'):
                info['drug_class'].append(line)

    # Parse METABOLISM for CYP enzymes
    metabolism = raw.get('metabolism', '')
    cyp_pattern = re.findall(r'CYP\w+', metabolism)
    info['cyp_enzymes'] = list(set(cyp_pattern))

    return info


def main():
    print(f"=== Building initial drug list ({len(PRIORITY_DRUGS_EN)} target drugs) ===\n")

    # Load existing KEGG JP drugs for reference
    jp_drugs_file = DATA_DIR / "kegg_jp_drugs.json"
    if jp_drugs_file.exists():
        with open(jp_drugs_file) as f:
            jp_drugs = json.load(f)
        kegg_names = {d['kegg_id']: d['name'] for d in jp_drugs}
        print(f"Loaded {len(kegg_names)} JP drugs from KEGG BRITE")
    else:
        kegg_names = {}

    # Search each drug name in KEGG
    drug_list = []
    not_found = []
    search_cache = {}

    for i, name in enumerate(PRIORITY_DRUGS_EN):
        print(f"[{i+1}/{len(PRIORITY_DRUGS_EN)}] Searching: {name}...", end=' ')

        results = search_kegg_drug(name)

        if not results:
            print("NOT FOUND")
            not_found.append(name)
            continue

        # Pick best match (prefer JP-approved, shortest ID)
        best = results[0]
        for r in results:
            # Prefer exact match in name
            if name.lower() in r['name'].lower().split(';')[0].lower():
                best = r
                break

        search_cache[name] = best
        print(f"→ {best['kegg_id']} ({best['name'][:50]})")

    print(f"\nFound: {len(search_cache)}/{len(PRIORITY_DRUGS_EN)}")
    print(f"Not found: {len(not_found)}: {not_found}")

    # Save intermediate result
    with open(DATA_DIR / "drug_search_results.json", "w", encoding='utf-8') as f:
        json.dump(search_cache, f, ensure_ascii=False, indent=2)

    # Now fetch details for each found drug
    print(f"\n=== Fetching detailed info for {len(search_cache)} drugs ===\n")

    detailed_drugs = []
    for i, (name, match) in enumerate(search_cache.items()):
        kegg_id = match['kegg_id']
        print(f"[{i+1}/{len(search_cache)}] Getting details: {kegg_id} ({name})...", end=' ')

        raw = get_drug_detail(kegg_id)
        if raw:
            parsed = parse_drug_info(raw)
            parsed['search_name'] = name  # Original search term
            detailed_drugs.append(parsed)
            print(f"OK (CYP: {parsed['cyp_enzymes']}, TC: {parsed['therapeutic_category']})")
        else:
            print("FAILED")

    # Save final drug list
    output_file = DATA_DIR / "initial_drugs.json"
    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(detailed_drugs, f, ensure_ascii=False, indent=2)

    print(f"\n=== Summary ===")
    print(f"Total drugs: {len(detailed_drugs)}")
    print(f"With CYP info: {sum(1 for d in detailed_drugs if d['cyp_enzymes'])}")
    print(f"With ATC code: {sum(1 for d in detailed_drugs if d['atc_code'])}")
    print(f"Saved to: {output_file}")


if __name__ == '__main__':
    main()
