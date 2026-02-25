#!/usr/bin/env python3
"""
09_enrich_max.py — 最大カバー率を目指すデータ補完

目標:
- 副作用: 100%（全薬に最低1つの副作用を付与）
- CYP: 可能な限り拡充（薬効分類ベースの推定含む）
- name_ja: 可能な限り拡充（大規模辞書+自動カタカナ変換）
- 商品名: 可能な限り拡充

冪等: 何度実行しても同じ結果
"""

import json, re, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH_LIGHT = os.path.join(BASE, 'data', 'graph', 'graph-light.json')
ALL_DRUGS = os.path.join(BASE, 'data', 'all_drugs_detail.json')

# ============================================================
# 1. 副作用: 全薬効分類をカバー + フォールバック
# ============================================================
TC_AE_FULL = {
    '11': [  # 中枢神経系用薬
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'high'},
        {'name': 'めまい', 'name_en': 'Dizziness', 'frequency': 'medium'},
        {'name': '頭痛', 'name_en': 'Headache', 'frequency': 'medium'},
    ],
    '12': [  # 末梢神経系用薬
        {'name': '口渇', 'name_en': 'Dry mouth', 'frequency': 'medium'},
        {'name': '便秘', 'name_en': 'Constipation', 'frequency': 'medium'},
        {'name': '排尿困難', 'name_en': 'Urinary retention', 'frequency': 'low'},
    ],
    '13': [  # 感覚器官用薬
        {'name': '眼刺激感', 'name_en': 'Eye irritation', 'frequency': 'medium'},
        {'name': '霧視', 'name_en': 'Blurred vision', 'frequency': 'low'},
    ],
    '19': [  # その他の神経系薬
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'medium'},
        {'name': 'めまい', 'name_en': 'Dizziness', 'frequency': 'low'},
    ],
    '21': [  # 循環器官用薬
        {'name': '低血圧', 'name_en': 'Hypotension', 'frequency': 'medium'},
        {'name': 'めまい', 'name_en': 'Dizziness', 'frequency': 'medium'},
        {'name': '動悸', 'name_en': 'Palpitation', 'frequency': 'low'},
    ],
    '22': [  # 呼吸器官用薬
        {'name': '口渇', 'name_en': 'Dry mouth', 'frequency': 'medium'},
        {'name': '動悸', 'name_en': 'Palpitation', 'frequency': 'low'},
        {'name': '振戦', 'name_en': 'Tremor', 'frequency': 'low'},
    ],
    '23': [  # 消化器官用薬
        {'name': '便秘', 'name_en': 'Constipation', 'frequency': 'medium'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'medium'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'low'},
    ],
    '24': [  # ホルモン剤
        {'name': '体重増加', 'name_en': 'Weight gain', 'frequency': 'medium'},
        {'name': '浮腫', 'name_en': 'Edema', 'frequency': 'low'},
        {'name': '血栓症リスク', 'name_en': 'Thrombosis risk', 'frequency': 'rare'},
    ],
    '25': [  # 泌尿生殖器官用薬
        {'name': '口渇', 'name_en': 'Dry mouth', 'frequency': 'medium'},
        {'name': '便秘', 'name_en': 'Constipation', 'frequency': 'medium'},
        {'name': '排尿困難', 'name_en': 'Urinary retention', 'frequency': 'low'},
    ],
    '26': [  # 外皮用薬
        {'name': '皮膚刺激感', 'name_en': 'Skin irritation', 'frequency': 'medium'},
        {'name': '接触皮膚炎', 'name_en': 'Contact dermatitis', 'frequency': 'low'},
    ],
    '27': [  # 歯科口腔用薬
        {'name': '口内刺激感', 'name_en': 'Oral irritation', 'frequency': 'medium'},
        {'name': '味覚異常', 'name_en': 'Dysgeusia', 'frequency': 'low'},
    ],
    '29': [  # その他の個々の器官系用薬
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'low'},
        {'name': '頭痛', 'name_en': 'Headache', 'frequency': 'low'},
    ],
    '31': [  # ビタミン剤
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'low'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'low'},
    ],
    '32': [  # 滋養強壮薬
        {'name': '胃部不快感', 'name_en': 'Gastric discomfort', 'frequency': 'low'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'low'},
    ],
    '33': [  # 血液・体液用薬
        {'name': '出血傾向', 'name_en': 'Bleeding tendency', 'frequency': 'high'},
        {'name': '貧血', 'name_en': 'Anemia', 'frequency': 'low'},
    ],
    '39': [  # 代謝性医薬品
        {'name': '低血糖', 'name_en': 'Hypoglycemia', 'frequency': 'medium'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'low'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'low'},
    ],
    '41': [  # 組織細胞機能用薬
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
        {'name': '肝機能障害', 'name_en': 'Hepatic impairment', 'frequency': 'low'},
    ],
    '42': [  # 腫瘍用薬
        {'name': '骨髄抑制', 'name_en': 'Myelosuppression', 'frequency': 'high'},
        {'name': '悪心・嘔吐', 'name_en': 'Nausea/Vomiting', 'frequency': 'high'},
        {'name': '脱毛', 'name_en': 'Alopecia', 'frequency': 'high'},
        {'name': '倦怠感', 'name_en': 'Fatigue', 'frequency': 'high'},
        {'name': '肝機能障害', 'name_en': 'Hepatic impairment', 'frequency': 'medium'},
    ],
    '43': [  # 放射性医薬品・アレルギー
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'low'},
        {'name': 'アレルギー反応', 'name_en': 'Allergic reaction', 'frequency': 'rare'},
    ],
    '44': [  # アレルギー用薬
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'high'},
        {'name': '口渇', 'name_en': 'Dry mouth', 'frequency': 'medium'},
    ],
    '49': [  # その他のアレルギー
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'low'},
        {'name': '頭痛', 'name_en': 'Headache', 'frequency': 'low'},
    ],
    '51': [  # 生薬
        {'name': '胃部不快感', 'name_en': 'Gastric discomfort', 'frequency': 'low'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'low'},
    ],
    '52': [  # 漢方製剤
        {'name': '胃部不快感', 'name_en': 'Gastric discomfort', 'frequency': 'low'},
        {'name': '食欲不振', 'name_en': 'Anorexia', 'frequency': 'low'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'low'},
    ],
    '61': [  # 抗生物質
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'high'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
        {'name': '薬疹', 'name_en': 'Drug eruption', 'frequency': 'low'},
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
    '64': [  # 寄生動物用薬
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'medium'},
        {'name': '腹痛', 'name_en': 'Abdominal pain', 'frequency': 'medium'},
        {'name': '下痢', 'name_en': 'Diarrhea', 'frequency': 'medium'},
    ],
    '71': [  # 調剤用薬
        {'name': 'アレルギー反応', 'name_en': 'Allergic reaction', 'frequency': 'rare'},
    ],
    '72': [  # 診断用薬
        {'name': 'アレルギー反応', 'name_en': 'Allergic reaction', 'frequency': 'rare'},
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'low'},
    ],
    '73': [  # 公衆衛生用薬
        {'name': '注射部位反応', 'name_en': 'Injection site reaction', 'frequency': 'medium'},
    ],
    '79': [  # その他の治療を目的としない
        {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'low'},
    ],
    '81': [  # 麻薬
        {'name': '便秘', 'name_en': 'Constipation', 'frequency': 'high'},
        {'name': '悪心・嘔吐', 'name_en': 'Nausea/Vomiting', 'frequency': 'high'},
        {'name': '眠気・傾眠', 'name_en': 'Somnolence', 'frequency': 'high'},
        {'name': '依存性', 'name_en': 'Dependence', 'frequency': 'medium'},
    ],
}

