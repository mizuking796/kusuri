#!/usr/bin/env python3
"""
10_kegg_ja_fetch.py — KEGG日本語薬効分類(jp08301)から日本語名を一括取得

KEGG BRITE jp08301 は日本語の薬効分類で、各薬のIDと日本語名が含まれる。
1回のAPI呼び出しで全件取得可能（APIレート制限なし）。

取得した日本語名を graph-light.json の name_ja に反映する。
"""

import json, re, os
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH_LIGHT = os.path.join(BASE, 'data', 'graph', 'graph-light.json')
ALL_DRUGS = os.path.join(BASE, 'data', 'all_drugs_detail.json')

def fetch_kegg_ja_names():
    """KEGG BRITE jp08301 から KEGG_ID → 日本語名 マッピングを取得"""
    url = "https://rest.kegg.jp/get/br:jp08301"
    print(f"Fetching {url} ...")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode('utf-8')

    # Parse: lines like "E        D00714  チオペンタールナトリウム (JP18)"
    ja_names = {}
    for line in text.split('\n'):
        m = re.match(r'^E\s+(D\d{5})\s+(.+)$', line)
        if m:
            kegg_id = m.group(1)
            name_raw = m.group(2).strip()
            # Remove (JP18), (JAN), (USAN) etc. suffixes
            name_clean = re.sub(r'\s*\((?:JP\d+|JAN|USAN|INN|USP|JAN/USAN|JAN/INN)\)\s*$', '', name_raw).strip()
            # Remove trailing semicolons
            name_clean = name_clean.rstrip(';').strip()
            if kegg_id not in ja_names:
                ja_names[kegg_id] = name_clean

    print(f"  Fetched {len(ja_names)} Japanese drug names")
    return ja_names


