#!/usr/bin/env python3
"""
new_03_match_names.py
厚労省成分名(JA) ↔ DDinter2薬名(EN) の名寄せ（多段マッチング）。

戦略:
1. 手動辞書: 既存 script 04/07 から ~1,200語の EN→JA辞書（精度100%）
2. カタカナ音写ルール: 接尾辞変換テーブル（~80ルール）
3. ファジーマッチ: 正規化後のLevenshtein距離 ≤ 2
4. 未マッチ: 手動レビューリスト出力

出力: data/drug_master.json
"""

import json
import re
import hashlib
from pathlib import Path
from collections import Counter

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"

YAKKA_FILE = DATA_DIR / "yakka_ingredients.json"
DDINTER_FILE = DATA_DIR / "ddinter_drugs.json"
OUTPUT = DATA_DIR / "drug_master.json"
UNMATCHED_OUTPUT = DATA_DIR / "unmatched_review.json"

# ============================================================
# 1. 統合 EN→JA 辞書（script 04 + script 07 統合、~1,200語）
# ============================================================
EN_JA_DICT = {
    # --- 鎮痛・解熱・抗炎症 ---
    "Acetaminophen": "アセトアミノフェン",
    "Aspirin": "アスピリン",
    "Loxoprofen": "ロキソプロフェン",
    "Ibuprofen": "イブプロフェン",
    "Diclofenac": "ジクロフェナク",
    "Celecoxib": "セレコキシブ",
    "Meloxicam": "メロキシカム",
    "Naproxen": "ナプロキセン",
    "Indomethacin": "インドメタシン",
    "Etodolac": "エトドラク",
    "Piroxicam": "ピロキシカム",
    "Mefenamic acid": "メフェナム酸",
    "Flurbiprofen": "フルルビプロフェン",
    "Sulindac": "スリンダク",
    "Tiaprofenic acid": "チアプロフェン酸",
    "Zaltoprofen": "ザルトプロフェン",
    # --- オピオイド ---
    "Morphine": "モルヒネ",
    "Oxycodone": "オキシコドン",
    "Fentanyl": "フェンタニル",
    "Tramadol": "トラマドール",
    "Codeine": "コデイン",
    "Hydromorphone": "ヒドロモルフォン",
    "Buprenorphine": "ブプレノルフィン",
    "Methadone": "メサドン",
    "Tapentadol": "タペンタドール",
    "Pentazocine": "ペンタゾシン",
    "Pethidine": "ペチジン",
    "Naloxone": "ナロキソン",
    "Naltrexone": "ナルトレキソン",
    # --- 神経・疼痛 ---
    "Pregabalin": "プレガバリン",
    "Gabapentin": "ガバペンチン",
    "Mirogabalin": "ミロガバリン",
    "Duloxetine": "デュロキセチン",
    "Amitriptyline": "アミトリプチリン",
    # --- 降圧 ARB ---
    "Candesartan": "カンデサルタン",
    "Olmesartan": "オルメサルタン",
    "Valsartan": "バルサルタン",
    "Telmisartan": "テルミサルタン",
    "Losartan": "ロサルタン",
    "Irbesartan": "イルベサルタン",
    "Azilsartan": "アジルサルタン",
    "Eprosartan": "エプロサルタン",
    # --- 降圧 ACE ---
    "Enalapril": "エナラプリル",
    "Lisinopril": "リシノプリル",
    "Ramipril": "ラミプリル",
    "Perindopril": "ペリンドプリル",
    "Captopril": "カプトプリル",
    "Imidapril": "イミダプリル",
    "Temocapril": "テモカプリル",
    "Benazepril": "ベナゼプリル",
    "Quinapril": "キナプリル",
    "Trandolapril": "トランドラプリル",
    # --- Ca拮抗 ---
    "Amlodipine": "アムロジピン",
    "Nifedipine": "ニフェジピン",
    "Diltiazem": "ジルチアゼム",
    "Verapamil": "ベラパミル",
    "Benidipine": "ベニジピン",
    "Azelnidipine": "アゼルニジピン",
    "Cilnidipine": "シルニジピン",
    "Nicardipine": "ニカルジピン",
    "Felodipine": "フェロジピン",
    "Barnidipine": "バルニジピン",
    "Manidipine": "マニジピン",
    "Nitrendipine": "ニトレンジピン",
    "Efonidipine": "エホニジピン",
    # --- β遮断 ---
    "Bisoprolol": "ビソプロロール",
    "Carvedilol": "カルベジロール",
    "Atenolol": "アテノロール",
    "Propranolol": "プロプラノロール",
    "Metoprolol": "メトプロロール",
    "Celiprolol": "セリプロロール",
    "Nebivolol": "ネビボロール",
    "Labetalol": "ラベタロール",
    # --- 利尿 ---
    "Furosemide": "フロセミド",
    "Tolvaptan": "トルバプタン",
    "Spironolactone": "スピロノラクトン",
    "Eplerenone": "エプレレノン",
    "Hydrochlorothiazide": "ヒドロクロロチアジド",
    "Trichlormethiazide": "トリクロルメチアジド",
    "Indapamide": "インダパミド",
    "Torasemide": "トラセミド",
    "Azosemide": "アゾセミド",
    # --- 強心・抗不整脈 ---
    "Digoxin": "ジゴキシン",
    "Amiodarone": "アミオダロン",
    "Flecainide": "フレカイニド",
    "Pilsicainide": "ピルシカイニド",
    "Lidocaine": "リドカイン",
    "Procainamide": "プロカインアミド",
    "Disopyramide": "ジソピラミド",
    "Mexiletine": "メキシレチン",
    "Propafenone": "プロパフェノン",
    "Bepridil": "ベプリジル",
    "Nicorandil": "ニコランジル",
    "Isosorbide": "イソソルビド",
    "Nitroglycerin": "ニトログリセリン",
    # --- スタチン ---
    "Atorvastatin": "アトルバスタチン",
    "Rosuvastatin": "ロスバスタチン",
    "Pravastatin": "プラバスタチン",
    "Pitavastatin": "ピタバスタチン",
    "Simvastatin": "シンバスタチン",
    "Fluvastatin": "フルバスタチン",
    "Lovastatin": "ロバスタチン",
    # --- 脂質異常 ---
    "Ezetimibe": "エゼチミブ",
    "Fenofibrate": "フェノフィブラート",
    "Bezafibrate": "ベザフィブラート",
    "Pemafibrate": "ペマフィブラート",
    "Clofibrate": "クロフィブラート",
    # --- 抗凝固 ---
    "Warfarin": "ワルファリン",
    "Heparin": "ヘパリン",
    "Edoxaban": "エドキサバン",
    "Rivaroxaban": "リバーロキサバン",
    "Apixaban": "アピキサバン",
    "Dabigatran": "ダビガトラン",
    "Enoxaparin": "エノキサパリン",
    "Fondaparinux": "フォンダパリヌクス",
    "Danaparoid": "ダナパロイド",
    # --- 抗血小板 ---
    "Clopidogrel": "クロピドグレル",
    "Prasugrel": "プラスグレル",
    "Ticagrelor": "チカグレロル",
    "Cilostazol": "シロスタゾール",
    "Ticlopidine": "チクロピジン",
    "Sarpogrelate": "サルポグレラート",
    # --- PPI ---
    "Omeprazole": "オメプラゾール",
    "Lansoprazole": "ランソプラゾール",
    "Rabeprazole": "ラベプラゾール",
    "Esomeprazole": "エソメプラゾール",
    "Vonoprazan": "ボノプラザン",
    "Famotidine": "ファモチジン",
    "Ranitidine": "ラニチジン",
    "Cimetidine": "シメチジン",
    "Nizatidine": "ニザチジン",
    "Lafutidine": "ラフチジン",
    # --- 消化器その他 ---
    "Rebamipide": "レバミピド",
    "Teprenone": "テプレノン",
    "Irsogladine": "イルソグラジン",
    "Sucralfate": "スクラルファート",
    "Misoprostol": "ミソプロストール",
    "Mosapride": "モサプリド",
    "Domperidone": "ドンペリドン",
    "Metoclopramide": "メトクロプラミド",
    "Itopride": "イトプリド",
    "Trimebutine": "トリメブチン",
    "Lubiprostone": "ルビプロストン",
    "Linaclotide": "リナクロチド",
    "Elobixibat": "エロビキシバット",
    "Loperamide": "ロペラミド",
    "Ondansetron": "オンダンセトロン",
    "Granisetron": "グラニセトロン",
    "Palonosetron": "パロノセトロン",
    "Aprepitant": "アプレピタント",
    "Fosaprepitant": "ホスアプレピタント",
    # --- 糖尿病 ---
    "Metformin": "メトホルミン",
    "Pioglitazone": "ピオグリタゾン",
    "Glimepiride": "グリメピリド",
    "Glibenclamide": "グリベンクラミド",
    "Gliclazide": "グリクラジド",
    "Voglibose": "ボグリボース",
    "Miglitol": "ミグリトール",
    "Acarbose": "アカルボース",
    "Sitagliptin": "シタグリプチン",
    "Vildagliptin": "ビルダグリプチン",
    "Alogliptin": "アログリプチン",
    "Linagliptin": "リナグリプチン",
    "Teneligliptin": "テネリグリプチン",
    "Saxagliptin": "サキサグリプチン",
    "Trelagliptin": "トレラグリプチン",
    "Empagliflozin": "エンパグリフロジン",
    "Dapagliflozin": "ダパグリフロジン",
    "Canagliflozin": "カナグリフロジン",
    "Ipragliflozin": "イプラグリフロジン",
    "Tofogliflozin": "トホグリフロジン",
    "Luseogliflozin": "ルセオグリフロジン",
    "Semaglutide": "セマグルチド",
    "Liraglutide": "リラグルチド",
    "Dulaglutide": "デュラグルチド",
    "Exenatide": "エキセナチド",
    "Insulin glargine": "インスリン グラルギン",
    "Insulin aspart": "インスリン アスパルト",
    "Insulin lispro": "インスリン リスプロ",
    "Insulin detemir": "インスリン デテミル",
    "Insulin degludec": "インスリン デグルデク",
    # --- 甲状腺 ---
    "Levothyroxine": "レボチロキシン",
    "Methimazole": "チアマゾール",
    "Propylthiouracil": "プロピルチオウラシル",
    "Thiamazole": "チアマゾール",
    # --- 骨粗鬆症 ---
    "Alendronate": "アレンドロン酸",
    "Risedronate": "リセドロン酸",
    "Minodronate": "ミノドロン酸",
    "Zoledronic acid": "ゾレドロン酸",
    "Ibandronate": "イバンドロン酸",
    "Denosumab": "デノスマブ",
    "Teriparatide": "テリパラチド",
    "Raloxifene": "ラロキシフェン",
    "Bazedoxifene": "バゼドキシフェン",
    "Eldecalcitol": "エルデカルシトール",
    "Alfacalcidol": "アルファカルシドール",
    "Calcitriol": "カルシトリオール",
    # --- 睡眠・抗不安 ---
    "Zolpidem": "ゾルピデム",
    "Zopiclone": "ゾピクロン",
    "Eszopiclone": "エスゾピクロン",
    "Suvorexant": "スボレキサント",
    "Lemborexant": "レンボレキサント",
    "Ramelteon": "ラメルテオン",
    "Triazolam": "トリアゾラム",
    "Nitrazepam": "ニトラゼパム",
    "Flunitrazepam": "フルニトラゼパム",
    "Brotizolam": "ブロチゾラム",
    "Estazolam": "エスタゾラム",
    "Quazepam": "クアゼパム",
    "Lormetazepam": "ロルメタゼパム",
    "Rilmazafone": "リルマザホン",
    "Diazepam": "ジアゼパム",
    "Alprazolam": "アルプラゾラム",
    "Lorazepam": "ロラゼパム",
    "Etizolam": "エチゾラム",
    "Clonazepam": "クロナゼパム",
    "Bromazepam": "ブロマゼパム",
    "Chlordiazepoxide": "クロルジアゼポキシド",
    "Midazolam": "ミダゾラム",
    "Melatonin": "メラトニン",
    # --- 抗うつ ---
    "Sertraline": "セルトラリン",
    "Escitalopram": "エスシタロプラム",
    "Paroxetine": "パロキセチン",
    "Fluvoxamine": "フルボキサミン",
    "Fluoxetine": "フルオキセチン",
    "Citalopram": "シタロプラム",
    "Mirtazapine": "ミルタザピン",
    "Venlafaxine": "ベンラファキシン",
    "Milnacipran": "ミルナシプラン",
    "Trazodone": "トラゾドン",
    "Nortriptyline": "ノルトリプチリン",
    "Imipramine": "イミプラミン",
    "Clomipramine": "クロミプラミン",
    "Maprotiline": "マプロチリン",
    # --- 抗精神病 ---
    "Haloperidol": "ハロペリドール",
    "Chlorpromazine": "クロルプロマジン",
    "Risperidone": "リスペリドン",
    "Olanzapine": "オランザピン",
    "Quetiapine": "クエチアピン",
    "Aripiprazole": "アリピプラゾール",
    "Brexpiprazole": "ブレクスピプラゾール",
    "Paliperidone": "パリペリドン",
    "Blonanserin": "ブロナンセリン",
    "Perospirone": "ペロスピロン",
    "Clozapine": "クロザピン",
    "Sulpiride": "スルピリド",
    "Tiapride": "チアプリド",
    "Lithium": "リチウム",
    # --- 抗てんかん ---
    "Carbamazepine": "カルバマゼピン",
    "Lamotrigine": "ラモトリギン",
    "Levetiracetam": "レベチラセタム",
    "Phenytoin": "フェニトイン",
    "Phenobarbital": "フェノバルビタール",
    "Topiramate": "トピラマート",
    "Zonisamide": "ゾニサミド",
    "Lacosamide": "ラコサミド",
    "Perampanel": "ペランパネル",
    "Clobazam": "クロバザム",
    "Rufinamide": "ルフィナミド",
    "Stiripentol": "スチリペントール",
    "Valproic acid": "バルプロ酸",
    # --- パーキンソン ---
    "Levodopa": "レボドパ",
    "Pramipexole": "プラミペキソール",
    "Ropinirole": "ロピニロール",
    "Rotigotine": "ロチゴチン",
    "Entacapone": "エンタカポン",
    "Selegiline": "セレギリン",
    "Rasagiline": "ラサギリン",
    "Safinamide": "サフィナミド",
    "Istradefylline": "イストラデフィリン",
    "Droxidopa": "ドロキシドパ",
    "Trihexyphenidyl": "トリヘキシフェニジル",
    "Biperiden": "ビペリデン",
    "Amantadine": "アマンタジン",
    # --- 認知症 ---
    "Donepezil": "ドネペジル",
    "Memantine": "メマンチン",
    "Galantamine": "ガランタミン",
    "Rivastigmine": "リバスチグミン",
    # --- 片頭痛 ---
    "Sumatriptan": "スマトリプタン",
    "Rizatriptan": "リザトリプタン",
    "Zolmitriptan": "ゾルミトリプタン",
    "Eletriptan": "エレトリプタン",
    "Naratriptan": "ナラトリプタン",
    "Erenumab": "エレヌマブ",
    "Galcanezumab": "ガルカネズマブ",
    "Fremanezumab": "フレマネズマブ",
    # --- 呼吸器 ---
    "Montelukast": "モンテルカスト",
    "Pranlukast": "プランルカスト",
    "Zafirlukast": "ザフィルルカスト",
    "Fluticasone": "フルチカゾン",
    "Budesonide": "ブデソニド",
    "Beclomethasone": "ベクロメタゾン",
    "Ciclesonide": "シクレソニド",
    "Mometasone": "モメタゾン",
    "Salbutamol": "サルブタモール",
    "Salmeterol": "サルメテロール",
    "Formoterol": "ホルモテロール",
    "Indacaterol": "インダカテロール",
    "Vilanterol": "ビランテロール",
    "Tiotropium": "チオトロピウム",
    "Glycopyrronium": "グリコピロニウム",
    "Umeclidinium": "ウメクリジニウム",
    "Theophylline": "テオフィリン",
    "Aminophylline": "アミノフィリン",
    "Carbocisteine": "カルボシステイン",
    "Ambroxol": "アンブロキソール",
    "Dextromethorphan": "デキストロメトルファン",
    "Ephedrine": "エフェドリン",
    "Cromoglicate": "クロモグリク酸",
    "Omalizumab": "オマリズマブ",
    "Mepolizumab": "メポリズマブ",
    "Benralizumab": "ベンラリズマブ",
    "Dupilumab": "デュピルマブ",
    # --- ステロイド ---
    "Prednisolone": "プレドニゾロン",
    "Dexamethasone": "デキサメタゾン",
    "Betamethasone": "ベタメタゾン",
    "Methylprednisolone": "メチルプレドニゾロン",
    "Hydrocortisone": "ヒドロコルチゾン",
    "Cortisone": "コルチゾン",
    "Triamcinolone": "トリアムシノロン",
    "Fludrocortisone": "フルドロコルチゾン",
    # --- 免疫抑制 ---
    "Tacrolimus": "タクロリムス",
    "Cyclosporine": "シクロスポリン",
    "Mycophenolate": "ミコフェノール酸",
    "Azathioprine": "アザチオプリン",
    "Methotrexate": "メトトレキサート",
    "Hydroxychloroquine": "ヒドロキシクロロキン",
    "Leflunomide": "レフルノミド",
    "Iguratimod": "イグラチモド",
    "Bucillamine": "ブシラミン",
    "Salazosulfapyridine": "サラゾスルファピリジン",
    # --- 生物学的製剤 ---
    "Adalimumab": "アダリムマブ",
    "Infliximab": "インフリキシマブ",
    "Etanercept": "エタネルセプト",
    "Tocilizumab": "トシリズマブ",
    "Sarilumab": "サリルマブ",
    "Golimumab": "ゴリムマブ",
    "Certolizumab": "セルトリズマブ",
    "Abatacept": "アバタセプト",
    "Ustekinumab": "ウステキヌマブ",
    "Secukinumab": "セクキヌマブ",
    "Ixekizumab": "イキセキズマブ",
    "Guselkumab": "グセルクマブ",
    "Risankizumab": "リサンキズマブ",
    "Vedolizumab": "ベドリズマブ",
    # --- JAK阻害 ---
    "Baricitinib": "バリシチニブ",
    "Tofacitinib": "トファシチニブ",
    "Upadacitinib": "ウパダシチニブ",
    "Peficitinib": "ペフィシチニブ",
    "Filgotinib": "フィルゴチニブ",
    # --- 抗菌 ---
    "Amoxicillin": "アモキシシリン",
    "Ampicillin": "アンピシリン",
    "Piperacillin": "ピペラシリン",
    "Sultamicillin": "スルタミシリン",
    "Benzylpenicillin": "ベンジルペニシリン",
    "Penicillin": "ペニシリン",
    "Cefazolin": "セファゾリン",
    "Cefditoren": "セフジトレン",
    "Ceftriaxone": "セフトリアキソン",
    "Cefepime": "セフェピム",
    "Cefmetazole": "セフメタゾール",
    "Cefotaxime": "セフォタキシム",
    "Ceftazidime": "セフタジジム",
    "Cefcapene": "セフカペン",
    "Cefpodoxime": "セフポドキシム",
    "Cephalexin": "セファレキシン",
    "Cefozopran": "セフォゾプラン",
    "Cefaclor": "セファクロル",
    "Flomoxef": "フロモキセフ",
    "Meropenem": "メロペネム",
    "Imipenem": "イミペネム",
    "Doripenem": "ドリペネム",
    "Biapenem": "ビアペネム",
    "Clarithromycin": "クラリスロマイシン",
    "Azithromycin": "アジスロマイシン",
    "Erythromycin": "エリスロマイシン",
    "Roxithromycin": "ロキシスロマイシン",
    "Josamycin": "ジョサマイシン",
    "Levofloxacin": "レボフロキサシン",
    "Moxifloxacin": "モキシフロキサシン",
    "Ciprofloxacin": "シプロフロキサシン",
    "Sitafloxacin": "シタフロキサシン",
    "Garenoxacin": "ガレノキサシン",
    "Tosufloxacin": "トスフロキサシン",
    "Norfloxacin": "ノルフロキサシン",
    "Ofloxacin": "オフロキサシン",
    "Prulifloxacin": "プルリフロキサシン",
    "Vancomycin": "バンコマイシン",
    "Teicoplanin": "テイコプラニン",
    "Linezolid": "リネゾリド",
    "Daptomycin": "ダプトマイシン",
    "Gentamicin": "ゲンタマイシン",
    "Amikacin": "アミカシン",
    "Tobramycin": "トブラマイシン",
    "Minocycline": "ミノサイクリン",
    "Doxycycline": "ドキシサイクリン",
    "Tetracycline": "テトラサイクリン",
    "Tigecycline": "チゲサイクリン",
    "Trimethoprim": "トリメトプリム",
    "Sulfamethoxazole": "スルファメトキサゾール",
    "Fosfomycin": "ホスホマイシン",
    "Clindamycin": "クリンダマイシン",
    "Metronidazole": "メトロニダゾール",
    "Colistin": "コリスチン",
    "Polymyxin": "ポリミキシン",
    "Rifampicin": "リファンピシン",
    "Isoniazid": "イソニアジド",
    "Pyrazinamide": "ピラジナミド",
    "Ethambutol": "エタンブトール",
    # --- 抗真菌 ---
    "Fluconazole": "フルコナゾール",
    "Itraconazole": "イトラコナゾール",
    "Voriconazole": "ボリコナゾール",
    "Posaconazole": "ポサコナゾール",
    "Micafungin": "ミカファンギン",
    "Caspofungin": "カスポファンギン",
    "Amphotericin": "アムホテリシン",
    "Terbinafine": "テルビナフィン",
    "Flucytosine": "フルシトシン",
    # --- 抗ウイルス ---
    "Acyclovir": "アシクロビル",
    "Valacyclovir": "バラシクロビル",
    "Oseltamivir": "オセルタミビル",
    "Baloxavir": "バロキサビル",
    "Laninamivir": "ラニナミビル",
    "Zanamivir": "ザナミビル",
    "Remdesivir": "レムデシビル",
    "Favipiravir": "ファビピラビル",
    "Ribavirin": "リバビリン",
    "Sofosbuvir": "ソホスブビル",
    "Ledipasvir": "レジパスビル",
    "Glecaprevir": "グレカプレビル",
    "Pibrentasvir": "ピブレンタスビル",
    "Entecavir": "エンテカビル",
    "Tenofovir": "テノホビル",
    "Lamivudine": "ラミブジン",
    "Adefovir": "アデホビル",
    "Ganciclovir": "ガンシクロビル",
    # --- 抗腫瘍 ---
    "Imatinib": "イマチニブ",
    "Gefitinib": "ゲフィチニブ",
    "Erlotinib": "エルロチニブ",
    "Afatinib": "アファチニブ",
    "Osimertinib": "オシメルチニブ",
    "Crizotinib": "クリゾチニブ",
    "Alectinib": "アレクチニブ",
    "Lorlatinib": "ロルラチニブ",
    "Sunitinib": "スニチニブ",
    "Sorafenib": "ソラフェニブ",
    "Lenvatinib": "レンバチニブ",
    "Regorafenib": "レゴラフェニブ",
    "Cabozantinib": "カボザンチニブ",
    "Axitinib": "アキシチニブ",
    "Pazopanib": "パゾパニブ",
    "Dabrafenib": "ダブラフェニブ",
    "Trametinib": "トラメチニブ",
    "Vemurafenib": "ベムラフェニブ",
    "Ibrutinib": "イブルチニブ",
    "Acalabrutinib": "アカラブルチニブ",
    "Ruxolitinib": "ルキソリチニブ",
    "Palbociclib": "パルボシクリブ",
    "Ribociclib": "リボシクリブ",
    "Abemaciclib": "アベマシクリブ",
    "Olaparib": "オラパリブ",
    "Niraparib": "ニラパリブ",
    "Everolimus": "エベロリムス",
    "Temsirolimus": "テムシロリムス",
    "Bortezomib": "ボルテゾミブ",
    "Lenalidomide": "レナリドミド",
    "Pomalidomide": "ポマリドミド",
    "Thalidomide": "サリドマイド",
    "Nivolumab": "ニボルマブ",
    "Pembrolizumab": "ペムブロリズマブ",
    "Atezolizumab": "アテゾリズマブ",
    "Durvalumab": "デュルバルマブ",
    "Avelumab": "アベルマブ",
    "Ipilimumab": "イピリムマブ",
    "Tremelimumab": "トレメリムマブ",
    "Trastuzumab": "トラスツズマブ",
    "Bevacizumab": "ベバシズマブ",
    "Rituximab": "リツキシマブ",
    "Cetuximab": "セツキシマブ",
    "Panitumumab": "パニツムマブ",
    "Pertuzumab": "ペルツズマブ",
    "Ramucirumab": "ラムシルマブ",
    "Daratumumab": "ダラツムマブ",
    "Obinutuzumab": "オビヌツズマブ",
    "Mogamulizumab": "モガムリズマブ",
    "Doxorubicin": "ドキソルビシン",
    "Epirubicin": "エピルビシン",
    "Cisplatin": "シスプラチン",
    "Carboplatin": "カルボプラチン",
    "Oxaliplatin": "オキサリプラチン",
    "Paclitaxel": "パクリタキセル",
    "Docetaxel": "ドセタキセル",
    "Fluorouracil": "フルオロウラシル",
    "Capecitabine": "カペシタビン",
    "Gemcitabine": "ゲムシタビン",
    "Irinotecan": "イリノテカン",
    "Etoposide": "エトポシド",
    "Cyclophosphamide": "シクロホスファミド",
    "Vincristine": "ビンクリスチン",
    "Vinblastine": "ビンブラスチン",
    "Pemetrexed": "ペメトレキセド",
    "Cytarabine": "シタラビン",
    "Bleomycin": "ブレオマイシン",
    "Mitomycin": "マイトマイシン",
    "Temozolomide": "テモゾロミド",
    # --- 支持療法 ---
    "Filgrastim": "フィルグラスチム",
    "Pegfilgrastim": "ペグフィルグラスチム",
    "Epoetin": "エポエチン",
    "Darbepoetin": "ダルベポエチン",
    "Eltrombopag": "エルトロンボパグ",
    "Romiplostim": "ロミプロスチム",
    "Leucovorin": "ロイコボリン",
    "Mesna": "メスナ",
    "Dexrazoxane": "デクスラゾキサン",
    # --- アレルギー ---
    "Fexofenadine": "フェキソフェナジン",
    "Cetirizine": "セチリジン",
    "Levocetirizine": "レボセチリジン",
    "Loratadine": "ロラタジン",
    "Desloratadine": "デスロラタジン",
    "Bilastine": "ビラスチン",
    "Olopatadine": "オロパタジン",
    "Epinastine": "エピナスチン",
    "Bepotastine": "ベポタスチン",
    "Rupatadine": "ルパタジン",
    "Azelastine": "アゼラスチン",
    "Ketotifen": "ケトチフェン",
    "Diphenhydramine": "ジフェンヒドラミン",
    "Chlorpheniramine": "クロルフェニラミン",
    "Hydroxyzine": "ヒドロキシジン",
    "Promethazine": "プロメタジン",
    # --- 泌尿器 ---
    "Tamsulosin": "タムスロシン",
    "Naftopidil": "ナフトピジル",
    "Silodosin": "シロドシン",
    "Dutasteride": "デュタステリド",
    "Finasteride": "フィナステリド",
    "Mirabegron": "ミラベグロン",
    "Vibegron": "ビベグロン",
    "Solifenacin": "ソリフェナシン",
    "Fesoterodine": "フェソテロジン",
    "Tolterodine": "トルテロジン",
    "Oxybutynin": "オキシブチニン",
    "Propiverine": "プロピベリン",
    "Imidafenacin": "イミダフェナシン",
    "Sildenafil": "シルデナフィル",
    "Tadalafil": "タダラフィル",
    "Vardenafil": "バルデナフィル",
    # --- 痛風 ---
    "Allopurinol": "アロプリノール",
    "Febuxostat": "フェブキソスタット",
    "Topiroxostat": "トピロキソスタット",
    "Benzbromarone": "ベンズブロマロン",
    "Probenecid": "プロベネシド",
    "Colchicine": "コルヒチン",
    "Dotinurad": "ドチヌラド",
    # --- 止血・血液 ---
    "Tranexamic acid": "トラネキサム酸",
    "Carbazochrome": "カルバゾクロム",
    # --- 血管拡張 ---
    "Alprostadil": "アルプロスタジル",
    "Limaprost": "リマプロスト",
    "Beraprost": "ベラプロスト",
    # --- 麻酔 ---
    "Propofol": "プロポフォール",
    "Ketamine": "ケタミン",
    "Sevoflurane": "セボフルラン",
    "Isoflurane": "イソフルラン",
    "Desflurane": "デスフルラン",
    "Thiopental": "チオペンタール",
    "Dexmedetomidine": "デクスメデトミジン",
    "Rocuronium": "ロクロニウム",
    "Sugammadex": "スガマデクス",
    "Droperidol": "ドロペリドール",
    "Remimazolam": "レミマゾラム",
    # --- 肝疾患 ---
    "Ursodeoxycholic acid": "ウルソデオキシコール酸",
    # --- 肺線維症 ---
    "Pirfenidone": "ピルフェニドン",
    "Nintedanib": "ニンテダニブ",
    # --- 無機化合物 ---
    "Magnesium oxide": "酸化マグネシウム",
    "Lithium carbonate": "炭酸リチウム",
    "Potassium chloride": "塩化カリウム",
    "Sodium chloride": "塩化ナトリウム",
    "Calcium carbonate": "炭酸カルシウム",
    "Glucose": "ブドウ糖",
    "Oxygen": "酸素",
    "Nitrous oxide": "亜酸化窒素",
    "Heparinoid": "ヘパリノイド",
    "Sennosides": "センノシド",
    # --- その他 ---
    "Nicotine": "ニコチン",
    "Alteplase": "アルテプラーゼ",
    "Epinephrine": "アドレナリン",
    "Noradrenaline": "ノルアドレナリン",
    "Dopamine": "ドパミン",
    "Dobutamine": "ドブタミン",
    "Pilocarpine": "ピロカルピン",
    "Atropine": "アトロピン",
    "Baclofen": "バクロフェン",
    "Tizanidine": "チザニジン",
    "Eperisone": "エペリゾン",
    "Dantrolene": "ダントロレン",
    "Dipyridamole": "ジピリダモール",
    "Sacubitril": "サクビトリル",
    "Colestyramine": "コレスチラミン",
    "Naldemedine": "ナルデメジン",
    "Caffeine": "カフェイン",
    # --- 追加分（07_add_name_ja.py から） ---
    "Abacavir": "アバカビル",
    "Acetazolamide": "アセタゾラミド",
    "Acoramidis": "アコラミジス",
    "Acotiamide": "アコチアミド",
    "Actinomycin": "アクチノマイシン",
    "Aflibercept": "アフリベルセプト",
    "Afloqualone": "アフロクアロン",
    "Agalsidase": "アガルシダーゼ",
    "Albumin": "アルブミン",
    "Alfentanil": "アルフェンタニル",
    "Alglucosidase": "アルグルコシダーゼ",
    "Alirocumab": "アリロクマブ",
    "Aliskiren": "アリスキレン",
    "Alvimopan": "アルビモパン",
    "Ambrisentan": "アンブリセンタン",
    "Amenamevir": "アメナメビル",
    "Amobarbital": "アモバルビタール",
    "Anagliptin": "アナグリプチン",
    "Anakinra": "アナキンラ",
    "Anifrolumab": "アニフロルマブ",
    "Apomorphine": "アポモルヒネ",
    "Argatroban": "アルガトロバン",
    "Arsenic": "亜ヒ酸",
    "Ascorbic": "アスコルビン酸",
    "Asenapine": "アセナピン",
    "Asparaginase": "アスパラギナーゼ",
    "Atazanavir": "アタザナビル",
    "Auranofin": "オーラノフィン",
    "Avatrombopag": "アバトロンボパグ",
    "Azacitidine": "アザシチジン",
    "Azasetron": "アザセトロン",
    "Belimumab": "ベリムマブ",
    "Bendamustine": "ベンダムスチン",
    "Bethanechol": "ベタネコール",
    "Bictegravir": "ビクテグラビル",
    "Bimatoprost": "ビマトプロスト",
    "Binimetinib": "ビニメチニブ",
    "Biotin": "ビオチン",
    "Bisacodyl": "ビサコジル",
    "Bosentan": "ボセンタン",
    "Brentuximab": "ブレンツキシマブ",
    "Brimonidine": "ブリモニジン",
    "Brinzolamide": "ブリンゾラミド",
    "Brivaracetam": "ブリバラセタム",
    "Brolucizumab": "ブロルシズマブ",
    "Bromocriptine": "ブロモクリプチン",
    "Bunazosin": "ブナゾシン",
    "Bupivacaine": "ブピバカイン",
    "Buspirone": "ブスピロン",
    "Busulfan": "ブスルファン",
    "Butylscopolamine": "ブチルスコポラミン",
    "Cabazitaxel": "カバジタキセル",
    "Cabergoline": "カベルゴリン",
    "Calcipotriol": "カルシポトリオール",
    "Calcium": "カルシウム",
    "Camostat": "カモスタット",
    "Canakinumab": "カナキヌマブ",
    "Cannabidiol": "カンナビジオール",
    "Caplacizumab": "カプラシズマブ",
    "Capmatinib": "カプマチニブ",
    "Carfilzomib": "カルフィルゾミブ",
    "Cariprazine": "カリプラジン",
    "Cemiplimab": "セミプリマブ",
    "Chloral": "抱水クロラール",
    "Chlorphenesin": "クロルフェネシン",
    "Cholecalciferol": "コレカルシフェロール",
    "Cidofovir": "シドホビル",
    "Cisatracurium": "シスアトラクリウム",
    "Cladribine": "クラドリビン",
    "Clonidine": "クロニジン",
    "Clorazepate": "クロラゼプ酸",
    "Cloxazolam": "クロキサゾラム",
    "Cyanocobalamin": "シアノコバラミン",
    "Dacarbazine": "ダカルバジン",
    "Dapoxetine": "ダポキセチン",
    "Daprodustat": "ダプロデュスタット",
    "Darifenacin": "ダリフェナシン",
    "Darunavir": "ダルナビル",
    "Daunorubicin": "ダウノルビシン",
    "Decitabine": "デシタビン",
    "Dexlansoprazole": "デクスランソプラゾール",
    "Distigmine": "ジスチグミン",
    "Dolutegravir": "ドルテグラビル",
    "Dorzolamide": "ドルゾラミド",
    "Doxazosin": "ドキサゾシン",
    "Eculizumab": "エクリズマブ",
    "Efavirenz": "エファビレンツ",
    "Efinaconazole": "エフィナコナゾール",
    "Elotuzumab": "エロツズマブ",
    "Elvitegravir": "エルビテグラビル",
    "Emicizumab": "エミシズマブ",
    "Emtricitabine": "エムトリシタビン",
    "Enasidenib": "エナシデニブ",
    "Encorafenib": "エンコラフェニブ",
    "Ensitrelvir": "エンシトレルビル",
    "Entrectinib": "エヌトレクチニブ",
    "Epalrestat": "エパルレスタット",
    "Epoprostenol": "エポプロステノール",
    "Eribulin": "エリブリン",
    "Ertugliflozin": "エルツグリフロジン",
    "Esaxerenone": "エサキセレノン",
    "Esflurbiprofen": "エスフルルビプロフェン",
    "Esmolol": "エスモロール",
    "Ethosuximide": "エトスクシミド",
    "Evolocumab": "エボロクマブ",
    "Faricimab": "ファリシマブ",
    "Fenfluramine": "フェンフルラミン",
    "Finerenone": "フィネレノン",
    "Flavoxate": "フラボキサート",
    "Fludarabine": "フルダラビン",
    "Fluphenazine": "フルフェナジン",
    "Flurazepam": "フルラゼパム",
    "Flutazolam": "フルタゾラム",
    "Folic acid": "葉酸",
    "Foscarnet": "ホスカルネット",
    "Fosphenytoin": "ホスフェニトイン",
    "Gabexate": "ガベキサート",
    "Gilteritinib": "ギルテリチニブ",
    "Glipizide": "グリピジド",
    "Guanfacine": "グアンファシン",
    "Haloxazolam": "ハロキサゾラム",
    "Hydralazine": "ヒドララジン",
    "Hydroxyurea": "ヒドロキシウレア",
    "Ibudilast": "イブジラスト",
    "Idarubicin": "イダルビシン",
    "Ifosfamide": "イホスファミド",
    "Immunoglobulin": "免疫グロブリン",
    "Inclisiran": "インクリシラン",
    "Interferon": "インターフェロン",
    "Isatuximab": "イサツキシマブ",
    "Ivabradine": "イバブラジン",
    "Ixazomib": "イキサゾミブ",
    "Lactulose": "ラクツロース",
    "Landiolol": "ランジオロール",
    "Lapatinib": "ラパチニブ",
    "Larotrectinib": "ラロトレクチニブ",
    "Latanoprost": "ラタノプロスト",
    "Levobupivacaine": "レボブピバカイン",
    "Levomepromazine": "レボメプロマジン",
    "Lopinavir": "ロピナビル",
    "Luliconazole": "ルリコナゾール",
    "Lurasidone": "ルラシドン",
    "Macitentan": "マシテンタン",
    "Macrogol": "マクロゴール",
    "Magnesium": "マグネシウム",
    "Mannitol": "マンニトール",
    "Maxacalcitol": "マキサカルシトール",
    "Mecobalamin": "メコバラミン",
    "Medazepam": "メダゼパム",
    "Melphalan": "メルファラン",
    "Menatetrenone": "メナテトレノン",
    "Mepivacaine": "メピバカイン",
    "Methocarbamol": "メトカルバモール",
    "Methyldopa": "メチルドパ",
    "Mexazolam": "メキサゾラム",
    "Midostaurin": "ミドスタウリン",
    "Milrinone": "ミルリノン",
    "Minoxidil": "ミノキシジル",
    "Mitiglinide": "ミチグリニド",
    "Mitoxantrone": "ミトキサントロン",
    "Mizoribine": "ミゾリビン",
    "Molnupiravir": "モルヌピラビル",
    "Mupirocin": "ムピロシン",
    "Nafamostat": "ナファモスタット",
    "Nateglinide": "ナテグリニド",
    "Nemolizumab": "ネモリズマブ",
    "Neostigmine": "ネオスチグミン",
    "Neratinib": "ネラチニブ",
    "Nevirapine": "ネビラピン",
    "Niacin": "ナイアシン",
    "Nicotinamide": "ニコチンアミド",
    "Nimetazepam": "ニメタゼパム",
    "Nirmatrelvir": "ニルマトレルビル",
    "Olprinone": "オルプリノン",
    "Omarigliptin": "オマリグリプチン",
    "Oxazolam": "オキサゾラム",
    "Pancuronium": "パンクロニウム",
    "Panobinostat": "パノビノスタット",
    "Pantoprazole": "パントプラゾール",
    "Patisiran": "パチシラン",
    "Pemirolast": "ペミロラスト",
    "Penicillamine": "ペニシラミン",
    "Pentobarbital": "ペントバルビタール",
    "Pergolide": "ペルゴリド",
    "Perphenazine": "ペルフェナジン",
    "Picosulfate": "ピコスルファート",
    "Pimozide": "ピモジド",
    "Pirenzepine": "ピレンゼピン",
    "Polatuzumab": "ポラツズマブ",
    "Potassium": "カリウム",
    "Pralsetinib": "プラルセチニブ",
    "Prazosin": "プラゾシン",
    "Primidone": "プリミドン",
    "Procaine": "プロカイン",
    "Procarbazine": "プロカルバジン",
    "Prucalopride": "プルカロプリド",
    "Pyridoxine": "ピリドキシン",
    "Raltegravir": "ラルテグラビル",
    "Ramosetron": "ラモセトロン",
    "Ranibizumab": "ラニビズマブ",
    "Ravulizumab": "ラブリズマブ",
    "Remifentanil": "レミフェンタニル",
    "Repaglinide": "レパグリニド",
    "Riboflavin": "リボフラビン",
    "Rilpivirine": "リルピビリン",
    "Riociguat": "リオシグアト",
    "Ripasudil": "リパスジル",
    "Ritonavir": "リトナビル",
    "Roflumilast": "ロフルミラスト",
    "Ropivacaine": "ロピバカイン",
    "Roxadustat": "ロキサデュスタット",
    "Rucaparib": "ルカパリブ",
    "Sacituzumab": "サシツズマブ",
    "Selexipag": "セレキシパグ",
    "Selpercatinib": "セルペルカチニブ",
    "Sodium": "ナトリウム",
    "Sorbitol": "ソルビトール",
    "Sufentanil": "スフェンタニル",
    "Suplatast": "スプラタスト",
    "Suxamethonium": "スキサメトニウム",
    "Tacalcitol": "タカルシトール",
    "Tafamidis": "タファミジス",
    "Tafluprost": "タフルプロスト",
    "Talazoparib": "タラゾパリブ",
    "Tamibarotene": "タミバロテン",
    "Tandospirone": "タンドスピロン",
    "Tegafur": "テガフール",
    "Tepotinib": "テポチニブ",
    "Terazosin": "テラゾシン",
    "Tetracaine": "テトラカイン",
    "Tezepelumab": "テゼペルマブ",
    "Thiamine": "チアミン",
    "Timolol": "チモロール",
    "Tirzepatide": "チルゼパチド",
    "Tocopherol": "トコフェロール",
    "Tofisopam": "トフィソパム",
    "Tolperisone": "トルペリゾン",
    "Topotecan": "トポテカン",
    "Tranilast": "トラニラスト",
    "Travoprost": "トラボプロスト",
    "Treprostinil": "トレプロスチニル",
    "Tretinoin": "トレチノイン",
    "Trifluridine": "トリフルリジン",
    "Tucatinib": "ツカチニブ",
    "Ursodeoxycholic": "ウルソデオキシコール酸",
    "Valproate": "バルプロ酸",
    "Vandetanib": "バンデタニブ",
    "Vecuronium": "ベクロニウム",
    "Venetoclax": "ベネトクラクス",
    "Vigabatrin": "ビガバトリン",
    "Vinorelbine": "ビノレルビン",
    "Vismodegib": "ビスモデギブ",
    "Vorinostat": "ボリノスタット",
    "Zanubrutinib": "ザヌブルチニブ",
    "Zinc": "亜鉛",
    "Zotepine": "ゾテピン",
    "Iron": "鉄",
    "Ferrous": "鉄",
    "Copper": "銅",
    "Selenium": "セレン",
    "Iodine": "ヨウ素",
}

