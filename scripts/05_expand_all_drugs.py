#!/usr/bin/env python3
"""
Step 5: KEGG日本承認薬2,600品目を全取得
- KEGG BRITE階層から全薬IDを取得済み（kegg_jp_drugs.json）
- 各薬の詳細情報をバッチ取得
- 日本語名をカタカナ変換テーブル + 手動マッピングで付与
- DDIをバッチ取得
- 最終グラフデータを生成
"""

import json
import re
import time
import sys
from pathlib import Path
from collections import defaultdict, Counter

import requests

DATA_DIR = Path(__file__).parent.parent / "data"
KEGG_BASE = "https://rest.kegg.jp"
RATE_LIMIT = 0.34

# ===== 日本語名マッピング（主要薬 + カタカナ変換ルール） =====

# 手動マッピング（高頻度薬・変則的な読みのもの）
MANUAL_JA_NAMES = {
    "Aspirin": "アスピリン",
    "Acetaminophen": "アセトアミノフェン",
    "Morphine": "モルヒネ",
    "Codeine": "コデイン",
    "Caffeine": "カフェイン",
    "Insulin": "インスリン",
    "Heparin": "ヘパリン",
    "Warfarin": "ワルファリン",
    "Digoxin": "ジゴキシン",
    "Epinephrine": "エピネフリン",
    "Adrenaline": "アドレナリン",
    "Norepinephrine": "ノルエピネフリン",
    "Dopamine": "ドパミン",
    "Serotonin": "セロトニン",
    "Atropine": "アトロピン",
    "Lidocaine": "リドカイン",
    "Procaine": "プロカイン",
    "Cocaine": "コカイン",
    "Quinine": "キニーネ",
    "Quinidine": "キニジン",
    "Theophylline": "テオフィリン",
    "Penicillin": "ペニシリン",
    "Ampicillin": "アンピシリン",
    "Amoxicillin": "アモキシシリン",
    "Erythromycin": "エリスロマイシン",
    "Tetracycline": "テトラサイクリン",
    "Streptomycin": "ストレプトマイシン",
    "Gentamicin": "ゲンタマイシン",
    "Vancomycin": "バンコマイシン",
    "Chloramphenicol": "クロラムフェニコール",
    "Methotrexate": "メトトレキサート",
    "Cyclophosphamide": "シクロホスファミド",
    "Cisplatin": "シスプラチン",
    "Doxorubicin": "ドキソルビシン",
    "Vincristine": "ビンクリスチン",
    "Prednisolone": "プレドニゾロン",
    "Dexamethasone": "デキサメタゾン",
    "Hydrocortisone": "ヒドロコルチゾン",
    "Testosterone": "テストステロン",
    "Estradiol": "エストラジオール",
    "Progesterone": "プロゲステロン",
    "Oxytocin": "オキシトシン",
    "Vasopressin": "バソプレシン",
    "Thyroxine": "チロキシン",
    "Levothyroxine": "レボチロキシン",
    "Propranolol": "プロプラノロール",
    "Atenolol": "アテノロール",
    "Metoprolol": "メトプロロール",
    "Bisoprolol": "ビソプロロール",
    "Carvedilol": "カルベジロール",
    "Amlodipine": "アムロジピン",
    "Nifedipine": "ニフェジピン",
    "Verapamil": "ベラパミル",
    "Diltiazem": "ジルチアゼム",
    "Enalapril": "エナラプリル",
    "Lisinopril": "リシノプリル",
    "Captopril": "カプトプリル",
    "Losartan": "ロサルタン",
    "Valsartan": "バルサルタン",
    "Candesartan": "カンデサルタン",
    "Olmesartan": "オルメサルタン",
    "Telmisartan": "テルミサルタン",
    "Azilsartan": "アジルサルタン",
    "Furosemide": "フロセミド",
    "Spironolactone": "スピロノラクトン",
    "Hydrochlorothiazide": "ヒドロクロロチアジド",
    "Atorvastatin": "アトルバスタチン",
    "Rosuvastatin": "ロスバスタチン",
    "Simvastatin": "シンバスタチン",
    "Pravastatin": "プラバスタチン",
    "Pitavastatin": "ピタバスタチン",
    "Lovastatin": "ロバスタチン",
    "Fluvastatin": "フルバスタチン",
    "Metformin": "メトホルミン",
    "Glibenclamide": "グリベンクラミド",
    "Glimepiride": "グリメピリド",
    "Pioglitazone": "ピオグリタゾン",
    "Sitagliptin": "シタグリプチン",
    "Omeprazole": "オメプラゾール",
    "Lansoprazole": "ランソプラゾール",
    "Rabeprazole": "ラベプラゾール",
    "Esomeprazole": "エソメプラゾール",
    "Famotidine": "ファモチジン",
    "Ranitidine": "ラニチジン",
    "Diazepam": "ジアゼパム",
    "Alprazolam": "アルプラゾラム",
    "Lorazepam": "ロラゼパム",
    "Midazolam": "ミダゾラム",
    "Zolpidem": "ゾルピデム",
    "Haloperidol": "ハロペリドール",
    "Chlorpromazine": "クロルプロマジン",
    "Risperidone": "リスペリドン",
    "Olanzapine": "オランザピン",
    "Quetiapine": "クエチアピン",
    "Aripiprazole": "アリピプラゾール",
    "Sertraline": "セルトラリン",
    "Paroxetine": "パロキセチン",
    "Fluoxetine": "フルオキセチン",
    "Escitalopram": "エスシタロプラム",
    "Duloxetine": "デュロキセチン",
    "Mirtazapine": "ミルタザピン",
    "Amitriptyline": "アミトリプチリン",
    "Carbamazepine": "カルバマゼピン",
    "Valproic acid": "バルプロ酸",
    "Lamotrigine": "ラモトリギン",
    "Phenytoin": "フェニトイン",
    "Levodopa": "レボドパ",
    "Donepezil": "ドネペジル",
    "Tacrolimus": "タクロリムス",
    "Cyclosporine": "シクロスポリン",
    "Ibuprofen": "イブプロフェン",
    "Loxoprofen": "ロキソプロフェン",
    "Diclofenac": "ジクロフェナク",
    "Celecoxib": "セレコキシブ",
    "Indomethacin": "インドメタシン",
    "Naproxen": "ナプロキセン",
    "Tramadol": "トラマドール",
    "Fentanyl": "フェンタニル",
    "Oxycodone": "オキシコドン",
    "Pregabalin": "プレガバリン",
    "Gabapentin": "ガバペンチン",
    "Acyclovir": "アシクロビル",
    "Oseltamivir": "オセルタミビル",
    "Fluconazole": "フルコナゾール",
    "Itraconazole": "イトラコナゾール",
    "Clarithromycin": "クラリスロマイシン",
    "Azithromycin": "アジスロマイシン",
    "Levofloxacin": "レボフロキサシン",
    "Ciprofloxacin": "シプロフロキサシン",
    "Meropenem": "メロペネム",
    "Clopidogrel": "クロピドグレル",
    "Apixaban": "アピキサバン",
    "Rivaroxaban": "リバーロキサバン",
    "Edoxaban": "エドキサバン",
    "Dabigatran": "ダビガトラン",
    "Montelukast": "モンテルカスト",
    "Fexofenadine": "フェキソフェナジン",
    "Cetirizine": "セチリジン",
    "Loratadine": "ロラタジン",
    "Olopatadine": "オロパタジン",
    "Tamsulosin": "タムスロシン",
    "Allopurinol": "アロプリノール",
    "Febuxostat": "フェブキソスタット",
    "Colchicine": "コルヒチン",
    "Alendronate": "アレンドロン酸",
    "Nitroglycerin": "ニトログリセリン",
    "Amiodarone": "アミオダロン",
    "Magnesium oxide": "酸化マグネシウム",
    "Lithium carbonate": "炭酸リチウム",
    "Potassium chloride": "塩化カリウム",
    "Sodium chloride": "塩化ナトリウム",
    "Calcium carbonate": "�ite酸カルシウム",
    "Glucose": "ブドウ糖",
    "Water": "精製水",
    "Oxygen": "酸素",
    "Carbon dioxide": "二酸化炭素",
}