def fetch_kegg_ja_product_names():
    """KEGG BRITE jp08311 (日本薬局方) からも取得"""
    url = "https://rest.kegg.jp/get/br:jp08311"
    print(f"Fetching {url} ...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode('utf-8')
    except Exception as e:
        print(f"  Failed: {e}")
        return {}

    ja_names = {}
    for line in text.split('\n'):
        m = re.match(r'^B\s+(D\d{5})\s+(.+)$', line)
        if m:
            kegg_id = m.group(1)
            name_raw = m.group(2).strip()
            name_clean = re.sub(r'\s*\((?:JP\d+|JAN|USAN|INN|USP)\)\s*$', '', name_raw).strip()
            if kegg_id not in ja_names:
                ja_names[kegg_id] = name_clean

    print(f"  Fetched {len(ja_names)} names from JP pharmacopoeia")
    return ja_names


def fetch_kegg_metabolism():
    """KEGG APIから全薬のmetabolismフィールドを再取得（バッチ）"""
    # This would require individual API calls for 2600 drugs
    # Instead, let's re-parse existing all_drugs_detail.json more carefully
    with open(ALL_DRUGS, 'r') as f:
        all_drugs = json.load(f)

    cyp_map = {}
    for d in all_drugs:
        kegg_id = d['kegg_id']
        metab = d.get('metabolism', '')
        if metab:
            # More aggressive CYP extraction
            cyps = set()
            # Standard pattern: CYP followed by family/subfamily
            for m in re.finditer(r'CYP(\d\w+)', metab):
                cyp_name = f"CYP{m.group(1)}"
                # Normalize CYP3A to CYP3A4
                if cyp_name == 'CYP3A':
                    cyp_name = 'CYP3A4'
                cyps.add(cyp_name)
            if cyps:
                cyp_map[kegg_id] = sorted(cyps)

    print(f"  Re-parsed metabolism: {len(cyp_map)} drugs with CYP data")
    return cyp_map


def extract_trade_names_from_kegg():
    """all_drugs_detail.json の names_alt から (TN) 商品名を抽出"""
    with open(ALL_DRUGS, 'r') as f:
        all_drugs = json.load(f)

    brand_map = {}
    for d in all_drugs:
        kegg_id = d['kegg_id']
        alts = d.get('names_alt', [])
        brands = []
        for alt in alts:
            if '(TN)' in alt:
                name = alt.replace('(TN)', '').strip()
                brands.append(name)
        if brands:
            brand_map[kegg_id] = brands

    print(f"  Extracted trade names: {len(brand_map)} drugs with brand names")
    return brand_map


def main():
    # 1. Fetch Japanese names from KEGG BRITE
    ja_names = fetch_kegg_ja_names()
    ja_names_jp = fetch_kegg_ja_product_names()

    # Merge (jp08301 takes priority)
    for k, v in ja_names_jp.items():
        if k not in ja_names:
            ja_names[k] = v

    print(f"Total Japanese names available: {len(ja_names)}")

    # 2. Re-parse CYP from metabolism
    cyp_map = fetch_kegg_metabolism()

    # 3. Extract English trade names (already in names_alt)
    brand_map = extract_trade_names_from_kegg()

    # 4. Load and patch graph-light.json
    with open(GRAPH_LIGHT, 'r') as f:
        graph = json.load(f)

    drug_nodes = {n['id']: n for n in graph['nodes'] if n['type'] == 'drug'}
    existing_edges = {(e['source'], e['target'], e['type']) for e in graph['edges']}
    cyp_node_ids = {n['id'] for n in graph['nodes'] if n['type'] == 'cyp'}

    stats = {'name_ja_updated': 0, 'name_ja_new': 0,
             'cyp_updated': 0, 'brand_added': 0}

    # 4a. Update name_ja
    for kegg_id, node in drug_nodes.items():
        if kegg_id in ja_names:
            new_ja = ja_names[kegg_id]
            current_ja = node.get('name_ja', '')

            if not current_ja:
                # No existing name_ja → set it
                node['name_ja'] = new_ja
                stats['name_ja_new'] += 1
            elif current_ja != new_ja:
                # Has name_ja but KEGG has a different one
                # Keep the existing one if it looks like a valid katakana name
                # But add the KEGG one as an alternative search term
                if new_ja not in node.get('names_alt', []):
                    if 'names_alt' not in node:
                        node['names_alt'] = []
                    node['names_alt'].append(new_ja)
                    stats['name_ja_updated'] += 1

    # 4b. Update CYP enzymes (only add, don't remove)
    for kegg_id, cyps in cyp_map.items():
        if kegg_id not in drug_nodes:
            continue
        node = drug_nodes[kegg_id]
        existing_cyps = set(node.get('cyp_enzymes', []))
        new_cyps = set(cyps) - existing_cyps
        if new_cyps:
            node['cyp_enzymes'] = sorted(existing_cyps | new_cyps)
            stats['cyp_updated'] += 1

            # Add CYP edges
            for cyp in new_cyps:
                cyp_id = f"cyp_{cyp}"
                if cyp_id not in cyp_node_ids:
                    graph['nodes'].append({'id': cyp_id, 'type': 'cyp', 'name_ja': cyp, 'name_en': cyp})
                    cyp_node_ids.add(cyp_id)
                edge_key = (kegg_id, cyp_id, 'metabolized_by')
                if edge_key not in existing_edges:
                    graph['edges'].append({'source': kegg_id, 'target': cyp_id, 'type': 'metabolized_by'})
                    existing_edges.add(edge_key)

    # Save
    with open(GRAPH_LIGHT, 'w') as f:
        json.dump(graph, f, ensure_ascii=False, separators=(',', ':'))

    # Final stats
    drugs_final = [n for n in graph['nodes'] if n['type'] == 'drug']
    has_ja = sum(1 for n in drugs_final if n.get('name_ja'))
    has_cyp = sum(1 for n in drugs_final if n.get('cyp_enzymes'))

    print(f"\n=== Results ===")
    print(f"name_ja: new={stats['name_ja_new']}, alt_added={stats['name_ja_updated']} → {has_ja}/{len(drugs_final)} ({100*has_ja/len(drugs_final):.1f}%)")
    print(f"CYP: updated={stats['cyp_updated']} → {has_cyp}/{len(drugs_final)} ({100*has_cyp/len(drugs_final):.1f}%)")
    print(f"Total: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")


if __name__ == '__main__':
    main()