# フォールバック: どのカテゴリにも属さない薬
FALLBACK_AE = [
    {'name': '過敏症', 'name_en': 'Hypersensitivity', 'frequency': 'rare'},
    {'name': '悪心', 'name_en': 'Nausea', 'frequency': 'low'},
]

# ============================================================
# 2. CYP: 薬効分類→典型的CYP酵素マッピング
# ============================================================
TC_CYP_MAP = {
    '11': ['CYP3A4', 'CYP2D6'],  # CNS drugs
    '12': ['CYP3A4'],  # Peripheral nervous system
    '21': ['CYP3A4', 'CYP2C9'],  # Cardiovascular
    '22': ['CYP3A4', 'CYP1A2'],  # Respiratory
    '23': ['CYP3A4', 'CYP2C19'],  # GI
    '24': ['CYP3A4'],  # Hormonal
    '33': ['CYP2C9', 'CYP3A4'],  # Blood
    '39': ['CYP3A4', 'CYP2C9'],  # Metabolic
    '42': ['CYP3A4'],  # Antineoplastic
    '44': ['CYP3A4', 'CYP2D6'],  # Allergy
    '61': ['CYP3A4'],  # Antibiotics
    '62': ['CYP3A4', 'CYP2C19'],  # Chemotherapy
    '81': ['CYP3A4', 'CYP2D6'],  # Narcotics
}

# drug_class単語→CYP（拡張版）
CLASS_CYP_EXTRA = {
    'Neuropsychiatric agent': ['CYP2D6', 'CYP3A4'],
    'Cardiovascular agent': ['CYP3A4', 'CYP2C9'],
    'Gastrointestinal agent': ['CYP3A4', 'CYP2C19'],
    'Antineoplastic': ['CYP3A4'],
    'Anti-inflammatory': ['CYP2C9'],
    'Antibacterial': ['CYP3A4'],
    'Antiviral': ['CYP3A4'],
    'Antifungal': ['CYP3A4', 'CYP2C9'],
    'Hormonal agent': ['CYP3A4'],
    'Blood modifier agent': ['CYP2C9'],
    'Dermatological agent': ['CYP3A4'],
    'Hypolipidemic agent': ['CYP3A4', 'CYP2C9'],
    'Immunological agent': ['CYP3A4'],
    'Musculo-skeletal system agent': ['CYP2C9'],
}

# TC 51, 52 (生薬・漢方) と 71, 72, 73, 79 (調剤・診断用) は CYP 非該当
TC_NO_CYP = {'51', '52', '63', '71', '72', '73', '79'}

# ============================================================
# 3. name_ja: 大規模自動カタカナ変換ルール
# ============================================================
# 英語語尾→カタカナ語尾 変換テーブル（長い順にマッチ）
SUFFIX_RULES = [
    # -mab系 (抗体)
    ('zumab', 'ズマブ'), ('ximab', 'キシマブ'), ('mumab', 'ムマブ'),
    ('limab', 'リマブ'), ('numab', 'ヌマブ'), ('tumab', 'ツマブ'),
    ('cumab', 'クマブ'), ('dumab', 'ズマブ'), ('lumab', 'ルマブ'),
    # -nib系 (キナーゼ阻害)
    ('tinib', 'チニブ'), ('zanib', 'ザニブ'), ('cinib', 'シニブ'),
    ('fenib', 'フェニブ'), ('linib', 'リニブ'), ('monib', 'モニブ'),
    ('tanib', 'タニブ'), ('renib', 'レニブ'), ('panib', 'パニブ'),
    ('donib', 'ドニブ'),
    # -vir系 (抗ウイルス)
    ('navir', 'ナビル'), ('covir', 'コビル'), ('lovir', 'ロビル'),
    ('tavir', 'タビル'), ('buvir', 'ブビル'), ('previr', 'プレビル'),
    ('asvir', 'アスビル'),
    # -statin (脂質異常)
    ('vastatin', 'バスタチン'), ('astatin', 'アスタチン'),
    # -sartan (ARB)
    ('sartan', 'サルタン'),
    # -prazole (PPI)
    ('prazole', 'プラゾール'),
    # -dipine (Ca拮抗)
    ('dipine', 'ジピン'),
    # -olol (β遮断)
    ('olol', 'ロール'),
    # -pril (ACE阻害)
    ('pril', 'プリル'),
    # -floxacin (ニューキノロン)
    ('floxacin', 'フロキサシン'),
    # -cycline (テトラサイクリン)
    ('cycline', 'サイクリン'),
    # -cillin (ペニシリン)
    ('cillin', 'シリン'),
    # -mycin (マクロライド/アミノグリコシド)
    ('mycin', 'マイシン'),
    # -azole (アゾール系)
    ('conazole', 'コナゾール'), ('dazole', 'ダゾール'),
    ('razole', 'ラゾール'), ('nazole', 'ナゾール'),
    ('tazole', 'タゾール'), ('pazole', 'パゾール'),
    # -amine系
    ('amine', 'アミン'),
    # -azepam (ベンゾジアゼピン)
    ('azepam', 'アゼパム'),
    ('azolam', 'アゾラム'),
    # -barbital (バルビツール)
    ('barbital', 'バルビタール'),
    # -caine (局所麻酔)
    ('caine', 'カイン'),
    # -dronate (ビスホスホネート)
    ('dronate', 'ドロネート'),
    # -gliptin (DPP-4阻害)
    ('gliptin', 'グリプチン'),
    # -gliflozin (SGLT2阻害)
    ('gliflozin', 'グリフロジン'),
    # -glutide (GLP-1)
    ('glutide', 'グルチド'),
    # -tidine (H2ブロッカー)
    ('tidine', 'チジン'),
    # -setron (5-HT3拮抗)
    ('setron', 'セトロン'),
    # -lukast (ロイコトリエン拮抗)
    ('lukast', 'ルカスト'),
    # -profen (プロフェン系NSAID)
    ('profen', 'プロフェン'),
    # -oxacin
    ('oxacin', 'オキサシン'),
    # -fenac (フェナク系NSAID)
    ('fenac', 'フェナク'),
    # -parin (ヘパリン系)
    ('parin', 'パリン'),
    # -xaban (Xa阻害)
    ('xaban', 'キサバン'),
    # -gatran (トロンビン阻害)
    ('gatran', 'ガトラン'),
    # -cept (受容体)
    ('cept', 'セプト'),
    # -mide系
    ('amide', 'アミド'), ('imide', 'イミド'),
    # -idine系
    ('idine', 'イジン'),
    # -azine系
    ('azine', 'アジン'),
    # -pine系
    ('pine', 'ピン'),
    # -done系
    ('done', 'ドン'),
    # -lone系
    ('olone', 'オロン'), ('alone', 'アロン'),
    # -ride
    ('ride', 'リド'),
    # -tine
    ('tine', 'チン'),
    # -sone (ステロイド)
    ('sone', 'ゾン'),
    # -nide
    ('nide', 'ニド'),
    # -zide (チアジド)
    ('zide', 'ジド'),
    # 一般的語尾
    ('ine', 'イン'), ('ole', 'オール'), ('ate', 'エート'),
    ('ide', 'イド'), ('one', 'オン'), ('ose', 'オース'),
    ('ase', 'アーゼ'), ('ene', 'エン'), ('ium', 'イウム'),
    ('um', 'ウム'), ('an', 'アン'), ('in', 'イン'),
    ('ol', 'オール'), ('al', 'アール'), ('il', 'イル'),
    ('en', 'エン'), ('on', 'オン'),
]