# カタカナ変換テーブル（英語薬名の語尾パターン → カタカナ）
SUFFIX_RULES = [
    # 語尾変換ルール（長い順に適用）
    ("prazole", "プラゾール"),
    ("statin", "スタチン"),
    ("sartan", "サルタン"),
    ("dipine", "ジピン"),
    ("olol", "ロール"),
    ("pril", "プリル"),
    ("floxacin", "フロキサシン"),
    ("mycin", "マイシン"),
    ("cycline", "サイクリン"),
    ("cillin", "シリン"),
    ("azole", "アゾール"),
    ("navir", "ナビル"),
    ("vudine", "ブジン"),
    ("mab", "マブ"),
    ("nib", "ニブ"),
    ("lib", "リブ"),
    ("tide", "チド"),
    ("pine", "ピン"),
    ("pam", "パム"),
    ("lam", "ラム"),
    ("done", "ドン"),
    ("sone", "ゾン"),
    ("lone", "ロン"),
    ("tine", "チン"),
    ("dine", "ジン"),
    ("mine", "ミン"),
    ("zine", "ジン"),
    ("rine", "リン"),
    ("line", "リン"),
    ("ine", "イン"),
    ("ide", "イド"),
    ("ate", "エート"),
    ("ose", "オース"),
    ("ol", "オール"),
    ("il", "イル"),
    ("al", "アール"),
    ("an", "アン"),
    ("um", "ウム"),
    ("in", "イン"),
    ("on", "オン"),
    ("en", "エン"),
    ("er", "エル"),
    ("ax", "アクス"),
    ("ix", "イクス"),
    ("ox", "オクス"),
]