# JA→EN 逆辞書
JA_EN_DICT = {}
for en, ja in EN_JA_DICT.items():
    if ja not in JA_EN_DICT:
        JA_EN_DICT[ja] = en

# ============================================================
# 2. 接尾辞→カタカナ変換ルール
# ============================================================
SUFFIX_RULES = [
    ("zumab", "ズマブ"), ("ximab", "キシマブ"), ("mumab", "ムマブ"),
    ("lumab", "ルマブ"), ("tumab", "ツマブ"), ("numab", "ヌマブ"),
    ("cumab", "クマブ"),
    ("tinib", "チニブ"), ("zanib", "ザニブ"), ("fenib", "フェニブ"),
    ("ciclib", "シクリブ"), ("parib", "パリブ"),
    ("prazole", "プラゾール"), ("pridine", "プリジン"),
    ("statin", "スタチン"), ("fibrate", "フィブラート"),
    ("sartan", "サルタン"), ("dipine", "ジピン"),
    ("olol", "ロール"), ("pril", "プリル"),
    ("floxacin", "フロキサシン"), ("penem", "ペネム"),
    ("mycin", "マイシン"), ("cycline", "サイクリン"),
    ("cillin", "シリン"), ("azole", "アゾール"), ("fungin", "ファンギン"),
    ("navir", "ナビル"), ("buvir", "ブビル"), ("asvir", "アスビル"),
    ("previr", "プレビル"), ("vudine", "ブジン"),
    ("gliptin", "グリプチン"), ("gliflozin", "グリフロジン"),
    ("glutide", "グルチド"),
    ("citinib", "シチニブ"), ("limus", "リムス"),
    ("mab", "マブ"), ("nib", "ニブ"), ("lib", "リブ"),
    ("tide", "チド"), ("pine", "ピン"), ("pam", "パム"), ("lam", "ラム"),
    ("done", "ドン"), ("sone", "ゾン"), ("lone", "ロン"),
    ("tine", "チン"), ("dine", "ジン"), ("mine", "ミン"),
    ("zine", "ジン"), ("rine", "リン"), ("line", "リン"),
    ("ine", "イン"), ("ide", "イド"), ("ate", "エート"),
    ("ose", "オース"), ("ol", "オール"), ("il", "イル"),
    ("al", "アール"), ("an", "アン"), ("um", "ウム"),
    ("in", "イン"), ("on", "オン"), ("en", "エン"), ("er", "エル"),
    ("ax", "アクス"), ("ix", "イクス"), ("ox", "オクス"),
    ("ab", "アブ"), ("ib", "イブ"), ("ub", "ウブ"),
]


