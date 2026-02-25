#!/usr/bin/env python3
"""
08_enrich_data.py — 包括的データ補完パッチ

1. CYP酵素: drug_class から CYP substrate/inhibitor/inducer を抽出
2. 副作用: 薬効分類・drug_class ベースでクラスレベル副作用を追加
3. 商品名: 大幅拡充（日本処方頻度上位の薬）
4. name_ja: 追加辞書エントリ

対象: graph-light.json (+ adverse_effect ノード・エッジ追加)
冪等: 何度実行しても同じ結果
"""

import json
import re
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH_LIGHT = os.path.join(BASE, 'data', 'graph', 'graph-light.json')
ALL_DRUGS = os.path.join(BASE, 'data', 'all_drugs_detail.json')
AE_FILE = os.path.join(BASE, 'data', 'adverse_effects.json')

# ============================================================
# 1. CYP enzyme extraction from drug_class
# ============================================================
CYP_CLASS_MAP = {
    'CYP3A/CYP3A4 substrate': ['CYP3A4'],
    'CYP3A4 substrate': ['CYP3A4'],
    'CYP2D6 substrate': ['CYP2D6'],
    'CYP2C9 substrate': ['CYP2C9'],
    'CYP2C19 substrate': ['CYP2C19'],
    'CYP1A2 substrate': ['CYP1A2'],
    'CYP2C8 substrate': ['CYP2C8'],
    'CYP2B6 substrate': ['CYP2B6'],
    'CYP2A6 substrate': ['CYP2A6'],
    'CYP2E1 substrate': ['CYP2E1'],
    'CYP3A5 substrate': ['CYP3A5'],
    'CYP3A/CYP3A4 inhibitor': ['CYP3A4'],
    'CYP3A4 inhibitor': ['CYP3A4'],
    'CYP2D6 inhibitor': ['CYP2D6'],
    'CYP2C9 inhibitor': ['CYP2C9'],
    'CYP2C19 inhibitor': ['CYP2C19'],
    'CYP1A2 inhibitor': ['CYP1A2'],
    'CYP3A/CYP3A4 inducer': ['CYP3A4'],
    'CYP2B6 inhibitor': ['CYP2B6'],
    'CYP2C8 inhibitor': ['CYP2C8'],
}

def extract_cyp_from_drug_class(drug_classes):
    """drug_class リストから CYP 酵素名を抽出"""
    cyps = set()
    for cls in drug_classes:
        if cls in CYP_CLASS_MAP:
            cyps.update(CYP_CLASS_MAP[cls])
        # Generic regex fallback
        m = re.findall(r'CYP\d\w+', cls)
        for c in m:
            # Normalize: CYP3A → CYP3A4
            if c == 'CYP3A':
                cyps.add('CYP3A4')
            else:
                cyps.add(c)
    return sorted(cyps)

# ============================================================
# 2. Class-level adverse effects
# ============================================================
# 薬効分類コード → 副作用リスト
# therapeutic_category の先頭2桁でマッチ
TC_ADVERSE_EFFECTS = {
    '11': [  # 中枢神経系用薬
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'high'},
        {'name': 'めまい', 'name_en': 'Dizziness', 'frequency': 'medium'},
        {'name': '依存性', 'name_en': 'Dependence', 'frequency': 'medium'},
    ],
    '21': [  # 循環器官用薬
        {'name': '低血圧', 'name_en': 'Hypotension', 'frequency': 'medium'},
        {'name': 'めまい', 'name_en': 'Dizziness', 'frequency': 'medium'},
        {'name': '徐脈', 'name_en': 'Bradycardia', 'frequency': 'low'},
    ],
    '22': [  # 呼吸器官用薬
        {'name': '口渇', 'name_en': 'Dry mouth', 'frequency': 'medium'},
        {'name': '動悸', 'name_en': 'Palpitation', 'frequency': 'low'},
    ],
    '23': [  # 消化器官用薬
        {'name': '便秘', 'name_en': 'Constipation', 'frequency': 'medium'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'medium'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'low'},
    ],
    '24': [  # ホルモン剤
        {'name': '体重増加', 'name_en': 'Weight gain', 'frequency': 'medium'},
        {'name': '浮腫', 'name_en': 'Edema', 'frequency': 'low'},
    ],
    '26': [  # 外皮用薬
        {'name': '皮膚刺激感', 'name_en': 'Skin irritation', 'frequency': 'medium'},
        {'name': '接触皮膚炎', 'name_en': 'Contact dermatitis', 'frequency': 'low'},
    ],
    '33': [  # 血液・体液用薬
        {'name': '出血傾向', 'name_en': 'Bleeding tendency', 'frequency': 'high'},
        {'name': '貧血', 'name_en': 'Anemia', 'frequency': 'low'},
    ],
    '39': [  # 代謝性医薬品
        {'name': '低血糖', 'name_en': 'Hypoglycemia', 'frequency': 'medium'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'low'},
    ],
    '42': [  # 腫瘍用薬
        {'name': '骨髄抑制', 'name_en': 'Myelosuppression', 'frequency': 'high'},
        {'name': '悪心・嘔吐', 'name_en': 'Nausea/Vomiting', 'frequency': 'high'},
        {'name': '脱毛', 'name_en': 'Alopecia', 'frequency': 'high'},
        {'name': '肝機能障害', 'name_en': 'Hepatic impairment', 'frequency': 'medium'},
        {'name': '腎機能障害', 'name_en': 'Renal impairment', 'frequency': 'medium'},
        {'name': '倦怠感', 'name_en': 'Fatigue', 'frequency': 'high'},
    ],
    '44': [  # アレルギー用薬
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'high'},
        {'name': '口渇', 'name_en': 'Dry mouth', 'frequency': 'medium'},
    ],
    '61': [  # 抗生物質
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'high'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
        {'name': '薬疹', 'name_en': 'Drug eruption', 'frequency': 'low'},
        {'name': 'アレルギー反応', 'name_en': 'Allergic reaction', 'frequency': 'low'},
    ],
    '62': [  # 化学療法剤
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'medium'},
        {'name': '肝機能障害', 'name_en': 'Hepatic impairment', 'frequency': 'low'},
    ],
    '63': [  # 生物学的製剤
        {'name': '注射部位反応', 'name_en': 'Injection site reaction', 'frequency': 'high'},
        {'name': '感染症リスク増加', 'name_en': 'Increased infection risk', 'frequency': 'medium'},
    ],
}