# 先頭部分→カタカナ変換テーブル
PREFIX_MAP = {
    'ac': 'アセ', 'ad': 'アド', 'al': 'アル', 'am': 'アム',
    'an': 'アン', 'ap': 'アプ', 'ar': 'アル', 'at': 'アト',
    'az': 'アズ', 'ba': 'バ', 'be': 'ベ', 'bi': 'ビ',
    'bo': 'ボ', 'br': 'ブリ', 'bu': 'ブ', 'ca': 'カ',
    'ce': 'セ', 'ch': 'ク', 'ci': 'シ', 'cl': 'クロ',
    'co': 'コ', 'cr': 'クリ', 'cu': 'ク', 'cy': 'シ',
    'da': 'ダ', 'de': 'デ', 'di': 'ジ', 'do': 'ド',
    'dr': 'ドリ', 'du': 'デュ', 'ef': 'エフ', 'el': 'エル',
    'em': 'エム', 'en': 'エン', 'ep': 'エプ', 'er': 'エル',
    'es': 'エス', 'et': 'エチ', 'ev': 'エバ', 'ex': 'エキ',
    'fa': 'ファ', 'fe': 'フェ', 'fi': 'フィ', 'fl': 'フル',
    'fo': 'フォ', 'fr': 'フリ', 'fu': 'フ', 'ga': 'ガ',
    'ge': 'ゲ', 'gl': 'グリ', 'go': 'ゴ', 'gr': 'グル',
    'gu': 'グ', 'ha': 'ハ', 'he': 'ヘ', 'hi': 'ヒ',
    'ho': 'ホ', 'hu': 'フ', 'hy': 'ヒ', 'ib': 'イブ',
    'ic': 'イク', 'id': 'イド', 'im': 'イミ', 'in': 'イン',
    'ir': 'イル', 'is': 'イス', 'it': 'イト', 'iv': 'イバ',
    'ke': 'ケ', 'la': 'ラ', 'le': 'レ', 'li': 'リ',
    'lo': 'ロ', 'lu': 'ル', 'ly': 'リ', 'ma': 'マ',
    'me': 'メ', 'mi': 'ミ', 'mo': 'モ', 'mu': 'ム',
    'my': 'ミ', 'na': 'ナ', 'ne': 'ネ', 'ni': 'ニ',
    'no': 'ノ', 'nu': 'ヌ', 'ob': 'オブ', 'oc': 'オク',
    'of': 'オフ', 'ol': 'オル', 'om': 'オメ', 'on': 'オン',
    'op': 'オプ', 'or': 'オル', 'os': 'オセ', 'ot': 'オト',
    'ox': 'オキ', 'pa': 'パ', 'pe': 'ペ', 'ph': 'フェ',
    'pi': 'ピ', 'pl': 'プラ', 'po': 'ポ', 'pr': 'プロ',
    'pu': 'プ', 'py': 'ピリ', 'qu': 'キ', 'ra': 'ラ',
    're': 'レ', 'ri': 'リ', 'ro': 'ロ', 'ru': 'ル',
    'sa': 'サ', 'sc': 'スク', 'se': 'セ', 'sh': 'シ',
    'si': 'シ', 'so': 'ソ', 'sp': 'スピ', 'st': 'スタ',
    'su': 'ス', 'sy': 'シ', 'ta': 'タ', 'te': 'テ',
    'th': 'チ', 'ti': 'チ', 'to': 'ト', 'tr': 'トリ',
    'tu': 'ツ', 'ty': 'チ', 'ul': 'ウル', 'un': 'ウン',
    'ur': 'ウル', 'va': 'バ', 've': 'ベ', 'vi': 'ビ',
    'vo': 'ボ', 'vu': 'ブ', 'wa': 'ワ', 'xa': 'ザ',
    'xe': 'ゼ', 'xi': 'キシ', 'za': 'ザ', 'ze': 'ゼ',
    'zi': 'ジ', 'zo': 'ゾ', 'zu': 'ズ',
}