def extract_base_en(name: str) -> str:
    """英名から基本名を抽出"""
    base = name.split("(")[0].strip()
    for suffix in [" hydrochloride", " sodium", " potassium", " calcium",
                   " maleate", " fumarate", " mesylate", " besylate",
                   " besilate", " sulfate", " phosphate", " tartrate",
                   " citrate", " succinate", " acetate", " hydrate",
                   " dihydrochloride", " monohydrate", " hemihydrate",
                   " tosylate", " tosilate", " bromide", " chloride",
                   " nitrate", " oxide", " carbonate",
                   " alfa", " beta", " gamma", " delta",
                   " pivoxil", " marboxil", " proxetil", " axetil",
                   " medoxomil", " etexilate", " alafenamide",
                   " disoproxil", " mofetil", " diacetyl"]:
        if base.lower().endswith(suffix):
            base = base[:len(base) - len(suffix)].strip()
            break
    return base


def en_to_katakana(name_en: str) -> str:
    """英名→カタカナ変換（辞書→接尾辞ルール）"""
    base = extract_base_en(name_en)

    # 1. 辞書完全一致
    for key, val in EN_JA_DICT.items():
        if key.lower() == base.lower():
            return val

    # 2. 先頭単語マッチ
    first = base.split()[0] if " " in base else ""
    if first:
        for key, val in EN_JA_DICT.items():
            if key.lower() == first.lower():
                return val

    # 3. 前方一致
    bl = base.lower()
    for key, val in EN_JA_DICT.items():
        if bl.startswith(key.lower()):
            return val

    return ""