# 英語→カタカナ 音素変換（簡易版）
PHONEME_MAP = {
    "ph": "フ", "th": "ス", "ch": "チ", "sh": "シ",
    "ck": "ク", "qu": "ク",
    "a": "ア", "e": "エ", "i": "イ", "o": "オ", "u": "ウ",
    "b": "ブ", "c": "ク", "d": "ド", "f": "フ", "g": "グ",
    "h": "フ", "j": "ジ", "k": "ク", "l": "ル", "m": "ム",
    "n": "ン", "p": "プ", "r": "ル", "s": "ス", "t": "ト",
    "v": "ブ", "w": "ウ", "x": "クス", "y": "イ", "z": "ズ",
}


def english_to_katakana(name: str) -> str:
    """英語薬名 → カタカナ変換（簡易）"""
    # 手動マッピングチェック
    # nameの最初の単語（括弧前）で検索
    base = name.split('(')[0].split(';')[0].strip()
    for key, val in MANUAL_JA_NAMES.items():
        if key.lower() == base.lower():
            return val

    # 部分一致（先頭一致）
    for key, val in MANUAL_JA_NAMES.items():
        if base.lower().startswith(key.lower()):
            return val

    return ""  # 自動変換は精度が低いので空文字を返す


def get_drug_detail(kegg_id: str) -> dict:
    """KEGGから薬の詳細情報を取得"""
    time.sleep(RATE_LIMIT)
    url = f"{KEGG_BASE}/get/{kegg_id}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return {}
    except Exception:
        return {}

    info = {'kegg_id': kegg_id}
    current_field = ''
    current_value = []

    for line in r.text.split('\n'):
        if line.startswith('///'):
            break
        if line and not line[0].isspace():
            if current_field and current_value:
                info[current_field] = '\n'.join(current_value)
            parts = line.split(None, 1)
            current_field = parts[0].lower()
            current_value = [parts[1]] if len(parts) > 1 else []
        elif line.startswith(' ') and current_field:
            current_value.append(line.strip())

    if current_field and current_value:
        info[current_field] = '\n'.join(current_value)

    return info