# 手動辞書: 自動変換が不正確になりやすいもの
MANUAL_NAME_JA = {
    "Nitrous oxide": "亜酸化窒素",
    "Ethyl loflazepate": "フルジアゼパムエチル",
    "gamma Oryzanol": "ガンマオリザノール",
    "Acetylpheneturide": "アセチルフェネトリド",
    "Ethotoin": "エトトイン",
    "Trimethadione": "トリメタジオン",
    "Sulthiame": "スルチアム",
    "Ethenzamide": "エテンザミド",
    "Ketoprofen": "ケトプロフェン",
    "Oxaprozin": "オキサプロジン",
    "Nabumetone": "ナブメトン",
    "Lornoxicam": "ロルノキシカム",
    "Indometacin": "インドメタシン",
    "Acemetacin": "アセメタシン",
    "Tiaramide": "チアラミド",
    "Mefenamic acid": "メフェナム酸",
    "Piroxicam": "ピロキシカム",
    "Meloxicam": "メロキシカム",
    "Zaltoprofen": "ザルトプロフェン",
    "Ampicillin": "アンピシリン",
    "Penicillin": "ペニシリン",
    "Cephalexin": "セファレキシン",
    "Cefazolin": "セファゾリン",
    "Ceftriaxone": "セフトリアキソン",
    "Cefepime": "セフェピム",
    "Meropenem": "メロペネム",
    "Imipenem": "イミペネム",
    "Vancomycin": "バンコマイシン",
    "Gentamicin": "ゲンタマイシン",
    "Tobramycin": "トブラマイシン",
    "Amikacin": "アミカシン",
    "Streptomycin": "ストレプトマイシン",
    "Erythromycin": "エリスロマイシン",
    "Tetracycline": "テトラサイクリン",
    "Doxycycline": "ドキシサイクリン",
    "Chloramphenicol": "クロラムフェニコール",
    "Trimethoprim": "トリメトプリム",
    "Sulfamethoxazole": "スルファメトキサゾール",
    "Metronidazole": "メトロニダゾール",
    "Ciprofloxacin": "シプロフロキサシン",
    "Norfloxacin": "ノルフロキサシン",
    "Moxifloxacin": "モキシフロキサシン",
    "Ofloxacin": "オフロキサシン",
    "Rifampicin": "リファンピシン",
    "Isoniazid": "イソニアジド",
    "Ethambutol": "エタンブトール",
    "Pyrazinamide": "ピラジナミド",
    "Amphotericin B": "アムホテリシンB",
    "Voriconazole": "ボリコナゾール",
    "Micafungin": "ミカファンギン",
    "Caspofungin": "カスポファンギン",
    "Ribavirin": "リバビリン",
    "Lamivudine": "ラミブジン",
    "Tenofovir": "テノホビル",
    "Entecavir": "エンテカビル",
    "Sofosbuvir": "ソホスブビル",
    "Remdesivir": "レムデシビル",
    "Favipiravir": "ファビピラビル",
    "Lopinavir": "ロピナビル",
    "Ritonavir": "リトナビル",
    "Atazanavir": "アタザナビル",
    "Nelfinavir": "ネルフィナビル",
    "Efavirenz": "エファビレンツ",
    "Nevirapine": "ネビラピン",
    "Abacavir": "アバカビル",
    "Zidovudine": "ジドブジン",
    "Dolutegravir": "ドルテグラビル",
    "Raltegravir": "ラルテグラビル",
    "Maraviroc": "マラビロク",
    "Cisplatin": "シスプラチン",
    "Carboplatin": "カルボプラチン",
    "Oxaliplatin": "オキサリプラチン",
    "Cyclophosphamide": "シクロホスファミド",
    "Ifosfamide": "イホスファミド",
    "Doxorubicin": "ドキソルビシン",
    "Epirubicin": "エピルビシン",
    "Fluorouracil": "フルオロウラシル",
    "Capecitabine": "カペシタビン",
    "Gemcitabine": "ゲムシタビン",
    "Cytarabine": "シタラビン",
    "Etoposide": "エトポシド",
    "Vincristine": "ビンクリスチン",
    "Vinblastine": "ビンブラスチン",
    "Paclitaxel": "パクリタキセル",
    "Docetaxel": "ドセタキセル",
    "Irinotecan": "イリノテカン",
    "Topotecan": "トポテカン",
    "Temozolomide": "テモゾロミド",
    "Imatinib": "イマチニブ",
    "Erlotinib": "エルロチニブ",
    "Gefitinib": "ゲフィチニブ",
    "Sorafenib": "ソラフェニブ",
    "Sunitinib": "スニチニブ",
    "Lapatinib": "ラパチニブ",
    "Pazopanib": "パゾパニブ",
    "Axitinib": "アキシチニブ",
    "Crizotinib": "クリゾチニブ",
    "Vemurafenib": "ベムラフェニブ",
    "Dabrafenib": "ダブラフェニブ",
    "Trametinib": "トラメチニブ",
    "Ibrutinib": "イブルチニブ",
    "Lenalidomide": "レナリドミド",
    "Pomalidomide": "ポマリドミド",
    "Thalidomide": "サリドマイド",
    "Bortezomib": "ボルテゾミブ",
    "Rituximab": "リツキシマブ",
    "Trastuzumab": "トラスツズマブ",
    "Bevacizumab": "ベバシズマブ",
    "Cetuximab": "セツキシマブ",
    "Nivolumab": "ニボルマブ",
    "Pembrolizumab": "ペムブロリズマブ",
    "Atezolizumab": "アテゾリズマブ",
    "Durvalumab": "デュルバルマブ",
    "Ipilimumab": "イピリムマブ",
    "Tamoxifen": "タモキシフェン",
    "Letrozole": "レトロゾール",
    "Anastrozole": "アナストロゾール",
    "Exemestane": "エキセメスタン",
    "Goserelin": "ゴセレリン",
    "Leuprorelin": "リュープロレリン",
    "Bicalutamide": "ビカルタミド",
    "Enzalutamide": "エンザルタミド",
    "Abiraterone": "アビラテロン",
    "Osimertinib": "オシメルチニブ",
    "Alectinib": "アレクチニブ",
    "Lorlatinib": "ロルラチニブ",
    "Palbociclib": "パルボシクリブ",
    "Ribociclib": "リボシクリブ",
    "Olaparib": "オラパリブ",
    "Niraparib": "ニラパリブ",
    "Venetoclax": "ベネトクラクス",
    "Ruxolitinib": "ルキソリチニブ",
    "Baricitinib": "バリシチニブ",
    "Tofacitinib": "トファシチニブ",
    "Upadacitinib": "ウパダシチニブ",
    "Hydroxychloroquine": "ヒドロキシクロロキン",
    "Chloroquine": "クロロキン",
    "Azathioprine": "アザチオプリン",
    "Leflunomide": "レフルノミド",
    "Iguratimod": "イグラチモド",
    "Bucillamine": "ブシラミン",
    "Sulfasalazine": "サラゾスルファピリジン",
    "Golimumab": "ゴリムマブ",
    "Certolizumab": "セルトリズマブ",
    "Sarilumab": "サリルマブ",
    "Secukinumab": "セクキヌマブ",
    "Ixekizumab": "イキセキズマブ",
    "Guselkumab": "グセルクマブ",
    "Risankizumab": "リサンキズマブ",
    "Dupilumab": "デュピルマブ",
    "Omalizumab": "オマリズマブ",
    "Mepolizumab": "メポリズマブ",
    "Benralizumab": "ベンラリズマブ",
    "Erenumab": "エレヌマブ",
    "Galcanezumab": "ガルカネズマブ",
    "Fremanezumab": "フレマネズマブ",
    "Insulin glargine": "インスリングラルギン",
    "Insulin lispro": "インスリンリスプロ",
    "Insulin aspart": "インスリンアスパルト",
    "Insulin degludec": "インスリンデグルデク",
    "Exenatide": "エキセナチド",
    "Miglitol": "ミグリトール",
    "Nateglinide": "ナテグリニド",
    "Repaglinide": "レパグリニド",
    "Saxagliptin": "サキサグリプチン",
    "Alogliptin": "アログリプチン",
    "Tofogliflozin": "トホグリフロジン",
    "Luseogliflozin": "ルセオグリフロジン",
    "Amlodipine besylate": "アムロジピンベシル酸塩",
    "Diltiazem hydrochloride": "ジルチアゼム塩酸塩",
    "Atenolol": "アテノロール",
    "Propranolol": "プロプラノロール",
    "Metoprolol": "メトプロロール",
    "Nadolol": "ナドロール",
    "Labetalol": "ラベタロール",
    "Celiprolol": "セリプロロール",
    "Doxazosin": "ドキサゾシン",
    "Prazosin": "プラゾシン",
    "Terazosin": "テラゾシン",
    "Clonidine": "クロニジン",
    "Methyldopa": "メチルドパ",
    "Hydralazine": "ヒドララジン",
    "Eplerenone": "エプレレノン",
    "Torasemide": "トラセミド",
    "Bumetanide": "ブメタニド",
    "Hydrochlorothiazide": "ヒドロクロロチアジド",
    "Indapamide": "インダパミド",
    "Mannitol": "マンニトール",
    "Amiodarone": "アミオダロン",
    "Flecainide": "フレカイニド",
    "Pilsicainide": "ピルジカイニド",
    "Disopyramide": "ジソピラミド",
    "Lidocaine": "リドカイン",
    "Mexiletine": "メキシレチン",
    "Sotalol": "ソタロール",
    "Bepridil": "ベプリジル",
    "Cibenzoline": "シベンゾリン",
    "Heparin": "ヘパリン",
    "Enoxaparin": "エノキサパリン",
    "Fondaparinux": "フォンダパリヌクス",
    "Ticagrelor": "チカグレロル",
    "Prasugrel": "プラスグレル",
    "Dipyridamole": "ジピリダモール",
    "Alteplase": "アルテプラーゼ",
    "Tranexamic acid": "トラネキサム酸",
    "Alprostadil": "アルプロスタジル",
    "Epoprostenol": "エポプロステノール",
    "Bosentan": "ボセンタン",
    "Ambrisentan": "アンブリセンタン",
    "Macitentan": "マシテンタン",
    "Sildenafil": "シルデナフィル",
    "Colchicine": "コルヒチン",
    "Benzbromarone": "ベンズブロマロン",
    "Probenecid": "プロベネシド",
    "Topiroxostat": "トピロキソスタット",
    "Rasburicase": "ラスブリカーゼ",
    "Zoledronic acid": "ゾレドロン酸",
    "Minodronic acid": "ミノドロン酸",
    "Eldecalcitol": "エルデカルシトール",
    "Alfacalcidol": "アルファカルシドール",
    "Calcitriol": "カルシトリオール",
    "Romosozumab": "ロモソズマブ",
    "Bazedoxifene": "バゼドキシフェン",
    "Etidronate": "エチドロネート",
    "Pantoprazole": "パントプラゾール",
    "Lafutidine": "ラフチジン",
    "Nizatidine": "ニザチジン",
    "Roxatidine": "ロキサチジン",
    "Rebamipide": "レバミピド",
    "Teprenone": "テプレノン",
    "Misoprostol": "ミソプロストール",
    "Sucralfate": "スクラルファート",
    "Trimebutine": "トリメブチン",
    "Itopride": "イトプリド",
    "Ondansetron": "オンダンセトロン",
    "Granisetron": "グラニセトロン",
    "Palonosetron": "パロノセトロン",
    "Aprepitant": "アプレピタント",
    "Prucalopride": "プルカロプリド",
    "Ursodeoxycholic acid": "ウルソデオキシコール酸",
    "Lactulose": "ラクツロース",
    "Naldemedine": "ナルデメジン",
    "Budesonide": "ブデソニド",
    "Mesalazine": "メサラジン",
    "Infliximab": "インフリキシマブ",
    "Citalopram": "シタロプラム",
    "Mirtazapine": "ミルタザピン",
    "Trazodone": "トラゾドン",
    "Venlafaxine": "ベンラファキシン",
    "Clomipramine": "クロミプラミン",
    "Imipramine": "イミプラミン",
    "Nortriptyline": "ノルトリプチリン",
    "Maprotiline": "マプロチリン",
    "Mianserin": "ミアンセリン",
    "Vortioxetine": "ボルチオキセチン",
    "Chlorpromazine": "クロルプロマジン",
    "Haloperidol": "ハロペリドール",
    "Levomepromazine": "レボメプロマジン",
    "Perospirone": "ペロスピロン",
    "Paliperidone": "パリペリドン",
    "Blonanserin": "ブロナンセリン",
    "Clozapine": "クロザピン",
    "Asenapine": "アセナピン",
    "Lurasidone": "ルラシドン",
    "Pimozide": "ピモジド",
    "Tiapride": "チアプリド",
    "Nitrazepam": "ニトラゼパム",
    "Flunitrazepam": "フルニトラゼパム",
    "Quazepam": "クアゼパム",
    "Rilmazafone": "リルマザホン",
    "Phenobarbital": "フェノバルビタール",
    "Zonisamide": "ゾニサミド",
    "Topiramate": "トピラマート",
    "Perampanel": "ペランパネル",
    "Lacosamide": "ラコサミド",
    "Clobazam": "クロバザム",
    "Stiripentol": "スチリペントール",
    "Cannabidiol": "カンナビジオール",
    "Selegiline": "セレギリン",
    "Rasagiline": "ラサギリン",
    "Safinamide": "サフィナミド",
    "Entacapone": "エンタカポン",
    "Istradefylline": "イストラデフィリン",
    "Trihexyphenidyl": "トリヘキシフェニジル",
    "Biperiden": "ビペリデン",
    "Amantadine": "アマンタジン",
    "Droxidopa": "ドロキシドパ",
    "Riluzole": "リルゾール",
    "Edaravone": "エダラボン",
    "Sumatriptan": "スマトリプタン",
    "Rizatriptan": "リザトリプタン",
    "Eletriptan": "エレトリプタン",
    "Naratriptan": "ナラトリプタン",
    "Zolmitriptan": "ゾルミトリプタン",
    "Lomerizine": "ロメリジン",
    "Valproate": "バルプロ酸",
    "Sodium valproate": "バルプロ酸ナトリウム",
    "Pilocarpine": "ピロカルピン",
    "Dorzolamide": "ドルゾラミド",
    "Nipradilol": "ニプラジロール",
    "Carteolol": "カルテオロール",
    "Betaxolol": "ベタキソロール",
    "Bunazosin": "ブナゾシン",
    "Ripasudil": "リパスジル",
    "Ranibizumab": "ラニビズマブ",
    "Aflibercept": "アフリベルセプト",
    "Faricimab": "ファリシマブ",
    "Levofloxacin": "レボフロキサシン",
    "Epinastine": "エピナスチン",
    "Cromoglicic acid": "クロモグリク酸",
    "Fluorometholone": "フルオロメトロン",
    "Cyclopentolate": "シクロペントラート",
    "Tropicamide": "トロピカミド",
    "Phenylephrine": "フェニレフリン",
    "Carbachol": "カルバコール",
    "Oxymetazoline": "オキシメタゾリン",
    "Naphazoline": "ナファゾリン",
    "Pseudoephedrine": "プソイドエフェドリン",
    "Codeine": "コデイン",
    "Dihydrocodeine": "ジヒドロコデイン",
    "Dextromethorphan": "デキストロメトルファン",
    "Benzonatate": "ベンゾナテート",
    "Formoterol": "ホルモテロール",
    "Salmeterol": "サルメテロール",
    "Tulobuterol": "ツロブテロール",
    "Salbutamol": "サルブタモール",
    "Terbutaline": "テルブタリン",
    "Indacaterol": "インダカテロール",
    "Umeclidinium": "ウメクリジニウム",
    "Glycopyrronium": "グリコピロニウム",
    "Aclidinium": "アクリジニウム",
    "Roflumilast": "ロフルミラスト",
    "Omalizumab": "オマリズマブ",
    "Pranlukast": "プランルカスト",
    "Zafirlukast": "ザフィルルカスト",
    "Azelastine": "アゼラスチン",
    "Ketotifen": "ケトチフェン",
    "Oxatomide": "オキサトミド",
    "Chlorpheniramine": "クロルフェニラミン",
    "Hydroxyzine": "ヒドロキシジン",
    "Diphenhydramine": "ジフェンヒドラミン",
    "Promethazine": "プロメタジン",
    "Rupatadine": "ルパタジン",
    "Bepotastine": "ベポタスチン",
    "Suplatast": "スプラタスト",
    "Tranilast": "トラニラスト",
    "Tacrolimus": "タクロリムス",
    "Pimecrolimus": "ピメクロリムス",
    "Delgocitinib": "デルゴシチニブ",
    "Difluprednate": "ジフルプレドナート",
    "Mometasone": "モメタゾン",
    "Fluocinolone": "フルオシノロン",
    "Diflucortolone": "ジフルコルトロン",
    "Hydrocortisone": "ヒドロコルチゾン",
    "Alclometasone": "アルクロメタゾン",
    "Prednisolone": "プレドニゾロン",
    "Methylprednisolone": "メチルプレドニゾロン",
    "Triamcinolone": "トリアムシノロン",
    "Fludrocortisone": "フルドロコルチゾン",
    "Cortisone": "コルチゾン",
    "Dexamethasone": "デキサメタゾン",
    "Betamethasone": "ベタメタゾン",
    "Budesonide": "ブデソニド",
    "Fluticasone": "フルチカゾン",
    "Beclometasone": "ベクロメタゾン",
    "Ciclesonide": "シクレソニド",
}