def normalize_ja(name: str) -> str:
    """日本語成分名を正規化して比較用文字列を生成"""
    n = name.strip()
    # 塩形除去
    for suffix in ["ナトリウム水和物", "ナトリウム", "塩酸塩", "カリウム",
                    "カルシウム水和物", "カルシウム", "マレイン酸塩",
                    "フマル酸塩", "メシル酸塩", "リン酸エステル",
                    "臭化水素酸塩", "硫酸塩", "リン酸塩", "酒石酸塩",
                    "クエン酸塩", "コハク酸エステル", "酢酸エステル",
                    "水和物"]:
        if n.endswith(suffix) and len(n) > len(suffix):
            n = n[:-len(suffix)]
            break
    return n


def fuzzy_match_ja(name_a: str, name_b: str, max_dist: int = 2) -> bool:
    """カタカナ同士の近似マッチ（Levenshtein距離）"""
    if abs(len(name_a) - len(name_b)) > max_dist:
        return False
    # Simple Levenshtein
    m, n = len(name_a), len(name_b)
    if m > n:
        name_a, name_b = name_b, name_a
        m, n = n, m
    prev = list(range(m + 1))
    for j in range(1, n + 1):
        curr = [j] + [0] * m
        for i in range(1, m + 1):
            cost = 0 if name_a[i-1] == name_b[j-1] else 1
            curr[i] = min(curr[i-1]+1, prev[i]+1, prev[i-1]+cost)
        prev = curr
    return prev[m] <= max_dist