def parse_drug_info(raw: dict, brite_info: dict = None) -> dict:
    """KEGGデータを構造化"""
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

    # Parse NAME
    name_raw = raw.get('name', '')
    if name_raw:
        names = [n.strip() for n in name_raw.split(';')]
        info['name_en'] = names[0] if names else ''
        info['names_alt'] = names[1:] if len(names) > 1 else []

    # Japanese name
    search_name = info['name_en'].split('(')[0].strip()
    info['search_name'] = search_name
    info['name_ja'] = english_to_katakana(info['name_en'])

    # Parse REMARK
    remark = raw.get('remark', '')
    tc_match = re.search(r'Therapeutic category:\s*(\d+)', remark)
    if tc_match:
        info['therapeutic_category'] = tc_match.group(1)
    atc_match = re.search(r'ATC code:\s*(\S+)', remark)
    if atc_match:
        info['atc_code'] = atc_match.group(1)

    # Use BRITE category if available
    if brite_info and not info['therapeutic_category']:
        info['therapeutic_category'] = brite_info.get('category_code', '')

    # Parse CLASS
    class_raw = raw.get('class', '')
    if class_raw:
        for line in class_raw.split('\n'):
            line = line.strip()
            if line.startswith('DG'):
                m = re.match(r'DG\d+\s+(.+)', line)
                if m:
                    info['drug_class'].append(m.group(1).strip())
            elif line and not line.startswith('DG'):
                info['drug_class'].append(line)

    # Parse METABOLISM for CYP
    metabolism = raw.get('metabolism', '')
    cyp_pattern = re.findall(r'CYP\w+', metabolism)
    info['cyp_enzymes'] = list(set(cyp_pattern))

    return info


def fetch_ddi(kegg_id: str) -> list[dict]:
    """1薬のDDIを取得"""
    time.sleep(RATE_LIMIT)
    try:
        r = requests.get(f"{KEGG_BASE}/ddi/{kegg_id}", timeout=15)
        if r.status_code != 200 or not r.text.strip():
            return []
    except Exception:
        return []

    interactions = []
    for line in r.text.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) >= 3:
            drug1 = parts[0].replace('dr:', '')
            drug2 = parts[1].replace('dr:', '')
            severity = parts[2]
            mechanism = parts[3] if len(parts) > 3 else ''
            # Normalize severity
            if ',' in severity:
                severity = 'CI' if 'CI' in severity else severity.split(',')[0]
            interactions.append({
                'drug1': drug1, 'drug2': drug2,
                'severity': severity, 'mechanism': mechanism,
            })
    return interactions


