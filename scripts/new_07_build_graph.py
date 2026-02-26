#!/usr/bin/env python3
"""
new_07_build_graph.py
全データを統合して graph-light.json を生成。

入力:
  data/drug_master.json        — 薬マスタ（名寄せ済み）
  data/ddinter_interactions.json — DDI相互作用
  data/cyp_data.json           — CYP代謝情報
  data/adverse_effects_new.json — 副作用
  data/brand_names_new.json    — 商品名

出力:
  data/graph/graph-light.json  — Cytoscape.js用グラフデータ
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
GRAPH_DIR = DATA_DIR / "graph"

INPUT_FILES = {
    "drug_master": DATA_DIR / "drug_master.json",
    "ddinter_ddi": DATA_DIR / "ddinter_interactions.json",
    "cyp_data": DATA_DIR / "cyp_data.json",
    "adverse_effects": DATA_DIR / "adverse_effects_new.json",
    "brand_names": DATA_DIR / "brand_names_new.json",
}

OUTPUT = GRAPH_DIR / "graph-light.json"

# 日本語の薬効分類（04_build_graph_data.py 由来）
THERAPEUTIC_CATEGORIES = {
    "111": "全身麻酔剤", "112": "催眠鎮静剤・抗不安剤", "113": "抗てんかん剤",
    "114": "解熱鎮痛消炎剤", "115": "覚せい剤・精神神経用剤", "116": "抗パーキンソン剤",
    "117": "精神神経用剤", "118": "総合感冒剤", "119": "その他の中枢神経系用薬",
    "121": "局所麻酔剤", "122": "骨格筋弛緩剤", "123": "自律神経剤",
    "124": "鎮けい剤", "125": "抗ヒスタミン剤",
    "131": "眼科用剤", "132": "耳鼻科用剤", "133": "鎮暈剤",
    "211": "強心剤", "212": "不整脈用剤", "213": "利尿剤",
    "214": "血圧降下剤", "215": "血管補強剤", "216": "血管収縮剤",
    "217": "血管拡張剤", "218": "高脂血症用剤", "219": "その他の循環器官用薬",
    "221": "気管支拡張剤", "222": "含嗽剤", "223": "去たん剤",
    "224": "鎮咳剤", "225": "気管支喘息治療剤", "226": "呼吸促進剤",
    "229": "その他の呼吸器官用薬",
    "231": "止しゃ剤・整腸剤", "232": "消化性潰瘍用剤", "233": "健胃消化剤",
    "234": "制酸剤", "235": "下剤・浣腸剤", "236": "利胆剤",
    "237": "膵臓疾患用剤", "239": "その他の消化器官用薬",
    "241": "脳下垂体ホルモン剤", "242": "唾液腺ホルモン剤",
    "243": "甲状腺・副甲状腺ホルモン剤", "244": "たん白同化ステロイド剤",
    "245": "副腎ホルモン剤", "246": "男性ホルモン剤", "247": "卵胞・黄体ホルモン剤",
    "248": "混合ホルモン剤", "249": "その他のホルモン剤",
    "251": "泌尿器官用剤", "252": "生殖器官用剤", "253": "子宮収縮剤",
    "254": "避妊剤", "259": "その他の泌尿生殖器官・肛門用薬",
    "261": "外皮用殺菌消毒剤", "264": "鎮痛・鎮痒・収斂・消炎剤",
    "265": "寄生性皮膚疾患用剤", "266": "化膿性疾患用剤",
    "267": "皮膚軟化剤", "269": "その他の外皮用薬",
    "311": "ビタミンA剤", "312": "ビタミンB剤", "313": "ビタミンC剤",
    "314": "ビタミンD剤", "315": "ビタミンE剤", "316": "ビタミンK剤",
    "317": "混合ビタミン剤", "319": "その他のビタミン剤",
    "321": "カルシウム剤", "322": "無機質製剤", "323": "糖類剤",
    "324": "有機酸製剤", "325": "たん白質アミノ酸製剤", "329": "その他の栄養剤",
    "331": "血液代用剤", "332": "止血剤", "333": "血液凝固阻止剤",
    "339": "その他の血液・体液用薬",
    "391": "肝臓疾患用剤", "392": "解毒剤", "393": "習慣性中毒用剤",
    "394": "痛風治療剤", "395": "酵素製剤", "396": "糖尿病用剤",
    "399": "他に分類されない代謝性医薬品",
    "421": "アルキル化剤", "422": "代謝拮抗剤", "423": "抗腫瘍性抗生物質製剤",
    "424": "抗腫瘍性植物成分製剤", "429": "その他の腫瘍用薬",
    "441": "抗アレルギー剤", "442": "刺激療法剤", "449": "その他のアレルギー用薬",
    "611": "主としてグラム陽性菌に作用するもの",
    "612": "主としてグラム陰性菌に作用するもの",
    "613": "主としてグラム陽性・陰性菌に作用するもの",
    "614": "主としてグラム陽性菌・マイコプラズマに作用するもの",
    "615": "主としてグラム陰性菌・リケッチア・クラミジアに作用するもの",
    "616": "主として抗酸菌に作用するもの",
    "617": "主としてカビに作用するもの", "619": "その他の抗生物質製剤",
    "621": "サルファ剤", "622": "抗ウイルス剤", "623": "抗結核剤",
    "624": "合成抗菌剤", "625": "抗原虫剤", "629": "その他の化学療法剤",
    "631": "ワクチン類", "632": "毒素・トキソイド類",
    "634": "血液製剤類", "639": "その他の生物学的製剤",
    "811": "あへんアルカロイド系麻薬", "821": "合成麻薬",
}

# 薬効分類推定（英名の接尾辞ベース）
NAME_TO_CATEGORY = {
    r"statin$": "218",      # 高脂血症用剤
    r"sartan$": "214",      # 血圧降下剤
    r"pril$": "214",        # ACE阻害（降圧）
    r"dipine$": "214",      # Ca拮抗（降圧）
    r"olol$": "214",        # β遮断（降圧）
    r"semide$": "213",      # 利尿剤
    r"gliptin$": "396",     # 糖尿病用剤
    r"gliflozin$": "396",   # SGLT2阻害
    r"glutide$": "396",     # GLP-1
    r"prazole$": "232",     # PPI
    r"floxacin$": "624",    # ニューキノロン
    r"cillin$": "613",      # ペニシリン系
    r"mycin$": "614",       # マクロライド系
    r"azole$": "617",       # 抗真菌
    r"(pam|lam|zepam|zolam)$": "112",  # ベンゾ
    r"(oxetine|aline)$": "117",  # 抗うつ
    r"(apine|idone)$": "117",    # 抗精神病
    r"profen$": "114",      # NSAIDs
    r"(xaban|gatran)$": "333",   # 抗凝固
    r"(platin|taxel|rubicin)$": "429",  # 抗がん
    r"(mab|zumab)$": "429",      # 分子標的薬
    r"vir$": "622",         # 抗ウイルス
}

import re


def estimate_category(name_en: str) -> str:
    """英名から薬効分類コードを推定"""
    lower = name_en.lower()
    for pattern, code in NAME_TO_CATEGORY.items():
        if re.search(pattern, lower):
            return code
    return ""


def load_data() -> dict:
    """全入力データを読み込み"""
    data = {}
    for key, path in INPUT_FILES.items():
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data[key] = json.load(f)
            print(f"  {key}: loaded ({path.name})")
        else:
            print(f"  WARNING: {path.name} not found")
            data[key] = {}
    return data


def build_graph(data: dict) -> dict:
    """全データを統合してグラフ構造を構築"""
    master = data.get("drug_master", {})
    all_drugs = master.get("drugs", [])
    ddi_data = data.get("ddinter_ddi", {})
    ddis = ddi_data.get("interactions", [])
    cyp_data = data.get("cyp_data", {}).get("cyp_data", {})
    ae_data = data.get("adverse_effects", {}).get("adverse_effects", [])
    brand_data = data.get("brand_names", {}).get("brand_names", {})

    print(f"\n=== 入力データ（フィルタ前） ===")
    print(f"薬数: {len(all_drugs)}")
    print(f"DDIペア: {len(ddis)}")

    # ============ フィルタ: 日本市場関連薬に絞り込み ============
    # Step 1: name_ja ありの薬を「コア薬」とする
    # Step 2: コア薬のDDIパートナーを追加（name_jaなしでも）
    # Step 3: Minor DDI (Level 1) は除外してサイズ削減
    ddinter_to_id_all = {}
    for d in all_drugs:
        if d.get("ddinter_id"):
            ddinter_to_id_all[d["ddinter_id"]] = d["id"]

    drug_by_id_all = {d["id"]: d for d in all_drugs}

    # コア薬 = name_jaあり
    core_ids = set()
    for d in all_drugs:
        if d.get("name_ja"):
            core_ids.add(d["id"])

    print(f"コア薬 (name_jaあり): {len(core_ids)}")

    # DDIフィルタ: コア薬(name_jaあり)同士のDDIのみ保持
    # さらに Minor DDI (Level 1) は除外
    filtered_ddis = []
    ddi_seen = set()
    for ix in ddis:
        level_str = str(ix.get("level", "")).strip()
        if level_str == "1":  # Minor DDI は除外
            continue
        id_a = ddinter_to_id_all.get(ix["drug_a"], ix["drug_a"])
        id_b = ddinter_to_id_all.get(ix["drug_b"], ix["drug_b"])
        # 両端がコア薬（name_jaあり）
        if id_a in core_ids and id_b in core_ids:
            pair = tuple(sorted([id_a, id_b]))
            if pair not in ddi_seen:
                ddi_seen.add(pair)
                filtered_ddis.append((ix, id_a, id_b, level_str))
    ddis_to_process = filtered_ddis

    # 最終薬リスト = コア薬のみ（DDIパートナーは必然的にコア内）
    drugs = [d for d in all_drugs if d["id"] in core_ids]

    print(f"フィルタ後薬数: {len(drugs)} (除外: {len(all_drugs) - len(drugs)})")
    print(f"DDI (コア薬間, Minor除外, dedup): {len(ddis_to_process)} (元: {len(ddis)})")
    print(f"CYPデータ薬数: {len(cyp_data)}")
    print(f"副作用データ薬数: {len(ae_data)}")
    print(f"商品名マッチ薬数: {len(brand_data)}")

    # Build lookup maps
    drug_by_id = {d["id"]: d for d in drugs}
    # DDinter ID → drug ID
    ddinter_to_id = {}
    for d in drugs:
        if d.get("ddinter_id"):
            ddinter_to_id[d["ddinter_id"]] = d["id"]
    # EN name (lower) → drug ID
    en_to_id = {}
    for d in drugs:
        if d.get("name_en"):
            en_to_id[d["name_en"].lower()] = d["id"]

    ae_by_drug = {ae["drug_id"]: ae for ae in ae_data}

    nodes = []
    edges = []
    category_nodes = {}
    cyp_nodes = {}
    adverse_nodes = {}
    edge_id = 0

    # ============ Drug Nodes ============
    for drug in drugs:
        drug_id = drug["id"]
        name_en = drug.get("name_en", "")
        name_ja = drug.get("name_ja", "")

        # CYP情報
        cyp_enzymes = cyp_data.get(name_en.lower(), [])

        # 副作用
        ae_entry = ae_by_drug.get(drug_id, {})
        adverse_effects = ae_entry.get("adverse_effects", [])

        # 商品名
        brands = brand_data.get(drug_id, [])
        names_alt = brands.copy()

        # 薬効分類推定
        tc = drug.get("therapeutic_category", "") or estimate_category(name_en)

        node = {
            "id": drug_id,
            "type": "drug",
            "name_en": name_en,
            "name_ja": name_ja,
            "names_alt": names_alt,
            "search_name": name_en,
            "therapeutic_category": tc,
            "cyp_enzymes": cyp_enzymes,
            "adverse_effects": adverse_effects,
            "drugbank_id": drug.get("drugbank_id", ""),
        }
        nodes.append(node)

        # Category node
        if tc and tc not in category_nodes:
            cat_name = THERAPEUTIC_CATEGORIES.get(tc, f"分類{tc}")
            cat_id = f"cat_{tc}"
            category_nodes[tc] = cat_id
            nodes.append({
                "id": cat_id,
                "type": "category",
                "name_ja": cat_name,
                "name_en": "",
                "code": tc,
            })

        # CYP nodes
        for cyp in cyp_enzymes:
            if cyp not in cyp_nodes:
                cyp_id = f"cyp_{cyp}"
                cyp_nodes[cyp] = cyp_id
                nodes.append({
                    "id": cyp_id,
                    "type": "cyp",
                    "name_en": cyp,
                    "name_ja": cyp,
                })

        # Adverse effect nodes
        for ae in adverse_effects:
            ae_name = ae["name"]
            if ae_name not in adverse_nodes:
                ae_id = f"ae_{len(adverse_nodes)}"
                adverse_nodes[ae_name] = ae_id
                nodes.append({
                    "id": ae_id,
                    "type": "adverse_effect",
                    "name_ja": ae_name,
                    "name_en": ae.get("name_en", ""),
                })

    # ============ Edges ============

    # DDI edges (already filtered in preprocessing)
    valid_ids = {n["id"] for n in nodes if n["type"] == "drug"}
    ddi_stats = Counter()
    seen_ddi_pairs = set()

    for ix_tuple in ddis_to_process:
        ix, id_a, id_b, level_str = ix_tuple

        if id_a not in valid_ids or id_b not in valid_ids:
            ddi_stats["skip_missing"] += 1
            continue

        if id_a == id_b:
            ddi_stats["skip_selfloop"] += 1
            continue

        # Dedup
        pair_key = tuple(sorted([id_a, id_b]))
        if pair_key in seen_ddi_pairs:
            continue
        seen_ddi_pairs.add(pair_key)

        if level_str in ("3", "Major"):
            edge_type = "contraindication"
            severity = "CI"
        else:
            edge_type = "precaution"
            severity = "P"

        edge_id += 1
        edges.append({
            "id": f"e_{edge_id}",
            "source": id_a,
            "target": id_b,
            "type": edge_type,
            "severity": severity,
        })
        ddi_stats[edge_type] += 1

    print(f"\nDDI処理: {dict(ddi_stats)}")

    # Category edges
    for drug in drugs:
        drug_id = drug["id"]
        tc = drug.get("therapeutic_category", "") or estimate_category(drug.get("name_en", ""))
        if tc and tc in category_nodes:
            edge_id += 1
            edges.append({
                "id": f"e_{edge_id}",
                "source": drug_id,
                "target": category_nodes[tc],
                "type": "belongs_to_category",
            })

    # CYP edges
    for drug in drugs:
        drug_id = drug["id"]
        name_en = drug.get("name_en", "").lower()
        for cyp in cyp_data.get(name_en, []):
            if cyp in cyp_nodes:
                edge_id += 1
                edges.append({
                    "id": f"e_{edge_id}",
                    "source": drug_id,
                    "target": cyp_nodes[cyp],
                    "type": "metabolized_by",
                })

    # Adverse effect edges
    for ae_entry in ae_data:
        drug_id = ae_entry["drug_id"]
        if drug_id not in valid_ids:
            continue
        for ae in ae_entry.get("adverse_effects", []):
            ae_name = ae["name"]
            if ae_name in adverse_nodes:
                edge_id += 1
                edges.append({
                    "id": f"e_{edge_id}",
                    "source": drug_id,
                    "target": adverse_nodes[ae_name],
                    "type": "causes_adverse_effect",
                    "frequency": ae.get("frequency", ""),
                })

    return {"nodes": nodes, "edges": edges}


def validate(graph: dict) -> bool:
    """グラフのバリデーション"""
    print(f"\n=== バリデーション ===")
    nodes = graph["nodes"]
    edges = graph["edges"]
    ok = True

    # 1. ノードID一意性
    ids = [n["id"] for n in nodes]
    dupes = [id for id, cnt in Counter(ids).items() if cnt > 1]
    if dupes:
        print(f"  FAIL: 重複ノードID: {dupes[:5]}")
        ok = False
    else:
        print(f"  OK: ノードID一意 ({len(ids)})")

    # 2. エッジ参照整合性
    node_ids = set(ids)
    bad_refs = 0
    for e in edges:
        if e.get("source") not in node_ids:
            bad_refs += 1
        if e.get("target") not in node_ids:
            bad_refs += 1
    if bad_refs:
        print(f"  FAIL: 参照エラー {bad_refs} エッジ")
        ok = False
    else:
        print(f"  OK: エッジ参照整合 ({len(edges)})")

    # 3. 自己ループ
    self_loops = sum(1 for e in edges if e.get("source") == e.get("target"))
    if self_loops:
        print(f"  WARN: 自己ループ {self_loops} 件")
    else:
        print(f"  OK: 自己ループなし")

    # 4. DDIがdrug-drug間のみ
    drug_ids = {n["id"] for n in nodes if n["type"] == "drug"}
    ddi_edges = [e for e in edges if e["type"] in ("contraindication", "precaution")]
    bad_ddi = sum(1 for e in ddi_edges
                  if e["source"] not in drug_ids or e["target"] not in drug_ids)
    if bad_ddi:
        print(f"  FAIL: 非drug-drug DDI {bad_ddi} 件")
        ok = False
    else:
        print(f"  OK: DDI全てdrug-drug間")

    return ok


def print_stats(graph: dict):
    """統計を出力"""
    nodes = graph["nodes"]
    edges = graph["edges"]

    nt = Counter(n["type"] for n in nodes)
    et = Counter(e["type"] for e in edges)

    drugs = [n for n in nodes if n["type"] == "drug"]
    has_ja = sum(1 for d in drugs if d.get("name_ja"))
    has_cyp = sum(1 for d in drugs if d.get("cyp_enzymes"))
    has_ae = sum(1 for d in drugs if d.get("adverse_effects"))
    has_alt = sum(1 for d in drugs if d.get("names_alt"))

    print(f"\n=== ノード統計 ===")
    for t, c in nt.most_common():
        print(f"  {t}: {c}")
    print(f"  合計: {len(nodes)}")

    print(f"\n=== エッジ統計 ===")
    for t, c in et.most_common():
        print(f"  {t}: {c}")
    print(f"  合計: {len(edges)}")

    print(f"\n=== カバレッジ ===")
    print(f"  name_ja: {has_ja}/{len(drugs)} ({has_ja/len(drugs)*100:.1f}%)")
    print(f"  CYP: {has_cyp}/{len(drugs)}")
    print(f"  副作用: {has_ae}/{len(drugs)}")
    print(f"  商品名: {has_alt}/{len(drugs)}")

    # 定量比較
    print(f"\n=== 定量比較（現行vs新） ===")
    print(f"  薬ノード: {nt.get('drug', 0)} (現行2,600, 許容2,000-3,000)")
    ci = et.get("contraindication", 0)
    p = et.get("precaution", 0)
    print(f"  DDI(CI): {ci} (現行4,019, 許容2,000-6,000)")
    print(f"  DDI(P): {p} (現行18,327, 許容10,000-30,000)")
    ja_rate = has_ja / len(drugs) * 100 if drugs else 0
    print(f"  name_ja率: {ja_rate:.1f}% (現行79%, 目標>80%)")

    # 主要薬チェック
    print(f"\n=== 主要薬チェック ===")
    check_drugs = [
        "Warfarin", "Loxoprofen", "Clarithromycin", "Amiodarone",
        "Amlodipine", "Lansoprazole", "Carbamazepine", "Cyclosporine",
        "Metformin", "Prednisolone",
    ]
    for name in check_drugs:
        found = [d for d in drugs if d.get("name_en", "").lower() == name.lower()
                 or d.get("search_name", "").lower() == name.lower()]
        if found:
            d = found[0]
            print(f"  {name}: id={d['id']}, ja={d.get('name_ja','?')}, "
                  f"cyp={len(d.get('cyp_enzymes',[]))}, ae={len(d.get('adverse_effects',[]))}")
        else:
            print(f"  {name}: NOT FOUND")


def main():
    print("=== graph-light.json 統合ビルド ===\n")

    # Load
    print("データ読み込み:")
    data = load_data()

    # Build
    graph = build_graph(data)

    # Validate
    valid = validate(graph)

    # Stats
    print_stats(graph)

    # Save
    GRAPH_DIR.mkdir(exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f"\n保存: {OUTPUT} ({size_mb:.1f} MB)")

    if not valid:
        print("\nWARNING: バリデーションエラーあり。確認してください。")
        sys.exit(1)
    else:
        print("\nSUCCESS: バリデーション通過")


if __name__ == "__main__":
    main()
