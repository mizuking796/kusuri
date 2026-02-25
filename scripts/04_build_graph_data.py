#!/usr/bin/env python3
"""
Step 4: 全データを統合してCytoscape.js用のグラフデータ（JSON）を生成
nodes.json + edges.json → data/graph/ に出力
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter

DATA_DIR = Path(__file__).parent.parent / "data"
GRAPH_DIR = DATA_DIR / "graph"

# 日本語の薬効分類マッピング（主要なもの）
THERAPEUTIC_CATEGORIES = {
    "111": "全身麻酔剤",
    "112": "催眠鎮静剤・抗不安剤",
    "113": "抗てんかん剤",
    "114": "解熱鎮痛消炎剤",
    "115": "覚せい剤・精神神経用剤",
    "116": "抗パーキンソン剤",
    "117": "精神神経用剤",
    "118": "総合感冒剤",
    "119": "その他の中枢神経系用薬",
    "121": "局所麻酔剤",
    "122": "骨格筋弛緩剤",
    "123": "自律神経剤",
    "124": "鎮けい剤",
    "125": "抗ヒスタミン剤",
    "131": "眼科用剤",
    "132": "耳鼻科用剤",
    "133": "鎮暈剤",
    "211": "強心剤",
    "212": "不整脈用剤",
    "213": "利尿剤",
    "214": "血圧降下剤",
    "215": "血管補強剤",
    "216": "血管収縮剤",
    "217": "血管拡張剤",
    "218": "高脂血症用剤",
    "219": "その他の循環器官用薬",
    "221": "気管支拡張剤",
    "222": "含嗽剤",
    "223": "去たん剤",
    "224": "鎮咳剤",
    "225": "気管支喘息治療剤",
    "226": "呼吸促進剤",
    "229": "その他の呼吸器官用薬",
    "231": "止しゃ剤・整腸剤",
    "232": "消化性潰瘍用剤",
    "233": "健胃消化剤",
    "234": "制酸剤",
    "235": "下剤・浣腸剤",
    "236": "利胆剤",
    "237": "膵臓疾患用剤",
    "239": "その他の消化器官用薬",
    "241": "脳下垂体ホルモン剤",
    "242": "唾液腺ホルモン剤",
    "243": "甲状腺・副甲状腺ホルモン剤",
    "244": "たん白同化ステロイド剤",
    "245": "副腎ホルモン剤",
    "246": "男性ホルモン剤",
    "247": "卵胞・黄体ホルモン剤",
    "248": "混合ホルモン剤",
    "249": "その他のホルモン剤",
    "251": "泌尿器官用剤",
    "252": "生殖器官用剤",
    "253": "子宮収縮剤",
    "254": "避妊剤",
    "259": "その他の泌尿生殖器官・肛門用薬",
    "261": "外皮用殺菌消毒剤",
    "264": "鎮痛・鎮痒・収斂・消炎剤",
    "265": "寄生性皮膚疾患用剤",
    "266": "化膿性疾患用剤",
    "267": "皮膚軟化剤",
    "269": "その他の外皮用薬",
    "311": "ビタミンA剤",
    "312": "ビタミンB剤",
    "313": "ビタミンC剤",
    "314": "ビタミンD剤",
    "315": "ビタミンE剤",
    "316": "ビタミンK剤",
    "317": "混合ビタミン剤",
    "319": "その他のビタミン剤",
    "321": "カルシウム剤",
    "322": "無機質製剤",
    "323": "糖類剤",
    "324": "有機酸製剤",
    "325": "たん白質アミノ酸製剤",
    "329": "その他の栄養剤",
    "331": "血液代用剤",
    "332": "止血剤",
    "333": "血液凝固阻止剤",
    "339": "その他の血液・体液用薬",
    "391": "肝臓疾患用剤",
    "392": "解毒剤",
    "393": "習慣性中毒用剤",
    "394": "痛風治療剤",
    "395": "酵素製剤",
    "396": "糖尿病用剤",
    "399": "他に分類されない代謝性医薬品",
    "421": "アルキル化剤",
    "422": "代謝拮抗剤",
    "423": "抗腫瘍性抗生物質製剤",
    "424": "抗腫瘍性植物成分製剤",
    "429": "その他の腫瘍用薬",
    "441": "抗アレルギー剤",
    "442": "刺激療法剤",
    "449": "その他のアレルギー用薬",
    "611": "主としてグラム陽性菌に作用するもの",
    "612": "主としてグラム陰性菌に作用するもの",
    "613": "主としてグラム陽性・陰性菌に作用するもの",
    "614": "主としてグラム陽性菌・マイコプラズマに作用するもの",
    "615": "主としてグラム陰性菌・リケッチア・クラミジアに作用するもの",
    "616": "主として抗酸菌に作用するもの",
    "617": "主としてカビに作用するもの",
    "619": "その他の抗生物質製剤",
    "621": "サルファ剤",
    "622": "抗ウイルス剤",
    "623": "抗結核剤",
    "624": "合成抗菌剤",
    "625": "抗原虫剤",
    "629": "その他の化学療法剤",
    "631": "ワクチン類",
    "632": "毒素・トキソイド類",
    "634": "血液製剤類",
    "639": "その他の生物学的製剤",
    "811": "あへんアルカロイド系麻薬",
    "821": "合成麻薬",
}

# 日本語薬名マッピング（主要薬）
JA_DRUG_NAMES = {
    "Loxoprofen": "ロキソプロフェン",
    "Acetaminophen": "アセトアミノフェン",
    "Ibuprofen": "イブプロフェン",
    "Diclofenac": "ジクロフェナク",
    "Celecoxib": "セレコキシブ",
    "Aspirin": "アスピリン",
    "Indomethacin": "インドメタシン",
    "Naproxen": "ナプロキセン",
    "Etodolac": "エトドラク",
    "Meloxicam": "メロキシカム",
    "Amlodipine": "アムロジピン",
    "Nifedipine": "ニフェジピン",
    "Valsartan": "バルサルタン",
    "Candesartan": "カンデサルタン",
    "Olmesartan": "オルメサルタン",
    "Telmisartan": "テルミサルタン",
    "Losartan": "ロサルタン",
    "Azilsartan": "アジルサルタン",
    "Enalapril": "エナラプリル",
    "Lisinopril": "リシノプリル",
    "Atenolol": "アテノロール",
    "Bisoprolol": "ビソプロロール",
    "Carvedilol": "カルベジロール",
    "Doxazosin": "ドキサゾシン",
    "Diltiazem": "ジルチアゼム",
    "Atorvastatin": "アトルバスタチン",
    "Rosuvastatin": "ロスバスタチン",
    "Pravastatin": "プラバスタチン",
    "Pitavastatin": "ピタバスタチン",
    "Simvastatin": "シンバスタチン",
    "Ezetimibe": "エゼチミブ",
    "Bezafibrate": "ベザフィブラート",
    "Fenofibrate": "フェノフィブラート",
    "Metformin": "メトホルミン",
    "Glimepiride": "グリメピリド",
    "Glibenclamide": "グリベンクラミド",
    "Pioglitazone": "ピオグリタゾン",
    "Sitagliptin": "シタグリプチン",
    "Vildagliptin": "ビルダグリプチン",
    "Alogliptin": "アログリプチン",
    "Linagliptin": "リナグリプチン",
    "Teneligliptin": "テネリグリプチン",
    "Empagliflozin": "エンパグリフロジン",
    "Dapagliflozin": "ダパグリフロジン",
    "Canagliflozin": "カナグリフロジン",
    "Luseogliflozin": "ルセオグリフロジン",
    "Omeprazole": "オメプラゾール",
    "Lansoprazole": "ランソプラゾール",
    "Rabeprazole": "ラベプラゾール",
    "Esomeprazole": "エソメプラゾール",
    "Vonoprazan": "ボノプラザン",
    "Famotidine": "ファモチジン",
    "Ranitidine": "ラニチジン",
    "Teprenone": "テプレノン",
    "Rebamipide": "レバミピド",
    "Mosapride": "モサプリド",
    "Metoclopramide": "メトクロプラミド",
    "Domperidone": "ドンペリドン",
    "Sennoside": "センノシド",
    "Warfarin": "ワルファリン",
    "Clopidogrel": "クロピドグレル",
    "Prasugrel": "プラスグレル",
    "Apixaban": "アピキサバン",
    "Rivaroxaban": "リバーロキサバン",
    "Edoxaban": "エドキサバン",
    "Dabigatran": "ダビガトラン",
    "Cilostazol": "シロスタゾール",
    "Ticlopidine": "チクロピジン",
    "Amoxicillin": "アモキシシリン",
    "Ampicillin": "アンピシリン",
    "Azithromycin": "アジスロマイシン",
    "Clarithromycin": "クラリスロマイシン",
    "Erythromycin": "エリスロマイシン",
    "Levofloxacin": "レボフロキサシン",
    "Ciprofloxacin": "シプロフロキサシン",
    "Moxifloxacin": "モキシフロキサシン",
    "Minocycline": "ミノサイクリン",
    "Doxycycline": "ドキシサイクリン",
    "Vancomycin": "バンコマイシン",
    "Meropenem": "メロペネム",
    "Metronidazole": "メトロニダゾール",
    "Diazepam": "ジアゼパム",
    "Etizolam": "エチゾラム",
    "Alprazolam": "アルプラゾラム",
    "Lorazepam": "ロラゼパム",
    "Clonazepam": "クロナゼパム",
    "Zolpidem": "ゾルピデム",
    "Zopiclone": "ゾピクロン",
    "Eszopiclone": "エスゾピクロン",
    "Suvorexant": "スボレキサント",
    "Lemborexant": "レンボレキサント",
    "Ramelteon": "ラメルテオン",
    "Sertraline": "セルトラリン",
    "Paroxetine": "パロキセチン",
    "Escitalopram": "エスシタロプラム",
    "Fluvoxamine": "フルボキサミン",
    "Duloxetine": "デュロキセチン",
    "Venlafaxine": "ベンラファキシン",
    "Mirtazapine": "ミルタザピン",
    "Amitriptyline": "アミトリプチリン",
    "Aripiprazole": "アリピプラゾール",
    "Olanzapine": "オランザピン",
    "Quetiapine": "クエチアピン",
    "Risperidone": "リスペリドン",
    "Haloperidol": "ハロペリドール",
    "Valproic acid": "バルプロ酸",
    "Carbamazepine": "カルバマゼピン",
    "Lamotrigine": "ラモトリギン",
    "Levodopa": "レボドパ",
    "Pramipexole": "プラミペキソール",
    "Donepezil": "ドネペジル",
    "Montelukast": "モンテルカスト",
    "Pranlukast": "プランルカスト",
    "Theophylline": "テオフィリン",
    "Fexofenadine": "フェキソフェナジン",
    "Cetirizine": "セチリジン",
    "Loratadine": "ロラタジン",
    "Desloratadine": "デスロラタジン",
    "Olopatadine": "オロパタジン",
    "Bepotastine": "ベポタスチン",
    "Epinastine": "エピナスチン",
    "Prednisolone": "プレドニゾロン",
    "Dexamethasone": "デキサメタゾン",
    "Betamethasone": "ベタメタゾン",
    "Tamsulosin": "タムスロシン",
    "Silodosin": "シロドシン",
    "Naftopidil": "ナフトピジル",
    "Dutasteride": "デュタステリド",
    "Mirabegron": "ミラベグロン",
    "Solifenacin": "ソリフェナシン",
    "Tadalafil": "タダラフィル",
    "Alendronate": "アレンドロン酸",
    "Risedronate": "リセドロン酸",
    "Denosumab": "デノスマブ",
    "Levothyroxine": "レボチロキシン",
    "Thiamazole": "チアマゾール",
    "Allopurinol": "アロプリノール",
    "Febuxostat": "フェブキソスタット",
    "Colchicine": "コルヒチン",
    "Benzbromarone": "ベンズブロマロン",
    "Acyclovir": "アシクロビル",
    "Valacyclovir": "バラシクロビル",
    "Oseltamivir": "オセルタミビル",
    "Fluconazole": "フルコナゾール",
    "Itraconazole": "イトラコナゾール",
    "Terbinafine": "テルビナフィン",
    "Tacrolimus": "タクロリムス",
    "Cyclosporine": "シクロスポリン",
    "Furosemide": "フロセミド",
    "Spironolactone": "スピロノラクトン",
    "Eplerenone": "エプレレノン",
    "Digoxin": "ジゴキシン",
    "Amiodarone": "アミオダロン",
    "Nicorandil": "ニコランジル",
    "Gabapentin": "ガバペンチン",
    "Pregabalin": "プレガバリン",
    "Tramadol": "トラマドール",
    "Morphine": "モルヒネ",
    "Fentanyl": "フェンタニル",
    "Oxycodone": "オキシコドン",
    "Magnesium oxide": "酸化マグネシウム",
    "Diphenhydramine": "ジフェンヒドラミン",
    "Chlorpheniramine": "クロルフェニラミン",
    "Caffeine": "カフェイン",
    "Loperamide": "ロペラミド",
    "Codeine": "コデイン",
    "Dextromethorphan": "デキストロメトルファン",
    "Lithium carbonate": "炭酸リチウム",
    "Insulin glargine": "インスリン グラルギン",
    "Insulin aspart": "インスリン アスパルト",
    "Liraglutide": "リラグルチド",
    "Dulaglutide": "デュラグルチド",
    "Cefcapene pivoxil": "セフカペン ピボキシル",
    "Cefditoren pivoxil": "セフジトレン ピボキシル",
    "Cephalexin": "セファレキシン",
    "Sulfamethoxazole": "スルファメトキサゾール",
    "Ropinirole": "ロピニロール",
    "Budesonide": "ブデソニド",
    "Fluticasone": "フルチカゾン",
    "Beclomethasone": "ベクロメタゾン",
    "Salmeterol": "サルメテロール",
    "Formoterol": "ホルモテロール",
    "Tiotropium": "チオトロピウム",
    "Bilastine": "ビラスチン",
    "Finasteride": "フィナステリド",
    "Denosumab": "デノスマブ",
    "Eldecalcitol": "エルデカルシトール",
    "Alfacalcidol": "アルファカルシドール",
    "Baloxavir marboxil": "バロキサビル マルボキシル",
    "Mycophenolate mofetil": "ミコフェノール酸モフェチル",
    "Potassium chloride": "塩化カリウム",
    "Bismuth": "次サリチル酸ビスマス",
    "Hydrochlorothiazide": "ヒドロクロロチアジド",
}


def load_data():
    """全データソースを読み込み"""
    drugs_file = DATA_DIR / "initial_drugs.json"
    ddi_file = DATA_DIR / "ddi_internal.json"
    adverse_file = DATA_DIR / "adverse_effects.json"

    if not drugs_file.exists():
        raise FileNotFoundError(f"{drugs_file} not found. Run 01_build_drug_list.py first.")

    with open(drugs_file) as f:
        drugs = json.load(f)

    ddi = []
    if ddi_file.exists():
        with open(ddi_file) as f:
            ddi = json.load(f)
    else:
        print("WARNING: ddi_internal.json not found. Run 02_fetch_ddi.py first.")

    adverse = []
    if adverse_file.exists():
        with open(adverse_file) as f:
            adverse = json.load(f)
    else:
        print("WARNING: adverse_effects.json not found. Run 03_fetch_jader.py first.")

    return drugs, ddi, adverse


def build_nodes(drugs, adverse):
    """ノードデータの構築"""
    nodes = []
    adverse_map = {a['kegg_id']: a['adverse_effects'] for a in adverse}
    adverse_nodes = {}  # name → id
    category_nodes = {}  # code → id
    cyp_nodes = {}  # name → id

    # Drug nodes
    for drug in drugs:
        kegg_id = drug['kegg_id']
        search_name = drug.get('search_name', '')
        # Prefer existing name_ja from drug data, fallback to manual mapping
        name_ja = drug.get('name_ja', '') or JA_DRUG_NAMES.get(search_name, '')

        node = {
            'id': kegg_id,
            'type': 'drug',
            'name_en': drug.get('name_en', search_name),
            'name_ja': name_ja,
            'names_alt': drug.get('names_alt', []),
            'search_name': search_name,
            'formula': drug.get('formula', ''),
            'efficacy': drug.get('efficacy', ''),
            'therapeutic_category': drug.get('therapeutic_category', ''),
            'atc_code': drug.get('atc_code', ''),
            'drug_class': drug.get('drug_class', []),
            'cyp_enzymes': drug.get('cyp_enzymes', []),
            'adverse_effects': adverse_map.get(kegg_id, []),
        }
        nodes.append(node)

        # Collect category nodes
        tc = drug.get('therapeutic_category', '')
        if tc and tc not in category_nodes:
            cat_name = THERAPEUTIC_CATEGORIES.get(tc, f"分類{tc}")
            cat_id = f"cat_{tc}"
            category_nodes[tc] = cat_id
            nodes.append({
                'id': cat_id,
                'type': 'category',
                'name_ja': cat_name,
                'name_en': '',
                'code': tc,
            })

        # Collect CYP nodes
        for cyp in drug.get('cyp_enzymes', []):
            if cyp not in cyp_nodes:
                cyp_id = f"cyp_{cyp}"
                cyp_nodes[cyp] = cyp_id
                nodes.append({
                    'id': cyp_id,
                    'type': 'cyp',
                    'name_en': cyp,
                    'name_ja': cyp,
                })

        # Collect adverse effect nodes
        for ae in adverse_map.get(kegg_id, []):
            ae_name = ae['name']
            if ae_name not in adverse_nodes:
                ae_id = f"ae_{len(adverse_nodes)}"
                adverse_nodes[ae_name] = ae_id
                nodes.append({
                    'id': ae_id,
                    'type': 'adverse_effect',
                    'name_ja': ae_name,
                    'name_en': ae.get('name_en', ''),
                })

    return nodes, category_nodes, cyp_nodes, adverse_nodes


def build_edges(drugs, ddi, category_nodes, cyp_nodes, adverse_nodes, adverse_data):
    """エッジデータの構築"""
    edges = []
    edge_id = 0

    # DDI edges (drug ↔ drug)
    for ix in ddi:
        edge_id += 1
        edges.append({
            'id': f"e_{edge_id}",
            'source': ix['drug1'],
            'target': ix['drug2'],
            'type': 'contraindication' if ix['severity'] == 'CI' else 'precaution',
            'severity': ix['severity'],
            'mechanism': ix.get('mechanism', ''),
        })

    # Drug → Category edges
    for drug in drugs:
        tc = drug.get('therapeutic_category', '')
        if tc and tc in category_nodes:
            edge_id += 1
            edges.append({
                'id': f"e_{edge_id}",
                'source': drug['kegg_id'],
                'target': category_nodes[tc],
                'type': 'belongs_to_category',
            })

    # Drug → CYP edges
    for drug in drugs:
        for cyp in drug.get('cyp_enzymes', []):
            if cyp in cyp_nodes:
                edge_id += 1
                edges.append({
                    'id': f"e_{edge_id}",
                    'source': drug['kegg_id'],
                    'target': cyp_nodes[cyp],
                    'type': 'metabolized_by',
                })

    # Drug → Adverse Effect edges
    adverse_map = {a['kegg_id']: a['adverse_effects'] for a in adverse_data}
    for drug in drugs:
        kegg_id = drug['kegg_id']
        for ae in adverse_map.get(kegg_id, []):
            ae_name = ae['name']
            if ae_name in adverse_nodes:
                edge_id += 1
                edges.append({
                    'id': f"e_{edge_id}",
                    'source': kegg_id,
                    'target': adverse_nodes[ae_name],
                    'type': 'causes_adverse_effect',
                    'frequency': ae.get('frequency', ''),
                })

    return edges


def main():
    print("=== Building Cytoscape.js graph data ===\n")

    drugs, ddi, adverse = load_data()
    print(f"Drugs: {len(drugs)}")
    print(f"DDI pairs: {len(ddi)}")
    print(f"Adverse effect entries: {len(adverse)}")

    # Build nodes
    nodes, category_nodes, cyp_nodes, adverse_nodes = build_nodes(drugs, adverse)

    # Build edges
    edges = build_edges(drugs, ddi, category_nodes, cyp_nodes, adverse_nodes, adverse)

    # Stats
    node_types = Counter(n.get('type', 'unknown') for n in nodes)
    edge_types = Counter(e.get('type', 'unknown') for e in edges)

    print(f"\n=== Node Summary ===")
    for t, c in node_types.most_common():
        print(f"  {t}: {c}")
    print(f"  Total: {len(nodes)}")

    print(f"\n=== Edge Summary ===")
    for t, c in edge_types.most_common():
        print(f"  {t}: {c}")
    print(f"  Total: {len(edges)}")

    # Save
    GRAPH_DIR.mkdir(exist_ok=True)

    # Individual files (for modular loading)
    with open(GRAPH_DIR / "nodes.json", "w", encoding='utf-8') as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)

    with open(GRAPH_DIR / "edges.json", "w", encoding='utf-8') as f:
        json.dump(edges, f, ensure_ascii=False, indent=2)

    # Combined file (for single-load)
    combined = {'nodes': nodes, 'edges': edges}
    with open(GRAPH_DIR / "graph.json", "w", encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to:")
    print(f"  {GRAPH_DIR / 'nodes.json'}")
    print(f"  {GRAPH_DIR / 'edges.json'}")
    print(f"  {GRAPH_DIR / 'graph.json'}")


if __name__ == '__main__':
    main()