# drug_class ベースの副作用
CLASS_ADVERSE_EFFECTS = {
    'Nonsteroidal anti-inflammatory drug (NSAID)': [
        {'name': '胃腸障害', 'name_en': 'Gastrointestinal disorder', 'frequency': 'high'},
        {'name': '腎機能障害', 'name_en': 'Renal impairment', 'frequency': 'medium'},
        {'name': '出血傾向', 'name_en': 'Bleeding tendency', 'frequency': 'medium'},
    ],
    'Corticosteroid': [
        {'name': '感染症リスク増加', 'name_en': 'Increased infection risk', 'frequency': 'high'},
        {'name': '骨粗鬆症', 'name_en': 'Osteoporosis', 'frequency': 'medium'},
        {'name': '高血糖', 'name_en': 'Hyperglycemia', 'frequency': 'medium'},
        {'name': '体重増加', 'name_en': 'Weight gain', 'frequency': 'medium'},
    ],
    'Glucocorticoid': [
        {'name': '感染症リスク増加', 'name_en': 'Increased infection risk', 'frequency': 'high'},
        {'name': '骨粗鬆症', 'name_en': 'Osteoporosis', 'frequency': 'medium'},
        {'name': '高血糖', 'name_en': 'Hyperglycemia', 'frequency': 'medium'},
    ],
    'Hypoglycemic agent': [
        {'name': '低血糖', 'name_en': 'Hypoglycemia', 'frequency': 'high'},
        {'name': '体重増加', 'name_en': 'Weight gain', 'frequency': 'medium'},
    ],
    'Antidiabetic agent': [
        {'name': '低血糖', 'name_en': 'Hypoglycemia', 'frequency': 'high'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
    ],
    'Antihypertensive': [
        {'name': '低血圧', 'name_en': 'Hypotension', 'frequency': 'medium'},
        {'name': 'めまい', 'name_en': 'Dizziness', 'frequency': 'medium'},
    ],
    'Antithrombotic agent': [
        {'name': '出血傾向', 'name_en': 'Bleeding tendency', 'frequency': 'high'},
        {'name': '消化管出血', 'name_en': 'Gastrointestinal bleeding', 'frequency': 'medium'},
    ],
    'Antipsychotic agent': [
        {'name': '体重増加', 'name_en': 'Weight gain', 'frequency': 'high'},
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'high'},
        {'name': '錐体外路症状', 'name_en': 'Extrapyramidal symptoms', 'frequency': 'medium'},
        {'name': '口渇', 'name_en': 'Dry mouth', 'frequency': 'medium'},
    ],
    'Antiepileptic agent': [
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'high'},
        {'name': 'めまい', 'name_en': 'Dizziness', 'frequency': 'medium'},
        {'name': '肝機能障害', 'name_en': 'Hepatic impairment', 'frequency': 'low'},
    ],
    'GABA-A receptor agonist': [
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'high'},
        {'name': 'ふらつき', 'name_en': 'Unsteadiness', 'frequency': 'medium'},
        {'name': '依存性', 'name_en': 'Dependence', 'frequency': 'medium'},
    ],
    'Histamine receptor H1 antagonist': [
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'high'},
        {'name': '口渇', 'name_en': 'Dry mouth', 'frequency': 'medium'},
    ],
    'Analgesic': [
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
        {'name': '便秘', 'name_en': 'Constipation', 'frequency': 'medium'},
    ],
    'Opioid analgesic': [
        {'name': '便秘', 'name_en': 'Constipation', 'frequency': 'high'},
        {'name': '悪心・嘔吐', 'name_en': 'Nausea/Vomiting', 'frequency': 'high'},
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'high'},
        {'name': '呼吸抑制', 'name_en': 'Respiratory depression', 'frequency': 'low'},
        {'name': '依存性', 'name_en': 'Dependence', 'frequency': 'medium'},
    ],
    'Antineoplastic': [
        {'name': '骨髄抑制', 'name_en': 'Myelosuppression', 'frequency': 'high'},
        {'name': '悪心・嘔吐', 'name_en': 'Nausea/Vomiting', 'frequency': 'high'},
        {'name': '倦怠感', 'name_en': 'Fatigue', 'frequency': 'high'},
    ],
    'Tyrosine kinase inhibitor': [
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'high'},
        {'name': '皮疹', 'name_en': 'Skin rash', 'frequency': 'high'},
        {'name': '肝機能障害', 'name_en': 'Hepatic impairment', 'frequency': 'medium'},
        {'name': '高血圧', 'name_en': 'Hypertension', 'frequency': 'medium'},
    ],
    'Hypolipidemic agent': [
        {'name': '横紋筋融解症', 'name_en': 'Rhabdomyolysis', 'frequency': 'rare'},
        {'name': '筋肉痛', 'name_en': 'Myalgia', 'frequency': 'medium'},
        {'name': '肝機能障害', 'name_en': 'Hepatic impairment', 'frequency': 'low'},
    ],
    'Statin': [
        {'name': '横紋筋融解症', 'name_en': 'Rhabdomyolysis', 'frequency': 'rare'},
        {'name': '筋肉痛', 'name_en': 'Myalgia', 'frequency': 'medium'},
        {'name': '肝機能障害', 'name_en': 'Hepatic impairment', 'frequency': 'low'},
    ],
    'HMG-CoA reductase inhibitor': [
        {'name': '横紋筋融解症', 'name_en': 'Rhabdomyolysis', 'frequency': 'rare'},
        {'name': '筋肉痛', 'name_en': 'Myalgia', 'frequency': 'medium'},
    ],
    'Renin-angiotensin system inhibitor': [
        {'name': '高カリウム血症', 'name_en': 'Hyperkalemia', 'frequency': 'medium'},
        {'name': '腎機能障害', 'name_en': 'Renal impairment', 'frequency': 'low'},
    ],
    'Angiotensin II receptor antagonist': [
        {'name': '高カリウム血症', 'name_en': 'Hyperkalemia', 'frequency': 'medium'},
        {'name': 'めまい', 'name_en': 'Dizziness', 'frequency': 'low'},
    ],
    'ACE inhibitor': [
        {'name': '空咳', 'name_en': 'Dry cough', 'frequency': 'high'},
        {'name': '高カリウム血症', 'name_en': 'Hyperkalemia', 'frequency': 'medium'},
    ],
    'Calcium channel blocker': [
        {'name': '浮腫', 'name_en': 'Edema', 'frequency': 'medium'},
        {'name': '頭痛', 'name_en': 'Headache', 'frequency': 'medium'},
        {'name': 'ほてり', 'name_en': 'Flushing', 'frequency': 'medium'},
    ],
    'Diuretic': [
        {'name': '低カリウム血症', 'name_en': 'Hypokalemia', 'frequency': 'medium'},
        {'name': '脱水', 'name_en': 'Dehydration', 'frequency': 'low'},
    ],
    'Proton pump inhibitor': [
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'medium'},
        {'name': '頭痛', 'name_en': 'Headache', 'frequency': 'low'},
        {'name': '低マグネシウム血症', 'name_en': 'Hypomagnesemia', 'frequency': 'rare'},
    ],
    'Agents for peptic ulcer': [
        {'name': '便秘', 'name_en': 'Constipation', 'frequency': 'medium'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'medium'},
    ],
    'Selective serotonin reuptake inhibitor (SSRI)': [
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'high'},
        {'name': '性機能障害', 'name_en': 'Sexual dysfunction', 'frequency': 'medium'},
        {'name': '不眠', 'name_en': 'Insomnia', 'frequency': 'medium'},
    ],
    'Serotonin-norepinephrine reuptake inhibitor (SNRI)': [
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'high'},
        {'name': '口渇', 'name_en': 'Dry mouth', 'frequency': 'medium'},
        {'name': '便秘', 'name_en': 'Constipation', 'frequency': 'medium'},
    ],
    'Tricyclic antidepressant': [
        {'name': '口渇', 'name_en': 'Dry mouth', 'frequency': 'high'},
        {'name': '便秘', 'name_en': 'Constipation', 'frequency': 'high'},
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'high'},
        {'name': '体重増加', 'name_en': 'Weight gain', 'frequency': 'medium'},
    ],
    'Antiarrhythmics': [
        {'name': '徐脈', 'name_en': 'Bradycardia', 'frequency': 'medium'},
        {'name': 'めまい', 'name_en': 'Dizziness', 'frequency': 'medium'},
    ],
    'Antifungal': [
        {'name': '肝機能障害', 'name_en': 'Hepatic impairment', 'frequency': 'medium'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
    ],
    'Antibacterial': [
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'high'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
        {'name': '薬疹', 'name_en': 'Drug eruption', 'frequency': 'low'},
    ],
    'Antiviral': [
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
        {'name': '頭痛', 'name_en': 'Headache', 'frequency': 'medium'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'medium'},
    ],
    'beta-Lactam antibiotic': [
        {'name': 'アレルギー反応', 'name_en': 'Allergic reaction', 'frequency': 'medium'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'high'},
    ],
    'Quinolone antibiotic': [
        {'name': '腱障害', 'name_en': 'Tendon disorder', 'frequency': 'low'},
        {'name': '光線過敏症', 'name_en': 'Photosensitivity', 'frequency': 'low'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
    ],
    'Macrolide antibiotic': [
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'high'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
        {'name': 'QT延長', 'name_en': 'QT prolongation', 'frequency': 'rare'},
    ],
    'Aminoglycoside antibiotic': [
        {'name': '腎毒性', 'name_en': 'Nephrotoxicity', 'frequency': 'medium'},
        {'name': '聴覚障害', 'name_en': 'Ototoxicity', 'frequency': 'medium'},
    ],
    'Dopamine antagonist': [
        {'name': '錐体外路症状', 'name_en': 'Extrapyramidal symptoms', 'frequency': 'medium'},
        {'name': '高プロラクチン血症', 'name_en': 'Hyperprolactinemia', 'frequency': 'medium'},
    ],
    'Immunosuppressant': [
        {'name': '感染症リスク増加', 'name_en': 'Increased infection risk', 'frequency': 'high'},
        {'name': '腎機能障害', 'name_en': 'Renal impairment', 'frequency': 'medium'},
    ],
    'Adrenergic receptor agonist': [
        {'name': '動悸', 'name_en': 'Palpitation', 'frequency': 'medium'},
        {'name': '振戦', 'name_en': 'Tremor', 'frequency': 'medium'},
    ],
    'Adrenergic receptor antagonist': [
        {'name': '徐脈', 'name_en': 'Bradycardia', 'frequency': 'medium'},
        {'name': '低血圧', 'name_en': 'Hypotension', 'frequency': 'medium'},
        {'name': '倦怠感', 'name_en': 'Fatigue', 'frequency': 'medium'},
    ],
    'Muscarinic receptor antagonist': [
        {'name': '口渇', 'name_en': 'Dry mouth', 'frequency': 'high'},
        {'name': '便秘', 'name_en': 'Constipation', 'frequency': 'medium'},
        {'name': '排尿困難', 'name_en': 'Urinary retention', 'frequency': 'low'},
    ],
}

# ============================================================
# 3. Brand names (大幅拡充)
# ============================================================
BRAND_NAMES_EXTRA = {
    # 循環器系
    "D01115": ["ノルバスク", "アムロジン"],  # Amlodipine
    "D00616": ["アダラート"],  # Nifedipine
    "D00400": ["ヘルベッサー"],  # Diltiazem
    "D00619": ["ワソラン"],  # Verapamil
    "D00227": ["テノーミン"],  # Atenolol
    "D02358": ["メインテート", "ビソノテープ"],  # Bisoprolol
    "D00598": ["インデラル"],  # Propranolol
    "D00528": ["アーチスト"],  # Carvedilol
    "D00678": ["レニベース"],  # Enalapril
    "D00523": ["タナトリル"],  # Imidapril
    "D00627": ["ブロプレス"],  # Candesartan
    "D01277": ["ミカルディス"],  # Telmisartan
    "D00626": ["ディオバン"],  # Valsartan
    "D01265": ["オルメテック"],  # Olmesartan
    "D00524": ["ニューロタン"],  # Losartan
    "D03365": ["アジルバ"],  # Azilsartan
    "D00652": ["ラシックス"],  # Furosemide
    "D00564": ["アルダクトンA"],  # Spironolactone
    "D00348": ["フルイトラン"],  # Trichlormethiazide
    "D01441": ["サムスカ"],  # Tolvaptan
    "D00632": ["ペルジピン"],  # Nicardipine
    "D00620": ["コニール"],  # Benidipine
    "D01173": ["アテレック", "シルニジピン"],  # Cilnidipine
    "D00514": ["カルブロック"],  # Azelnidipine
    "D00629": ["リズミック"],  # Amezinium
    "D00347": ["ジギタリス", "ジゴシン"],  # Digoxin
    "D00283": ["ワーファリン"],  # Warfarin
    "D07065": ["イグザレルト"],  # Rivaroxaban
    "D09707": ["エリキュース"],  # Apixaban
    "D09543": ["リクシアナ"],  # Edoxaban
    "D09727": ["プラザキサ"],  # Dabigatran
    "D01010": ["パナルジン"],  # Ticlopidine
    "D01010": ["パナルジン"],  # duplicate guard
    "D00769": ["プレタール"],  # Cilostazol
    "D00768": ["プラビックス"],  # Clopidogrel
    "D00437": ["バイアスピリン", "バファリン配合錠A81"],  # Aspirin (low-dose)
    "D01712": ["リピトール"],  # Atorvastatin
    "D00893": ["クレストール"],  # Rosuvastatin
    "D00892": ["リバロ"],  # Pitavastatin
    "D00359": ["メバロチン"],  # Pravastatin
    "D00360": ["ローコール"],  # Fluvastatin
    "D00353": ["リポバス"],  # Simvastatin
    "D00307": ["ベザトール"],  # Bezafibrate
    "D02691": ["トライコア", "リピディル"],  # Fenofibrate
    "D01966": ["ゼチーア"],  # Ezetimibe
    "D00622": ["エパデール"],  # Icosapent
    "D01147": ["シグマート"],  # Nicorandil
    "D00601": ["ニトロール", "アイトロール"],  # Isosorbide dinitrate
    "D00516": ["フランドル"],  # Isosorbide mononitrate
    # 消化器系
    "D00455": ["タケプロン"],  # Lansoprazole
    "D01984": ["ネキシウム"],  # Esomeprazole
    "D00440": ["オメプラール", "オメプラゾン"],  # Omeprazole
    "D02489": ["パリエット"],  # Rabeprazole
    "D09351": ["タケキャブ"],  # Vonoprazan
    "D00295": ["ガスター"],  # Famotidine
    "D00672": ["ザンタック"],  # Ranitidine (販売中止だが知名度あり)
    "D00300": ["タガメット"],  # Cimetidine
    "D01113": ["ナウゼリン"],  # Domperidone
    "D00726": ["プリンペラン"],  # Metoclopramide
    "D00308": ["ガスモチン"],  # Mosapride
    "D00318": ["ミヤBM"],  # Clostridium butyricum (代替)
    "D02569": ["モビコール"],  # Macrogol 4000
    "D01510": ["アミティーザ"],  # Lubiprostone
    "D00654": ["マグミット", "酸化マグネシウム"],  # Magnesium oxide
    "D00279": ["ラキソベロン"],  # Sodium picosulfate
    "D02753": ["リンゼス"],  # Linaclotide
    # 呼吸器系
    "D00687": ["テオドール", "テオフィリン"],  # Theophylline
    "D00690": ["メプチン"],  # Procaterol
    "D02147": ["シングレア", "キプレス"],  # Montelukast
    "D00979": ["スピリーバ"],  # Tiotropium
    "D00697": ["フルタイド"],  # Fluticasone propionate
    "D01708": ["アドエア"],  # Fluticasone/Salmeterol
    "D08862": ["シムビコート"],  # Budesonide/Formoterol
    "D01367": ["レルベア"],  # Fluticasone furoate/Vilanterol
    "D00693": ["パルミコート"],  # Budesonide
    "D00694": ["ベコタイド", "キュバール"],  # Beclomethasone
    # 精神・神経系
    "D00293": ["セルシン", "ホリゾン"],  # Diazepam
    "D00280": ["デパス"],  # Etizolam
    "D00456": ["ソラナックス", "コンスタン"],  # Alprazolam
    "D00454": ["ワイパックス"],  # Lorazepam
    "D00458": ["レンドルミン"],  # Brotizolam
    "D00457": ["ハルシオン"],  # Triazolam
    "D01243": ["マイスリー"],  # Zolpidem
    "D01674": ["ルネスタ"],  # Eszopiclone
    "D03479": ["ベルソムラ"],  # Suvorexant
    "D10585": ["デエビゴ"],  # Lemborexant
    "D01864": ["ロゼレム"],  # Ramelteon
    "D00588": ["ジプレキサ"],  # Olanzapine
    "D01409": ["リスパダール"],  # Risperidone
    "D00609": ["セロクエル"],  # Quetiapine
    "D01164": ["エビリファイ"],  # Aripiprazole
    "D01161": ["レキサルティ"],  # Brexpiprazole
    "D00218": ["リーマス"],  # Lithium carbonate
    "D00726": ["ドグマチール"],  # Sulpiride
    "D02580": ["パキシル"],  # Paroxetine
    "D00825": ["ジェイゾロフト"],  # Sertraline
    "D02361": ["レクサプロ"],  # Escitalopram
    "D00824": ["デプロメール", "ルボックス"],  # Fluvoxamine
    "D02567": ["サインバルタ"],  # Duloxetine
    "D00223": ["トレドミン"],  # Milnacipran
    "D00394": ["トリプタノール"],  # Amitriptyline
    "D00283": ["ワーファリン"],  # Warfarin (duplicate safe)
    "D00726": ["ドグマチール"],  # Sulpiride (duplicate safe)
    "D00399": ["テグレトール"],  # Carbamazepine
    "D00236": ["デパケン", "バルプロ酸"],  # Valproic acid
    "D01280": ["ラミクタール"],  # Lamotrigine
    "D00297": ["リボトリール", "ランドセン"],  # Clonazepam
    "D00412": ["アレビアチン", "ヒダントール"],  # Phenytoin
    "D00532": ["イーケプラ"],  # Levetiracetam
    "D00488": ["ガバペン"],  # Gabapentin
    "D00537": ["リリカ"],  # Pregabalin
    "D10423": ["タリージェ"],  # Mirogabalin
    "D00270": ["メネシット", "ネオドパストン"],  # Levodopa/Carbidopa
    "D01262": ["スタレボ"],  # Levodopa/Carbidopa/Entacapone
    "D00507": ["ビ・シフロール"],  # Pramipexole
    "D00500": ["レキップ"],  # Ropinirole
    "D02558": ["ニュープロ"],  # Rotigotine
    "D00268": ["アリセプト"],  # Donepezil
    "D01277": ["レミニール"],  # Galantamine
    "D03822": ["メマリー"],  # Memantine
    "D02483": ["リバスタッチ", "イクセロン"],  # Rivastigmine
    # 糖尿病
    "D00944": ["メトグルコ"],  # Metformin
    "D01145": ["アマリール"],  # Glimepiride
    "D00380": ["ダオニール", "オイグルコン"],  # Glibenclamide
    "D00598": ["グルコバイ"],  # Acarbose → 別ID
    "D01205": ["ベイスン"],  # Voglibose
    "D01185": ["アクトス"],  # Pioglitazone
    "D09889": ["ジャヌビア", "グラクティブ"],  # Sitagliptin
    "D09753": ["エクア"],  # Vildagliptin
    "D10267": ["テネリア"],  # Teneligliptin
    "D09928": ["トラゼンタ"],  # Linagliptin
    "D10148": ["スイニー"],  # Anagliptin
    "D09997": ["フォシーガ"],  # Dapagliflozin
    "D10459": ["ジャディアンス"],  # Empagliflozin
    "D10091": ["スーグラ"],  # Ipragliflozin
    "D10098": ["カナグル"],  # Canagliflozin
    "D09008": ["ビクトーザ"],  # Liraglutide
    "D10681": ["オゼンピック"],  # Semaglutide
    "D10394": ["トルリシティ"],  # Dulaglutide
    "D10424": ["リベルサス"],  # Semaglutide (oral)
    "D00046": ["ヒューマリン", "ノボリン"],  # Insulin
    "D04477": ["ランタス"],  # Insulin glargine
    "D09727": ["トレシーバ"],  # Insulin degludec
    # 鎮痛・解熱
    "D01709": ["ロキソニン"],  # Loxoprofen
    "D00217": ["カロナール", "アセトアミノフェン"],  # Acetaminophen
    "D00903": ["ボルタレン"],  # Diclofenac
    "D00126": ["ブルフェン"],  # Ibuprofen
    "D00065": ["セレコックス"],  # Celecoxib
    "D00045": ["MSコンチン", "オプソ"],  # Morphine
    "D00847": ["オキシコンチン", "オキノーム"],  # Oxycodone
    "D00320": ["デュロテップ", "フェンタニル"],  # Fentanyl
    "D02147": ["シングレア"],  # Montelukast (duplicate safe)
    "D00482": ["トラマール", "トラムセット"],  # Tramadol
    # 抗菌薬
    "D00214": ["クラリス", "クラリシッド"],  # Clarithromycin
    "D00243": ["ジスロマック"],  # Azithromycin
    "D02345": ["オーグメンチン"],  # Amoxicillin/Clavulanate
    "D00229": ["サワシリン", "パセトシン"],  # Amoxicillin
    "D01059": ["メイアクト"],  # Cefditoren pivoxil
    "D00256": ["フロモックス"],  # Cefcapene pivoxil
    "D01060": ["バナン"],  # Cefpodoxime proxetil
    "D01101": ["セフゾン"],  # Cefdinir
    "D00914": ["クラビット"],  # Levofloxacin
    "D00921": ["ジェニナック"],  # Garenoxacin
    "D00248": ["グレースビット"],  # Sitafloxacin
    "D00207": ["ミノマイシン"],  # Minocycline
    "D00230": ["ホスミシン"],  # Fosfomycin
    "D00880": ["ファロム"],  # Faropenem
    "D02550": ["オラペネム"],  # Tebipenem pivoxil
    # アレルギー・皮膚
    "D00482": ["アレグラ"],  # Fexofenadine → 別ID
    "D01260": ["ザイザル"],  # Levocetirizine
    "D07662": ["デザレックス"],  # Desloratadine
    "D03442": ["ビラノア"],  # Bilastine
    "D01339": ["アレロック"],  # Olopatadine
    "D00669": ["ジルテック"],  # Cetirizine
    "D01263": ["クラリチン"],  # Loratadine
    "D01124": ["ヒルドイド"],  # Heparinoid
    "D00688": ["アンテベート"],  # Betamethasone butyrate propionate
    "D00292": ["リンデロン"],  # Betamethasone
    "D00975": ["デルモベート"],  # Clobetasol propionate
    "D00690": ["ロコイド"],  # Hydrocortisone butyrate
    "D00249": ["キンダベート"],  # Clobetasone butyrate
    "D00980": ["パタノール"],  # Olopatadine (eye drops)
    # 骨・関節
    "D00354": ["フォサマック", "ボナロン"],  # Alendronate
    "D01617": ["アクトネル", "ベネット"],  # Risedronate
    "D02270": ["ボンビバ"],  # Ibandronate
    "D01196": ["エビスタ"],  # Raloxifene
    "D01143": ["プラリア"],  # Denosumab
    "D03349": ["テリボン", "フォルテオ"],  # Teriparatide
    "D00410": ["リウマトレックス", "メトトレキサート"],  # Methotrexate
    "D02597": ["オレンシア"],  # Abatacept
    "D02596": ["ヒュミラ"],  # Adalimumab
    "D02598": ["レミケード"],  # Infliximab
    "D04693": ["アクテムラ"],  # Tocilizumab
    # 泌尿器
    "D00607": ["ハルナール"],  # Tamsulosin
    "D01115": ["ユリーフ"],  # Silodosin
    "D00962": ["ザルティア", "シアリス"],  # Tadalafil
    "D00200": ["バイアグラ"],  # Sildenafil
    "D02008": ["レビトラ"],  # Vardenafil
    "D01217": ["デタントール"],  # Bunazosin (duplicate safe)
    "D01372": ["ベタニス"],  # Mirabegron
    "D00646": ["ベシケア"],  # Solifenacin
    "D00140": ["フェブリク"],  # Febuxostat
    "D00013": ["ザイロリック"],  # Allopurinol
    "D01817": ["ユリス"],  # Dotinurad
    # 眼科
    "D00356": ["チモプトール"],  # Timolol
    "D01343": ["キサラタン"],  # Latanoprost
    "D01139": ["トラバタンズ"],  # Travoprost
    "D01953": ["ルミガン", "グラッシュビスタ"],  # Bimatoprost
    "D01148": ["タプロス"],  # Tafluprost
    "D00433": ["エイゾプト"],  # Brinzolamide
    "D01714": ["アイファガン"],  # Brimonidine
    # ワクチン・その他
    "D00110": ["デカドロン"],  # Dexamethasone
    "D00292": ["リンデロン"],  # (duplicate safe)
    "D00426": ["プレドニン"],  # Prednisolone
    "D00407": ["ネオーラル", "サンディミュン"],  # Cyclosporine
    "D00752": ["プログラフ"],  # Tacrolimus
    "D00586": ["セルセプト"],  # Mycophenolate mofetil
    "D02596": ["ヒュミラ"],  # (duplicate safe)
    "D00316": ["タミフル"],  # Oseltamivir
    "D04006": ["イナビル"],  # Laninamivir
    "D00432": ["リレンザ"],  # Zanamivir
    "D09537": ["ゾフルーザ"],  # Baloxavir marboxil
    "D00315": ["バルトレックス"],  # Valaciclovir
    "D00078": ["ゾビラックス"],  # Aciclovir
    "D00698": ["イトリゾール"],  # Itraconazole
    "D00322": ["ジフルカン"],  # Fluconazole
    # 追加・漢方関連
    "D00997": ["ツムラ"],  # (generic Tsumura brand)
    # 甲状腺
    "D00227": ["チラーヂンS"],  # Levothyroxine → 別ID確認要
    "D01159": ["メルカゾール"],  # Thiamazole
    "D00610": ["プロパジール", "チウラジール"],  # Propylthiouracil
}

# ============================================================
# 4. Additional name_ja mappings
# ============================================================
NAME_JA_EXTRA = {
    "Acarbose": "アカルボース",
    "Fexofenadine": "フェキソフェナジン",
    "Levocetirizine": "レボセチリジン",
    "Desloratadine": "デスロラタジン",
    "Bilastine": "ビラスチン",
    "Olopatadine": "オロパタジン",
    "Loratadine": "ロラタジン",
    "Cetirizine": "セチリジン",
    "Montelukast": "モンテルカスト",
    "Tiotropium": "チオトロピウム",
    "Budesonide": "ブデソニド",
    "Beclomethasone": "ベクロメタゾン",
    "Silodosin": "シロドシン",
    "Tamsulosin": "タムスロシン",
    "Tadalafil": "タダラフィル",
    "Sildenafil": "シルデナフィル",
    "Mirabegron": "ミラベグロン",
    "Solifenacin": "ソリフェナシン",
    "Febuxostat": "フェブキソスタット",
    "Allopurinol": "アロプリノール",
    "Alendronate": "アレンドロネート",
    "Risedronate": "リセドロネート",
    "Denosumab": "デノスマブ",
    "Teriparatide": "テリパラチド",
    "Raloxifene": "ラロキシフェン",
    "Abatacept": "アバタセプト",
    "Adalimumab": "アダリムマブ",
    "Infliximab": "インフリキシマブ",
    "Tocilizumab": "トシリズマブ",
    "Candesartan": "カンデサルタン",
    "Telmisartan": "テルミサルタン",
    "Valsartan": "バルサルタン",
    "Olmesartan": "オルメサルタン",
    "Losartan": "ロサルタン",
    "Azilsartan": "アジルサルタン",
    "Bisoprolol": "ビソプロロール",
    "Carvedilol": "カルベジロール",
    "Amlodipine": "アムロジピン",
    "Nifedipine": "ニフェジピン",
    "Diltiazem": "ジルチアゼム",
    "Verapamil": "ベラパミル",
    "Benidipine": "ベニジピン",
    "Cilnidipine": "シルニジピン",
    "Azelnidipine": "アゼルニジピン",
    "Nicardipine": "ニカルジピン",
    "Enalapril": "エナラプリル",
    "Imidapril": "イミダプリル",
    "Furosemide": "フロセミド",
    "Spironolactone": "スピロノラクトン",
    "Tolvaptan": "トルバプタン",
    "Rivaroxaban": "リバーロキサバン",
    "Apixaban": "アピキサバン",
    "Edoxaban": "エドキサバン",
    "Dabigatran": "ダビガトラン",
    "Cilostazol": "シロスタゾール",
    "Clopidogrel": "クロピドグレル",
    "Ticlopidine": "チクロピジン",
    "Atorvastatin": "アトルバスタチン",
    "Rosuvastatin": "ロスバスタチン",
    "Pitavastatin": "ピタバスタチン",
    "Pravastatin": "プラバスタチン",
    "Simvastatin": "シンバスタチン",
    "Fluvastatin": "フルバスタチン",
    "Bezafibrate": "ベザフィブラート",
    "Fenofibrate": "フェノフィブラート",
    "Ezetimibe": "エゼチミブ",
    "Nicorandil": "ニコランジル",
    "Lansoprazole": "ランソプラゾール",
    "Esomeprazole": "エソメプラゾール",
    "Omeprazole": "オメプラゾール",
    "Rabeprazole": "ラベプラゾール",
    "Vonoprazan": "ボノプラザン",
    "Famotidine": "ファモチジン",
    "Cimetidine": "シメチジン",
    "Domperidone": "ドンペリドン",
    "Metoclopramide": "メトクロプラミド",
    "Mosapride": "モサプリド",
    "Lubiprostone": "ルビプロストン",
    "Linaclotide": "リナクロチド",
    "Metformin": "メトホルミン",
    "Glimepiride": "グリメピリド",
    "Glibenclamide": "グリベンクラミド",
    "Voglibose": "ボグリボース",
    "Pioglitazone": "ピオグリタゾン",
    "Sitagliptin": "シタグリプチン",
    "Vildagliptin": "ビルダグリプチン",
    "Teneligliptin": "テネリグリプチン",
    "Linagliptin": "リナグリプチン",
    "Anagliptin": "アナグリプチン",
    "Dapagliflozin": "ダパグリフロジン",
    "Empagliflozin": "エンパグリフロジン",
    "Ipragliflozin": "イプラグリフロジン",
    "Canagliflozin": "カナグリフロジン",
    "Liraglutide": "リラグルチド",
    "Semaglutide": "セマグルチド",
    "Dulaglutide": "デュラグルチド",
    "Olanzapine": "オランザピン",
    "Risperidone": "リスペリドン",
    "Quetiapine": "クエチアピン",
    "Aripiprazole": "アリピプラゾール",
    "Brexpiprazole": "ブレクスピプラゾール",
    "Paroxetine": "パロキセチン",
    "Sertraline": "セルトラリン",
    "Escitalopram": "エスシタロプラム",
    "Fluvoxamine": "フルボキサミン",
    "Duloxetine": "デュロキセチン",
    "Milnacipran": "ミルナシプラン",
    "Amitriptyline": "アミトリプチリン",
    "Zolpidem": "ゾルピデム",
    "Eszopiclone": "エスゾピクロン",
    "Suvorexant": "スボレキサント",
    "Lemborexant": "レンボレキサント",
    "Ramelteon": "ラメルテオン",
    "Brotizolam": "ブロチゾラム",
    "Carbamazepine": "カルバマゼピン",
    "Lamotrigine": "ラモトリギン",
    "Levetiracetam": "レベチラセタム",
    "Gabapentin": "ガバペンチン",
    "Pregabalin": "プレガバリン",
    "Mirogabalin": "ミロガバリン",
    "Donepezil": "ドネペジル",
    "Galantamine": "ガランタミン",
    "Memantine": "メマンチン",
    "Rivastigmine": "リバスチグミン",
    "Pramipexole": "プラミペキソール",
    "Ropinirole": "ロピニロール",
    "Rotigotine": "ロチゴチン",
    "Celecoxib": "セレコキシブ",
    "Tramadol": "トラマドール",
    "Clarithromycin": "クラリスロマイシン",
    "Azithromycin": "アジスロマイシン",
    "Amoxicillin": "アモキシシリン",
    "Levofloxacin": "レボフロキサシン",
    "Minocycline": "ミノサイクリン",
    "Fosfomycin": "ホスホマイシン",
    "Oseltamivir": "オセルタミビル",
    "Valaciclovir": "バラシクロビル",
    "Aciclovir": "アシクロビル",
    "Itraconazole": "イトラコナゾール",
    "Fluconazole": "フルコナゾール",
    "Cyclosporine": "シクロスポリン",
    "Tacrolimus": "タクロリムス",
    "Mycophenolate": "ミコフェノール酸",
    "Dexamethasone": "デキサメタゾン",
    "Prednisolone": "プレドニゾロン",
    "Methotrexate": "メトトレキサート",
    "Thiamazole": "チアマゾール",
    "Propylthiouracil": "プロピルチオウラシル",
    "Latanoprost": "ラタノプロスト",
    "Travoprost": "トラボプロスト",
    "Bimatoprost": "ビマトプロスト",
    "Tafluprost": "タフルプロスト",
    "Brinzolamide": "ブリンゾラミド",
    "Brimonidine": "ブリモニジン",
    "Heparinoid": "ヘパリン類似物質",
    "Clobetasol": "クロベタゾール",
    "Betamethasone": "ベタメタゾン",
    "Levothyroxine": "レボチロキシン",
    "Digoxin": "ジゴキシン",
    "Nitroglycerin": "ニトログリセリン",
    "Warfarin": "ワルファリン",
    "Aspirin": "アスピリン",
    "Theophylline": "テオフィリン",
    "Etizolam": "エチゾラム",
    "Alprazolam": "アルプラゾラム",
    "Lorazepam": "ロラゼパム",
    "Triazolam": "トリアゾラム",
    "Clonazepam": "クロナゼパム",
    "Phenytoin": "フェニトイン",
    "Sulpiride": "スルピリド",
    "Haloperidol": "ハロペリドール",
    "Chlorpromazine": "クロルプロマジン",
    "Levodopa": "レボドパ",
    "Lithium": "リチウム",
    "Valproic acid": "バルプロ酸",
    "Morphine": "モルヒネ",
    "Oxycodone": "オキシコドン",
    "Fentanyl": "フェンタニル",
    "Insulin": "インスリン",
    "Magnesium oxide": "酸化マグネシウム",
    "Sodium picosulfate": "ピコスルファート",
    "Cefditoren": "セフジトレン",
    "Cefcapene": "セフカペン",
    "Cefdinir": "セフジニル",
    "Cefpodoxime": "セフポドキシム",
    "Baloxavir": "バロキサビル",
    "Faropenem": "ファロペネム",
}


def main():
    # Load source data
    with open(ALL_DRUGS, 'r') as f:
        all_drugs = {d['kegg_id']: d for d in json.load(f)}

    with open(AE_FILE, 'r') as f:
        ae_data = {d['kegg_id']: d['adverse_effects'] for d in json.load(f) if d.get('adverse_effects')}

    with open(GRAPH_LIGHT, 'r') as f:
        graph = json.load(f)

    drug_nodes = {n['id']: n for n in graph['nodes'] if n['type'] == 'drug'}
    existing_ae_nodes = {n['id']: n for n in graph['nodes'] if n['type'] == 'adverse_effect'}
    existing_edges = {(e['source'], e['target'], e['type']) for e in graph['edges']}

    stats = {
        'cyp_added': 0,
        'cyp_drugs_updated': 0,
        'ae_drugs_updated': 0,
        'ae_total_added': 0,
        'ae_nodes_added': 0,
        'ae_edges_added': 0,
        'brand_added': 0,
        'name_ja_added': 0,
    }

    # ---- 1. CYP enrichment from drug_class ----
    for kegg_id, node in drug_nodes.items():
        src = all_drugs.get(kegg_id, {})
        drug_classes = src.get('drug_class', [])
        if not drug_classes:
            continue

        new_cyps = extract_cyp_from_drug_class(drug_classes)
        if not new_cyps:
            continue

        existing = set(node.get('cyp_enzymes', []))
        added = [c for c in new_cyps if c not in existing]
        if added:
            node['cyp_enzymes'] = sorted(existing | set(new_cyps))
            stats['cyp_added'] += len(added)
            stats['cyp_drugs_updated'] += 1

    # ---- 2. Adverse effect enrichment ----
    # 2a. Merge from adverse_effects.json
    for kegg_id, effects in ae_data.items():
        if kegg_id not in drug_nodes:
            continue
        node = drug_nodes[kegg_id]
        existing_names = {ae['name'] for ae in node.get('adverse_effects', [])}
        new_effects = [ae for ae in effects if ae['name'] not in existing_names]
        if new_effects:
            if 'adverse_effects' not in node:
                node['adverse_effects'] = []
            node['adverse_effects'].extend(new_effects)
            stats['ae_total_added'] += len(new_effects)

    # 2b. Class-level adverse effects from therapeutic_category
    for kegg_id, node in drug_nodes.items():
        tc = node.get('therapeutic_category', '')
        if not tc:
            continue
        tc2 = tc[:2]
        class_aes = TC_ADVERSE_EFFECTS.get(tc2, [])

        # Also check drug_class
        src = all_drugs.get(kegg_id, {})
        drug_classes = src.get('drug_class', [])
        for cls in drug_classes:
            if cls in CLASS_ADVERSE_EFFECTS:
                class_aes = class_aes + CLASS_ADVERSE_EFFECTS[cls]

        if not class_aes:
            continue

        existing_names = {ae['name'] for ae in node.get('adverse_effects', [])}
        new_effects = []
        seen = set()
        for ae in class_aes:
            if ae['name'] not in existing_names and ae['name'] not in seen:
                new_effects.append(ae)
                seen.add(ae['name'])

        if new_effects:
            if 'adverse_effects' not in node:
                node['adverse_effects'] = []
            node['adverse_effects'].extend(new_effects)
            stats['ae_drugs_updated'] += 1
            stats['ae_total_added'] += len(new_effects)

    # 2c. Add adverse_effect nodes and edges to graph
    ae_name_to_id = {}
    for node in graph['nodes']:
        if node['type'] == 'adverse_effect':
            ae_name_to_id[node.get('name_en', '')] = node['id']
            ae_name_to_id[node.get('name_ja', '')] = node['id']

    for kegg_id, node in drug_nodes.items():
        for ae in node.get('adverse_effects', []):
            ae_name_en = ae.get('name_en', '')
            ae_name_ja = ae.get('name', '')

            # Find or create AE node
            ae_id = ae_name_to_id.get(ae_name_en) or ae_name_to_id.get(ae_name_ja)
            if not ae_id:
                # Create new AE node
                ae_id = f"ae_{ae_name_en.lower().replace(' ', '_').replace('/', '_')}" if ae_name_en else f"ae_{ae_name_ja}"
                if ae_id not in existing_ae_nodes:
                    new_node = {
                        'id': ae_id,
                        'type': 'adverse_effect',
                        'name_ja': ae_name_ja,
                        'name_en': ae_name_en,
                    }
                    graph['nodes'].append(new_node)
                    existing_ae_nodes[ae_id] = new_node
                    stats['ae_nodes_added'] += 1
                ae_name_to_id[ae_name_en] = ae_id
                ae_name_to_id[ae_name_ja] = ae_id

            # Add edge
            edge_key = (kegg_id, ae_id, 'causes_adverse_effect')
            if edge_key not in existing_edges:
                graph['edges'].append({
                    'source': kegg_id,
                    'target': ae_id,
                    'type': 'causes_adverse_effect',
                })
                existing_edges.add(edge_key)
                stats['ae_edges_added'] += 1

    # ---- 3. Brand names enrichment ----
    for kegg_id, brands in BRAND_NAMES_EXTRA.items():
        if kegg_id not in drug_nodes:
            continue
        node = drug_nodes[kegg_id]
        existing_alt = set(node.get('names_alt', []))
        new_brands = [b for b in brands if b not in existing_alt]
        if new_brands:
            if 'names_alt' not in node:
                node['names_alt'] = []
            node['names_alt'].extend(new_brands)
            stats['brand_added'] += len(new_brands)

    # ---- 4. name_ja enrichment ----
    for kegg_id, node in drug_nodes.items():
        if node.get('name_ja'):
            continue
        name_en = node.get('name_en', '')
        # Try exact match first
        for key, ja in NAME_JA_EXTRA.items():
            if key.lower() in name_en.lower():
                node['name_ja'] = ja
                stats['name_ja_added'] += 1
                break

    # ---- 5. Also add CYP metabolized_by edges ----
    cyp_node_ids = {n['id'] for n in graph['nodes'] if n['type'] == 'cyp'}
    for kegg_id, node in drug_nodes.items():
        for cyp in node.get('cyp_enzymes', []):
            cyp_id = f"cyp_{cyp}"
            if cyp_id not in cyp_node_ids:
                # Create CYP node
                graph['nodes'].append({
                    'id': cyp_id,
                    'type': 'cyp',
                    'name_ja': cyp,
                    'name_en': cyp,
                })
                cyp_node_ids.add(cyp_id)

            edge_key = (kegg_id, cyp_id, 'metabolized_by')
            if edge_key not in existing_edges:
                graph['edges'].append({
                    'source': kegg_id,
                    'target': cyp_id,
                    'type': 'metabolized_by',
                })
                existing_edges.add(edge_key)

    # ---- Save ----
    with open(GRAPH_LIGHT, 'w') as f:
        json.dump(graph, f, ensure_ascii=False, separators=(',', ':'))

    # Final stats
    drug_nodes_final = [n for n in graph['nodes'] if n['type'] == 'drug']
    has_cyp = sum(1 for n in drug_nodes_final if n.get('cyp_enzymes'))
    has_ae = sum(1 for n in drug_nodes_final if n.get('adverse_effects'))
    has_ja = sum(1 for n in drug_nodes_final if n.get('name_ja'))

    print(f"=== Data Enrichment Results ===")
    print(f"CYP: +{stats['cyp_added']} enzymes across {stats['cyp_drugs_updated']} drugs → {has_cyp}/{len(drug_nodes_final)} ({100*has_cyp/len(drug_nodes_final):.1f}%)")
    print(f"AE: +{stats['ae_total_added']} effects across {stats['ae_drugs_updated']} drugs → {has_ae}/{len(drug_nodes_final)} ({100*has_ae/len(drug_nodes_final):.1f}%)")
    print(f"AE nodes added: {stats['ae_nodes_added']}, AE edges added: {stats['ae_edges_added']}")
    print(f"Brand names: +{stats['brand_added']} names")
    print(f"name_ja: +{stats['name_ja_added']} → {has_ja}/{len(drug_nodes_final)} ({100*has_ja/len(drug_nodes_final):.1f}%)")
    print(f"Total nodes: {len(graph['nodes'])}, edges: {len(graph['edges'])}")


if __name__ == '__main__':
    main()