def main():
    # Load BRITE drug list
    brite_file = DATA_DIR / "kegg_jp_drugs.json"
    with open(brite_file) as f:
        brite_drugs = json.load(f)

    # Get unique drug IDs
    seen_ids = set()
    unique_drugs = []
    brite_map = {}
    for d in brite_drugs:
        kid = d['kegg_id']
        if kid not in seen_ids:
            seen_ids.add(kid)
            unique_drugs.append(d)
            brite_map[kid] = d

    print(f"=== Total unique drugs to process: {len(unique_drugs)} ===\n")

    # Load existing data to skip already fetched
    existing_file = DATA_DIR / "all_drugs_detail.json"
    existing = {}
    if existing_file.exists():
        with open(existing_file) as f:
            for d in json.load(f):
                existing[d['kegg_id']] = d
        print(f"Already fetched: {len(existing)} drugs (resuming)\n")

    # Phase 1: Fetch details
    all_drugs = list(existing.values())
    to_fetch = [d for d in unique_drugs if d['kegg_id'] not in existing]

    print(f"Phase 1: Fetching details for {len(to_fetch)} new drugs...\n")

    for i, drug in enumerate(to_fetch):
        kegg_id = drug['kegg_id']
        print(f"[{i+1}/{len(to_fetch)}] {kegg_id}...", end=' ', flush=True)

        raw = get_drug_detail(kegg_id)
        if raw:
            parsed = parse_drug_info(raw, brite_map.get(kegg_id))
            all_drugs.append(parsed)
            print(f"OK - {parsed.get('name_ja', '') or parsed.get('name_en', '')[:30]}")
        else:
            print("SKIP")

        # Save progress every 100 drugs
        if (i + 1) % 100 == 0:
            with open(existing_file, "w", encoding='utf-8') as f:
                json.dump(all_drugs, f, ensure_ascii=False, indent=2)
            print(f"  [Progress saved: {len(all_drugs)} drugs]\n")

    # Final save
    with open(existing_file, "w", encoding='utf-8') as f:
        json.dump(all_drugs, f, ensure_ascii=False, indent=2)

    drug_ids = {d['kegg_id'] for d in all_drugs}
    with_ja = sum(1 for d in all_drugs if d.get('name_ja'))
    print(f"\n=== Phase 1 Complete ===")
    print(f"Total drugs: {len(all_drugs)}")
    print(f"With Japanese name: {with_ja} ({100*with_ja/len(all_drugs):.1f}%)")

    # Phase 2: Fetch DDI (internal only)
    print(f"\n=== Phase 2: Fetching DDI ===\n")

    ddi_cache_file = DATA_DIR / "all_ddi_cache.json"
    ddi_cache = {}
    if ddi_cache_file.exists():
        with open(ddi_cache_file) as f:
            ddi_cache = json.load(f)
        print(f"DDI cache: {len(ddi_cache)} drugs already fetched\n")

    to_fetch_ddi = [d for d in all_drugs if d['kegg_id'] not in ddi_cache]
    print(f"DDI to fetch: {len(to_fetch_ddi)} drugs\n")

    for i, drug in enumerate(to_fetch_ddi):
        kegg_id = drug['kegg_id']
        print(f"[{i+1}/{len(to_fetch_ddi)}] DDI {kegg_id}...", end=' ', flush=True)

        interactions = fetch_ddi(kegg_id)
        # Only keep internal interactions (both drugs in our list)
        internal = [ix for ix in interactions if ix['drug1'] in drug_ids and ix['drug2'] in drug_ids]
        ddi_cache[kegg_id] = internal
        print(f"{len(interactions)} total, {len(internal)} internal")

        if (i + 1) % 100 == 0:
            with open(ddi_cache_file, "w", encoding='utf-8') as f:
                json.dump(ddi_cache, f, ensure_ascii=False, indent=2)
            print(f"  [DDI progress saved]\n")

    with open(ddi_cache_file, "w", encoding='utf-8') as f:
        json.dump(ddi_cache, f, ensure_ascii=False, indent=2)

    # Deduplicate all DDI
    seen = set()
    all_ddi = []
    for interactions in ddi_cache.values():
        for ix in interactions:
            pair = tuple(sorted([ix['drug1'], ix['drug2']]))
            key = (pair[0], pair[1], ix['severity'])
            if key not in seen:
                seen.add(key)
                all_ddi.append(ix)

    ddi_file = DATA_DIR / "ddi_internal.json"
    with open(ddi_file, "w", encoding='utf-8') as f:
        json.dump(all_ddi, f, ensure_ascii=False, indent=2)

    print(f"\n=== Phase 2 Complete ===")
    print(f"Total unique internal DDI: {len(all_ddi)}")
    ci_count = sum(1 for d in all_ddi if d['severity'] == 'CI')
    print(f"  CI: {ci_count}, P: {len(all_ddi) - ci_count}")

    # Phase 3: Update initial_drugs.json with all drugs
    with open(DATA_DIR / "initial_drugs.json", "w", encoding='utf-8') as f:
        json.dump(all_drugs, f, ensure_ascii=False, indent=2)

    print(f"\n=== All done! ===")
    print(f"Run 04_build_graph_data.py to rebuild graph.")


if __name__ == '__main__':
    main()