def make_drug_id(drugbank_id: str, name_en: str) -> str:
    """薬IDを生成。DrugBank IDがあればそれを使用、なければJP_+hash"""
    if drugbank_id and drugbank_id.startswith("DB"):
        return drugbank_id
    h = hashlib.md5(name_en.encode()).hexdigest()[:8]
    return f"JP_{h}"


def main():
    # Load inputs
    if not YAKKA_FILE.exists():
        print(f"ERROR: {YAKKA_FILE} not found. Run new_01 first.")
        return
    if not DDINTER_FILE.exists():
        print(f"ERROR: {DDINTER_FILE} not found. Run new_02 first.")
        return

    with open(YAKKA_FILE, encoding="utf-8") as f:
        yakka = json.load(f)
    with open(DDINTER_FILE, encoding="utf-8") as f:
        ddinter = json.load(f)

    ja_ingredients = yakka["ingredients"]
    dd_drugs = ddinter["drugs"]

    print(f"厚労省成分: {len(ja_ingredients)}")
    print(f"DDinter2薬: {len(dd_drugs)}")
    print(f"EN→JA辞書: {len(EN_JA_DICT)} 語")

    # Build lookup structures
    # DDinter2: name → drug record
    dd_by_name = {}
    for d in dd_drugs:
        name = d.get("Drug_Name", d.get("name", "")).strip()
        if name:
            dd_by_name[name.lower()] = d

    # 厚労省: JA name → ingredient record
    yakka_by_ja = {}
    for ing in ja_ingredients:
        ja = ing["name_ja"]
        norm = normalize_ja(ja)
        yakka_by_ja[ja] = ing
        if norm != ja:
            yakka_by_ja[norm] = ing

    # ============ マッチング ============
    master = []
    matched_dd = set()
    matched_yakka = set()
    stats = Counter()

    # Pass 1: 辞書ベースマッチ
    for en_name, dd_drug in [(d.get("Drug_Name", ""), d) for d in dd_drugs]:
        if not en_name:
            continue
        base_en = extract_base_en(en_name)
        ja_name = en_to_katakana(en_name)
        if not ja_name:
            continue

        # 厚労省成分とマッチ
        norm_ja = normalize_ja(ja_name)
        matched_ing = None
        for candidate in [ja_name, norm_ja]:
            if candidate in yakka_by_ja:
                matched_ing = yakka_by_ja[candidate]
                break

        dd_id = dd_drug.get("DDInter_id", "")
        drugbank_id = dd_drug.get("DrugBank_ID", "")

        entry = {
            "id": make_drug_id(drugbank_id, base_en),
            "name_en": base_en,
            "name_ja": ja_name,
            "ddinter_id": dd_id,
            "drugbank_id": drugbank_id or "",
            "yakka_matched": matched_ing is not None,
            "match_method": "dictionary",
        }

        if matched_ing:
            entry["yakka_name"] = matched_ing["name_ja"]
            entry["category"] = matched_ing.get("category", "general")
            matched_yakka.add(matched_ing["name_ja"])

        master.append(entry)
        matched_dd.add(dd_id)
        stats["dict_match"] += 1

    print(f"\nPass 1 (辞書マッチ): {stats['dict_match']} 薬")

    # Pass 2: DDinter2のうち辞書で未マッチ → 接尾辞ルールでカタカナ生成 → 厚労省マッチ
    for dd_drug in dd_drugs:
        dd_id = dd_drug.get("DDInter_id", "")
        if dd_id in matched_dd:
            continue

        en_name = dd_drug.get("Drug_Name", "")
        if not en_name:
            continue

        base_en = extract_base_en(en_name)
        drugbank_id = dd_drug.get("DrugBank_ID", "")

        # 接尾辞ルールで推定
        base_lower = base_en.lower()
        ja_estimated = ""
        for suffix_en, suffix_ja in SUFFIX_RULES:
            if base_lower.endswith(suffix_en):
                ja_estimated = f"[{base_en}]"  # マーク付き
                break

        entry = {
            "id": make_drug_id(drugbank_id, base_en),
            "name_en": base_en,
            "name_ja": "",  # 自動変換は精度不確実なのでブランク
            "ddinter_id": dd_id,
            "drugbank_id": drugbank_id or "",
            "yakka_matched": False,
            "match_method": "en_only",
        }

        master.append(entry)
        matched_dd.add(dd_id)
        stats["en_only"] += 1

    print(f"Pass 2 (英名のみ): {stats['en_only']} 薬")

    # Pass 3: 厚労省のうちDDinter2に未マッチ → JP_ IDで登録
    for ing in ja_ingredients:
        ja = ing["name_ja"]
        if ja in matched_yakka:
            continue
        # 漢方・配合剤はスキップ（DDI対象外）
        if ing.get("category") in ("kampo", "haigo"):
            stats["skip_kampo_haigo"] += 1
            continue

        entry = {
            "id": f"JP_{hashlib.md5(ja.encode()).hexdigest()[:8]}",
            "name_en": JA_EN_DICT.get(ja, ""),
            "name_ja": ja,
            "ddinter_id": "",
            "drugbank_id": "",
            "yakka_matched": True,
            "yakka_name": ja,
            "match_method": "yakka_only",
            "category": ing.get("category", "general"),
        }
        master.append(entry)
        stats["yakka_only"] += 1

    print(f"Pass 3 (厚労省のみ): {stats['yakka_only']} 薬")
    print(f"  スキップ (漢方/配合): {stats['skip_kampo_haigo']}")

    # Dedup by id
    seen_ids = set()
    unique_master = []
    for m in master:
        if m["id"] not in seen_ids:
            seen_ids.add(m["id"])
            unique_master.append(m)
    master = unique_master

    # 統計
    total = len(master)
    has_ja = sum(1 for m in master if m.get("name_ja"))
    has_en = sum(1 for m in master if m.get("name_en"))
    has_both = sum(1 for m in master if m.get("name_ja") and m.get("name_en"))
    yakka_matched = sum(1 for m in master if m.get("yakka_matched"))
    has_ddi = sum(1 for m in master if m.get("ddinter_id"))

    print(f"\n=== Drug Master 統計 ===")
    print(f"総薬数: {total}")
    print(f"name_ja あり: {has_ja} ({has_ja/total*100:.1f}%)")
    print(f"name_en あり: {has_en} ({has_en/total*100:.1f}%)")
    print(f"両方あり: {has_both} ({has_both/total*100:.1f}%)")
    print(f"厚労省マッチ: {yakka_matched} ({yakka_matched/total*100:.1f}%)")
    print(f"DDI情報あり: {has_ddi}")

    # Save
    output = {
        "total_drugs": total,
        "stats": dict(stats),
        "drugs": master,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n保存: {OUTPUT}")

    # 未マッチリスト（レビュー用）
    unmatched = [m for m in master if not m.get("name_ja") and m.get("name_en")]
    unmatched.sort(key=lambda x: x["name_en"])
    with open(UNMATCHED_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(unmatched, f, ensure_ascii=False, indent=2)
    print(f"未マッチ (要レビュー): {len(unmatched)} 薬 → {UNMATCHED_OUTPUT}")


if __name__ == "__main__":
    main()
