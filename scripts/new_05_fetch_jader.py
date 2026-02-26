#!/usr/bin/env python3
"""
new_05_fetch_jader.py
JADER副作用データの処理（既存 03_fetch_jader.py のロジック再利用）。

JADER（Japanese Adverse Drug Event Report database）は厚労省の副作用報告DB。
手動DLが必要（PMDAサイト）→ data/jader_raw/ に配置。
未入手時はフォールバック（クラスベース副作用推定）を使用。

出力: data/adverse_effects_new.json
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
JADER_DIR = DATA_DIR / "jader_raw"
DRUG_MASTER = DATA_DIR / "drug_master.json"
OUTPUT = DATA_DIR / "adverse_effects_new.json"

# 薬効クラス → 副作用マッピング（03_fetch_jader.py由来）
CLASS_ADVERSE_EFFECTS = {
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
    "Antiepileptic": [
        {"name": "眠気", "name_en": "Somnolence", "frequency": "high"},
        {"name": "めまい", "name_en": "Dizziness", "frequency": "high"},
        {"name": "肝機能障害", "name_en": "Hepatic impairment", "frequency": "medium"},
        {"name": "皮膚障害", "name_en": "Skin disorder", "frequency": "medium"},
    ],
    "Immunosuppressant": [
        {"name": "感染症", "name_en": "Infection", "frequency": "high"},
        {"name": "腎機能障害", "name_en": "Renal impairment", "frequency": "high"},
        {"name": "肝機能障害", "name_en": "Hepatic impairment", "frequency": "medium"},
        {"name": "悪性腫瘍", "name_en": "Malignancy", "frequency": "low"},
    ],
    "Diuretic": [
        {"name": "電解質異常", "name_en": "Electrolyte imbalance", "frequency": "high"},
        {"name": "脱水", "name_en": "Dehydration", "frequency": "medium"},
        {"name": "低血圧", "name_en": "Hypotension", "frequency": "medium"},
    ],
    "Antithrombotic": [
        {"name": "出血", "name_en": "Hemorrhage", "frequency": "high"},
        {"name": "血小板減少", "name_en": "Thrombocytopenia", "frequency": "medium"},
    ],
    "Anticancer": [
        {"name": "骨髄抑制", "name_en": "Myelosuppression", "frequency": "high"},
        {"name": "悪心・嘔吐", "name_en": "Nausea/vomiting", "frequency": "high"},
        {"name": "脱毛", "name_en": "Alopecia", "frequency": "high"},
        {"name": "感染症", "name_en": "Infection", "frequency": "high"},
        {"name": "肝機能障害", "name_en": "Hepatic impairment", "frequency": "medium"},
    ],
}

# EN名 → クラス推定ルール
NAME_CLASS_RULES = [
    (r"statin$", "Statin"),
    (r"sartan$", "ARB"),
    (r"pril$", "ACE inhibitor"),
    (r"dipine$", "CCB"),
    (r"olol$", "Beta blocker"),
    (r"gliptin$", "DPP-4 inhibitor"),
    (r"gliflozin$", "SGLT2 inhibitor"),
    (r"prazole$", "PPI"),
    (r"(pam|lam|zepam|zolam)$", "Benzodiazepine"),
    (r"(oxetine|aline|ipran)$", "SSRI"),
    (r"floxacin$", "Fluoroquinolone"),
    (r"(thromycin|mycin)$", "Macrolide"),
    (r"(apine|idone|azole|pride)$", "Antipsychotic"),
    (r"(codone|phine|adol)$", "Opioid"),
    (r"(azepine|trigine|topiramate|amide)$", "Antiepileptic"),
    (r"(limus|prine|trexate)$", "Immunosuppressant"),
    (r"semide$", "Diuretic"),
    (r"(xaban|gatran|farin)$", "Anticoagulant"),
    (r"(grelat|dogrel|agrelor|stazol)$", "Antithrombotic"),
    (r"(platin|taxel|rubicin|abine)$", "Anticancer"),
    (r"(mab|zumab|ximab)$", "Anticancer"),  # rough
    (r"(tinib|rafenib|zomib)$", "Anticancer"),
    (r"(profen|fenac|oxicam)$", "NSAID"),
]


def classify_drug(name_en: str) -> list[str]:
    """英名から薬効クラスを推定"""
    classes = []
    name_lower = name_en.lower()
    for pattern, cls in NAME_CLASS_RULES:
        if re.search(pattern, name_lower):
            classes.append(cls)
    return classes


def generate_adverse_effects(drugs: list[dict]) -> list[dict]:
    """Drug masterからクラスベース副作用を生成"""
    results = []

    for drug in drugs:
        drug_id = drug["id"]
        name_en = drug.get("name_en", "")

        classes = classify_drug(name_en)

        # Collect unique adverse effects
        seen = set()
        effects = []
        for cls in classes:
            for ae in CLASS_ADVERSE_EFFECTS.get(cls, []):
                if ae["name"] not in seen:
                    seen.add(ae["name"])
                    effects.append(ae.copy())

        # Default if no class match: general effects
        if not effects:
            effects = [
                {"name": "肝機能障害", "name_en": "Hepatic impairment", "frequency": "low"},
                {"name": "過敏症", "name_en": "Hypersensitivity", "frequency": "low"},
            ]

        results.append({
            "drug_id": drug_id,
            "name_en": name_en,
            "drug_classes": classes,
            "adverse_effects": effects,
        })

    return results


def main():
    if not DRUG_MASTER.exists():
        print(f"ERROR: {DRUG_MASTER} not found. Run new_03 first.")
        return

    with open(DRUG_MASTER, encoding="utf-8") as f:
        master = json.load(f)

    drugs = master["drugs"]
    print(f"Drug master: {len(drugs)} 薬")

    # Check if JADER raw data exists
    has_jader = JADER_DIR.exists() and (JADER_DIR / "drug.csv").exists()

    if has_jader:
        print("JADER生データを検出。JADER処理を実行...")
        # Future: implement full JADER processing
        print("（未実装 - フォールバック使用）")

    print("クラスベース副作用推定を使用")
    results = generate_adverse_effects(drugs)

    output = {
        "source": "Class-based estimation (JADER fallback)",
        "total_drugs": len(results),
        "adverse_effects": results,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Stats
    with_ae = sum(1 for r in results if r["adverse_effects"])
    total_ae = sum(len(r["adverse_effects"]) for r in results)
    ae_names = Counter()
    for r in results:
        for ae in r["adverse_effects"]:
            ae_names[ae["name"]] += 1

    print(f"\n=== 副作用統計 ===")
    print(f"副作用付き薬: {with_ae}/{len(results)} ({with_ae/len(results)*100:.1f}%)")
    print(f"副作用エントリ総数: {total_ae}")
    print(f"ユニーク副作用名: {len(ae_names)}")
    print(f"\nTop 10 副作用:")
    for name, cnt in ae_names.most_common(10):
        print(f"  {name}: {cnt} 薬")
    print(f"\n保存: {OUTPUT}")


if __name__ == "__main__":
    main()