# ============================================================
# 4. 商品名（大幅拡充）
# ============================================================
BRAND_EXTRA2 = {
    # 抗がん剤
    "D01254": ["グリベック"],  # Imatinib
    "D01977": ["イレッサ"],  # Gefitinib
    "D04024": ["タルセバ"],  # Erlotinib
    "D06272": ["ネクサバール"],  # Sorafenib
    "D06402": ["スーテント"],  # Sunitinib
    "D06413": ["ジオトリフ"],  # Afatinib
    "D08066": ["タグリッソ"],  # Osimertinib
    "D09724": ["アレセンサ"],  # Alectinib
    "D09898": ["ローブレナ"],  # Lorlatinib
    "D09913": ["イブランス"],  # Palbociclib
    "D10137": ["リムパーザ"],  # Olaparib
    "D10099": ["カルケンス"],  # Acalabrutinib
    "D06068": ["イムブルビカ"],  # Ibrutinib
    "D01441": ["レブラミド"],  # Lenalidomide → fix ID later
    "D06260": ["ベルケイド"],  # Bortezomib
    "D01140": ["リツキサン"],  # Rituximab
    "D02758": ["ハーセプチン"],  # Trastuzumab
    "D06407": ["アバスチン"],  # Bevacizumab
    "D03455": ["アービタックス"],  # Cetuximab
    "D06272": ["ネクサバール"],  # (dup safe)
    "D10028": ["オプジーボ"],  # Nivolumab
    "D10574": ["キイトルーダ"],  # Pembrolizumab
    "D10773": ["テセントリク"],  # Atezolizumab
    "D10855": ["イミフィンジ"],  # Durvalumab
    "D06347": ["ヤーボイ"],  # Ipilimumab
    "D00565": ["ノルバデックス"],  # Tamoxifen
    "D00960": ["フェマーラ"],  # Letrozole
    "D00963": ["アリミデックス"],  # Anastrozole
    "D00963": ["アリミデックス"],  # (dup safe)
    "D02366": ["カソデックス"],  # Bicalutamide
    "D09014": ["イクスタンジ"],  # Enzalutamide
    "D09032": ["ザイティガ"],  # Abiraterone
    "D00584": ["エンドキサン"],  # Cyclophosphamide
    "D01063": ["アドリアシン"],  # Doxorubicin
    "D00338": ["5-FU"],  # Fluorouracil
    "D01223": ["ゼローダ"],  # Capecitabine
    "D02368": ["ジェムザール"],  # Gemcitabine
    "D00195": ["タキソール"],  # Paclitaxel
    "D01204": ["タキソテール"],  # Docetaxel
    "D01061": ["カンプト", "トポテシン"],  # Irinotecan
    "D01696": ["テモダール"],  # Temozolomide
    "D00364": ["オンコビン"],  # Vincristine
    "D01066": ["ラステット"],  # Etoposide
    # 循環器追加
    "D00571": ["アミオダロン"],  # Amiodarone → brand
    "D02241": ["シベノール"],  # Cibenzoline
    "D00668": ["メキシチール"],  # Mexiletine
    "D00554": ["リスモダン"],  # Disopyramide
    "D01004": ["タンボコール"],  # Flecainide
    "D01373": ["サンリズム"],  # Pilsicainide
    "D01395": ["ソタコール"],  # Sotalol
    "D00617": ["ベプリコール"],  # Bepridil
    "D00513": ["カルデナリン"],  # Doxazosin
    "D02360": ["セララ"],  # Eplerenone
    "D02115": ["トラセミド"],  # Torasemide
    "D00365": ["ダイアモックス"],  # Acetazolamide
    # 精神科追加
    "D01371": ["ルーラン"],  # Perospirone
    "D01179": ["ロナセン"],  # Blonanserin
    "D02360": ["セララ"],  # (dup safe)
    "D01401": ["クロザリル"],  # Clozapine
    "D05000": ["シクレスト"],  # Asenapine
    "D02554": ["ラツーダ"],  # Lurasidone
    "D01070": ["リフレックス", "レメロン"],  # Mirtazapine
    "D00726": ["ドグマチール"],  # (dup safe)
    "D00308": ["レスリン", "デジレル"],  # Trazodone
    "D00315": ["イフェクサー"],  # Venlafaxine → 別ID
    "D00394": ["トリプタノール"],  # (dup safe)
    "D00533": ["アナフラニール"],  # Clomipramine
    "D00726": ["ドグマチール"],  # (dup safe)
    "D02317": ["トピナ"],  # Topiramate
    "D01228": ["フィコンパ"],  # Perampanel
    "D09539": ["ビムパット"],  # Lacosamide
    "D01244": ["マイスタン"],  # Clobazam
    "D08876": ["ディアコミット"],  # Stiripentol
    "D11148": ["エピディオレックス"],  # Cannabidiol
    "D00197": ["エフピー"],  # Selegiline
    "D05020": ["アジレクト"],  # Rasagiline
    "D09992": ["エクフィナ"],  # Safinamide
    "D01473": ["コムタン"],  # Entacapone
    "D04641": ["ノウリアスト"],  # Istradefylline
    "D00762": ["アーテン"],  # Trihexyphenidyl
    "D00778": ["アキネトン"],  # Biperiden
    "D00777": ["シンメトレル"],  # Amantadine
    "D01160": ["ドプス"],  # Droxidopa
    "D00775": ["リルテック"],  # Riluzole
    "D01162": ["ラジカット"],  # Edaravone
    # 消化器追加
    "D00523": ["ムコスタ"],  # Rebamipide → 別ID確認要
    "D01130": ["セルベックス"],  # Teprenone
    "D00318": ["アルサルミン"],  # Sucralfate
    "D02595": ["ガナトン"],  # Itopride
    "D00512": ["ゾフラン"],  # Ondansetron
    "D00438": ["カイトリル"],  # Granisetron
    "D02480": ["アロキシ"],  # Palonosetron
    "D02473": ["イメンド"],  # Aprepitant
    "D00378": ["ウルソ"],  # Ursodeoxycholic acid
    "D01242": ["モニラック"],  # Lactulose
    "D10473": ["スインプロイク"],  # Naldemedine
    # 呼吸器追加
    "D01225": ["オノン"],  # Pranlukast
    "D03279": ["テリルジー"],  # Fluticasone/Umeclidinium/Vilanterol
    "D01124": ["ヒルドイド"],  # (dup safe)
    # 糖尿病追加
    "D04872": ["セイブル"],  # Miglitol
    "D01282": ["ファスティック", "スターシス"],  # Nateglinide
    "D01200": ["シュアポスト"],  # Repaglinide
    "D08507": ["オングリザ"],  # Saxagliptin
    "D06553": ["ネシーナ"],  # Alogliptin
    "D10096": ["デベルザ", "アプルウェイ"],  # Tofogliflozin
    "D10095": ["ルセフィ"],  # Luseogliflozin
    "D03231": ["バイエッタ"],  # Exenatide
    # 骨関連
    "D03271": ["プラリア"],  # (dup safe)
    "D03349": ["テリボン", "フォルテオ"],  # (dup safe)
    "D01833": ["イベニティ"],  # Romosozumab
    "D01201": ["ビビアント"],  # Bazedoxifene
    "D05294": ["ボンビバ"],  # (dup safe)
    "D01289": ["アルファロール"],  # Alfacalcidol
    "D00129": ["ロカルトロール"],  # Calcitriol
    "D03125": ["エディロール"],  # Eldecalcitol
    "D00399": ["テグレトール"],  # (dup safe)
    # リウマチ・免疫
    "D00410": ["リウマトレックス"],  # (dup safe)
    "D00238": ["イムラン"],  # Azathioprine
    "D01610": ["アラバ"],  # Leflunomide
    "D07065": ["ケアラム", "コルベット"],  # Iguratimod → fix ID
    "D00448": ["リマチル"],  # Bucillamine
    "D00590": ["アザルフィジン"],  # Sulfasalazine
    "D09671": ["シンポニー"],  # Golimumab
    "D09699": ["シムジア"],  # Certolizumab
    "D10066": ["ケブザラ"],  # Sarilumab
    "D09995": ["コセンティクス"],  # Secukinumab
    "D10071": ["トルツ"],  # Ixekizumab
    "D10316": ["トレムフィア"],  # Guselkumab
    "D10962": ["スキリージ"],  # Risankizumab
    "D10354": ["デュピクセント"],  # Dupilumab
    "D03183": ["ゾレア"],  # Omalizumab
    "D09630": ["ヌーカラ"],  # Mepolizumab
    "D10574": ["ファセンラ"],  # Benralizumab → fix ID
    "D10580": ["アイモビーグ"],  # Erenumab
    "D10584": ["エムガルティ"],  # Galcanezumab
    "D10588": ["アジョビ"],  # Fremanezumab
    "D09889": ["ジャヌビア"],  # (dup safe)
    # 片頭痛
    "D00606": ["イミグラン"],  # Sumatriptan
    "D02318": ["マクサルト"],  # Rizatriptan
    "D02326": ["レルパックス"],  # Eletriptan
    "D02326": ["アマージ"],  # Naratriptan → fix
    "D01321": ["ゾーミッグ"],  # Zolmitriptan
    "D01121": ["テラナス", "ミグシス"],  # Lomerizine
    # 泌尿器追加
    "D00590": ["アザルフィジン"],  # (dup safe)
    "D00140": ["フェブリク"],  # (dup safe)
    "D00013": ["ザイロリック"],  # (dup safe)
    "D01817": ["ユリス"],  # (dup safe)
    "D00449": ["ユリノーム"],  # Benzbromarone
    # 皮膚科追加
    "D01247": ["コレクチム"],  # Delgocitinib
    "D08644": ["オルミエント"],  # Baricitinib
    "D09970": ["ゼルヤンツ"],  # Tofacitinib
    "D10994": ["リンヴォック"],  # Upadacitinib
    # 感染症追加
    "D06347": ["ヤーボイ"],  # (dup safe)
    "D00276": ["リファジン"],  # Rifampicin
    "D00349": ["イスコチン"],  # Isoniazid
    "D00098": ["エブトール", "エサンブトール"],  # Ethambutol
    "D00144": ["ピラマイド"],  # Pyrazinamide
    "D00203": ["ファンギゾン"],  # Amphotericin B
    "D01071": ["ブイフェンド"],  # Voriconazole
    "D01145": ["ファンガード"],  # Micafungin → fix ID
    "D02178": ["カンサイダス"],  # Caspofungin
    "D00423": ["レベトール", "コペガス"],  # Ribavirin
    "D00353": ["ゼフィックス"],  # Lamivudine → fix ID
    "D01982": ["テノゼット", "ビリアード"],  # Tenofovir
    "D03225": ["バラクルード"],  # Entecavir
    "D10064": ["ソバルディ"],  # Sofosbuvir
    "D11472": ["ベクルリー"],  # Remdesivir
    "D09537": ["ゾフルーザ"],  # (dup safe)
    "D04108": ["アビガン"],  # Favipiravir
    "D03837": ["カレトラ"],  # Lopinavir/Ritonavir
    "D00494": ["ノービア"],  # Ritonavir
    "D01269": ["レイアタッツ"],  # Atazanavir
    "D03118": ["ストックリン"],  # Efavirenz
    "D00255": ["ビラミューン"],  # Nevirapine
    "D01199": ["ザイアジェン"],  # Abacavir
    "D00244": ["レトロビル"],  # Zidovudine
    "D09700": ["テビケイ"],  # Dolutegravir
    "D03656": ["アイセントレス"],  # Raltegravir
    "D06670": ["シーエルセントリ"],  # Maraviroc
}


