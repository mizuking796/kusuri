#!/usr/bin/env python3
"""
Step 2: 薬物間相互作用（DDI）データの収集
initial_drugs.json の各薬についてKEGG REST APIからDDIを取得
"""

import json
import time
import requests
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
KEGG_BASE = "https://rest.kegg.jp"
RATE_LIMIT = 0.35  # 3 requests/sec max


def fetch_ddi(kegg_id: str) -> list[dict]:
    """1薬のDDI（相互作用）を全て取得"""
    time.sleep(RATE_LIMIT)
    url = f"{KEGG_BASE}/ddi/{kegg_id}"
    r = requests.get(url)
    if r.status_code != 200 or not r.text.strip():
        return []

    interactions = []
    for line in r.text.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) >= 3:
            drug1 = parts[0].replace('dr:', '')
            drug2 = parts[1].replace('dr:', '')
            severity = parts[2]  # CI = Contraindication, P = Precaution
            mechanism = parts[3] if len(parts) > 3 else ''
            interactions.append({
                'drug1': drug1,
                'drug2': drug2,
                'severity': severity,  # CI or P
                'mechanism': mechanism,
            })
    return interactions


def main():
    # Load initial drug list
    drugs_file = DATA_DIR / "initial_drugs.json"
    if not drugs_file.exists():
        print("ERROR: initial_drugs.json not found. Run 01_build_drug_list.py first.")
        return

    with open(drugs_file) as f:
        drugs = json.load(f)

    drug_ids = {d['kegg_id'] for d in drugs}
    drug_names = {d['kegg_id']: d.get('search_name', d.get('name_en', '')) for d in drugs}

    print(f"=== Fetching DDI for {len(drug_ids)} drugs ===\n")

    all_interactions = []
    internal_interactions = []  # Both drugs in our list
    stats = {'total': 0, 'CI': 0, 'P': 0, 'CI,P': 0, 'internal_CI': 0, 'internal_P': 0, 'internal_CI,P': 0}

    for i, drug in enumerate(drugs):
        kegg_id = drug['kegg_id']
        name = drug.get('search_name', drug.get('name_en', kegg_id))
        print(f"[{i+1}/{len(drugs)}] DDI for {kegg_id} ({name})...", end=' ')

        interactions = fetch_ddi(kegg_id)
        print(f"{len(interactions)} interactions")

        for ix in interactions:
            stats['total'] += 1
            sev = ix['severity']
            if sev not in stats:
                stats[sev] = 0
            stats[sev] += 1
            all_interactions.append(ix)

            # Normalize severity: CI,P → CI (take the more severe)
            if ',' in ix['severity']:
                ix['severity'] = 'CI' if 'CI' in ix['severity'] else ix['severity'].split(',')[0]

            # Check if both drugs are in our initial list
            partner = ix['drug2'] if ix['drug1'] == kegg_id else ix['drug1']
            if partner in drug_ids:
                internal_interactions.append(ix)
                int_key = f"internal_{ix['severity']}"
                if int_key not in stats:
                    stats[int_key] = 0
                stats[int_key] += 1

    # Deduplicate internal interactions (A-B and B-A)
    seen = set()
    unique_internal = []
    for ix in internal_interactions:
        pair = tuple(sorted([ix['drug1'], ix['drug2']]))
        key = (pair[0], pair[1], ix['severity'])
        if key not in seen:
            seen.add(key)
            unique_internal.append(ix)

    # Deduplicate all interactions
    seen_all = set()
    unique_all = []
    for ix in all_interactions:
        pair = tuple(sorted([ix['drug1'], ix['drug2']]))
        key = (pair[0], pair[1], ix['severity'])
        if key not in seen_all:
            seen_all.add(key)
            unique_all.append(ix)

    # Enrich with drug names
    for ix in unique_internal:
        ix['drug1_name'] = drug_names.get(ix['drug1'], ix['drug1'])
        ix['drug2_name'] = drug_names.get(ix['drug2'], ix['drug2'])

    # Save
    output_all = DATA_DIR / "ddi_all.json"
    output_internal = DATA_DIR / "ddi_internal.json"

    with open(output_all, "w", encoding='utf-8') as f:
        json.dump(unique_all, f, ensure_ascii=False, indent=2)

    with open(output_internal, "w", encoding='utf-8') as f:
        json.dump(unique_internal, f, ensure_ascii=False, indent=2)

    print(f"\n=== Summary ===")
    print(f"Total raw interactions: {stats['total']}")
    print(f"  CI (contraindication): {stats['CI']}")
    print(f"  P  (precaution):       {stats['P']}")
    print(f"Unique interactions (all): {len(unique_all)}")
    print(f"Internal (both in our list): {len(unique_internal)}")
    print(f"  CI: {stats['internal_CI']//2}")
    print(f"  P:  {stats['internal_P']//2}")
    print(f"\nSaved: {output_all}")
    print(f"Saved: {output_internal}")


if __name__ == '__main__':
    main()