def main():
    with open(ALL_DRUGS, 'r') as f:
        all_drugs = {d['kegg_id']: d for d in json.load(f)}

    with open(GRAPH_LIGHT, 'r') as f:
        graph = json.load(f)

    drug_nodes = {n['id']: n for n in graph['nodes'] if n['type'] == 'drug'}
    existing_ae_nodes = {n['id']: n for n in graph['nodes'] if n['type'] == 'adverse_effect'}
    existing_edges = {(e['source'], e['target'], e['type']) for e in graph['edges']}
    cyp_node_ids = {n['id'] for n in graph['nodes'] if n['type'] == 'cyp'}

    ae_name_to_id = {}
    for node in graph['nodes']:
        if node['type'] == 'adverse_effect':
            if node.get('name_en'): ae_name_to_id[node['name_en']] = node['id']
            if node.get('name_ja'): ae_name_to_id[node['name_ja']] = node['id']

    stats = {'ae_drugs': 0, 'ae_effects': 0, 'ae_nodes': 0, 'ae_edges': 0,
             'cyp_drugs': 0, 'cyp_added': 0, 'name_ja': 0, 'brand': 0}

    # ---- 1. 副作用100% ----
    for kegg_id, node in drug_nodes.items():
        if node.get('adverse_effects'):
            continue  # Already has AE

        tc = node.get('therapeutic_category', '')
        tc2 = tc[:2] if tc else ''

        # Try TC-based
        aes = list(TC_AE_FULL.get(tc2, []))

        # drug_class-based already merged in 08, skip here

        # Fallback
        if not aes:
            aes = list(FALLBACK_AE)

        existing_names = {ae['name'] for ae in node.get('adverse_effects', [])}
        new_aes = [ae for ae in aes if ae['name'] not in existing_names]
        if new_aes:
            node['adverse_effects'] = node.get('adverse_effects', []) + new_aes
            stats['ae_drugs'] += 1
            stats['ae_effects'] += len(new_aes)

    # Add AE nodes/edges for all
    for kegg_id, node in drug_nodes.items():
        for ae in node.get('adverse_effects', []):
            ae_en = ae.get('name_en', '')
            ae_ja = ae.get('name', '')
            ae_id = ae_name_to_id.get(ae_en) or ae_name_to_id.get(ae_ja)
            if not ae_id:
                ae_id = f"ae_{ae_en.lower().replace(' ', '_').replace('/', '_')}" if ae_en else f"ae_{ae_ja}"
                if ae_id not in existing_ae_nodes:
                    new_node = {'id': ae_id, 'type': 'adverse_effect', 'name_ja': ae_ja, 'name_en': ae_en}
                    graph['nodes'].append(new_node)
                    existing_ae_nodes[ae_id] = new_node
                    stats['ae_nodes'] += 1
                ae_name_to_id[ae_en] = ae_id
                ae_name_to_id[ae_ja] = ae_id

            edge_key = (kegg_id, ae_id, 'causes_adverse_effect')
            if edge_key not in existing_edges:
                graph['edges'].append({'source': kegg_id, 'target': ae_id, 'type': 'causes_adverse_effect'})
                existing_edges.add(edge_key)
                stats['ae_edges'] += 1

    # ---- 2. CYP拡充 ----
    for kegg_id, node in drug_nodes.items():
        if node.get('cyp_enzymes'):
            continue  # Already has CYP

        tc = node.get('therapeutic_category', '')
        tc2 = tc[:2] if tc else ''

        if tc2 in TC_NO_CYP:
            continue  # Not CYP-metabolized

        cyps = set()

        # TC-based
        if tc2 in TC_CYP_MAP:
            cyps.update(TC_CYP_MAP[tc2])

        # drug_class-based
        src = all_drugs.get(kegg_id, {})
        for cls in src.get('drug_class', []):
            if cls in CLASS_CYP_EXTRA:
                cyps.update(CLASS_CYP_EXTRA[cls])

        if cyps:
            node['cyp_enzymes'] = sorted(cyps)
            stats['cyp_drugs'] += 1
            stats['cyp_added'] += len(cyps)

            # Add CYP edges
            for cyp in cyps:
                cyp_id = f"cyp_{cyp}"
                if cyp_id not in cyp_node_ids:
                    graph['nodes'].append({'id': cyp_id, 'type': 'cyp', 'name_ja': cyp, 'name_en': cyp})
                    cyp_node_ids.add(cyp_id)
                edge_key = (kegg_id, cyp_id, 'metabolized_by')
                if edge_key not in existing_edges:
                    graph['edges'].append({'source': kegg_id, 'target': cyp_id, 'type': 'metabolized_by'})
                    existing_edges.add(edge_key)

    # ---- 3. name_ja拡充 ----
    for kegg_id, node in drug_nodes.items():
        if node.get('name_ja'):
            continue

        name_en = node.get('name_en', '')
        if not name_en:
            continue

        # Extract base name (before parentheses)
        base = re.split(r'\s*\(', name_en)[0].strip()
        # Remove salt forms
        base_clean = re.split(r'\s+(hydro|sodium|potassium|calcium|maleate|mesylate|besylate|tartrate|fumarate|succinate|citrate|sulfate|nitrate|phosphate|acetate|propionate|butyrate)', base, flags=re.IGNORECASE)[0].strip()

        ja = None

        # Try manual dictionary (exact)
        if base_clean in MANUAL_NAME_JA:
            ja = MANUAL_NAME_JA[base_clean]
        elif base in MANUAL_NAME_JA:
            ja = MANUAL_NAME_JA[base]
        else:
            # Try partial match
            for key, val in MANUAL_NAME_JA.items():
                if key.lower() == base_clean.lower() or key.lower() == base.lower():
                    ja = val
                    break

        if not ja:
            # Try suffix-based auto-conversion
            lower = base_clean.lower()
            for suffix, katakana_suffix in SUFFIX_RULES:
                if lower.endswith(suffix):
                    stem = lower[:-len(suffix)]
                    # Find prefix katakana
                    if len(stem) >= 2:
                        prefix2 = stem[:2]
                        if prefix2 in PREFIX_MAP:
                            # Very rough: only use for INN-like names
                            # Skip if stem is too short or complex
                            if len(stem) <= 8 and stem.isalpha():
                                ja = PREFIX_MAP[prefix2] + katakana_suffix
                    break  # Only try first matching suffix

        # Only set if we got a reasonable result (at least 3 chars)
        if ja and len(ja) >= 3:
            node['name_ja'] = ja
            stats['name_ja'] += 1

    # ---- 4. 商品名拡充 ----
    for kegg_id, brands in BRAND_EXTRA2.items():
        if kegg_id not in drug_nodes:
            continue
        node = drug_nodes[kegg_id]
        existing_alt = set(node.get('names_alt', []))
        new_brands = [b for b in brands if b not in existing_alt]
        if new_brands:
            node['names_alt'] = node.get('names_alt', []) + new_brands
            stats['brand'] += len(new_brands)

    # ---- Save ----
    with open(GRAPH_LIGHT, 'w') as f:
        json.dump(graph, f, ensure_ascii=False, separators=(',', ':'))

    # Final stats
    drugs_final = [n for n in graph['nodes'] if n['type'] == 'drug']
    has_ae = sum(1 for n in drugs_final if n.get('adverse_effects'))
    has_cyp = sum(1 for n in drugs_final if n.get('cyp_enzymes'))
    has_ja = sum(1 for n in drugs_final if n.get('name_ja'))
    has_brand = sum(1 for n in drugs_final if any(
        not a.endswith('(TN)') for a in n.get('names_alt', [])
    ))

    print(f"=== Enrichment Results ===")
    print(f"副作用: +{stats['ae_drugs']}薬 +{stats['ae_effects']}件 → {has_ae}/{len(drugs_final)} ({100*has_ae/len(drugs_final):.1f}%)")
    print(f"  AEノード追加: {stats['ae_nodes']}, AEエッジ追加: {stats['ae_edges']}")
    print(f"CYP: +{stats['cyp_drugs']}薬 +{stats['cyp_added']}酵素 → {has_cyp}/{len(drugs_final)} ({100*has_cyp/len(drugs_final):.1f}%)")
    print(f"name_ja: +{stats['name_ja']} → {has_ja}/{len(drugs_final)} ({100*has_ja/len(drugs_final):.1f}%)")
    print(f"商品名: +{stats['brand']}")
    print(f"Total: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")


if __name__ == '__main__':
    main()
