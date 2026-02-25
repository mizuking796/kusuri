#!/usr/bin/env python3
"""
06_add_brand_names.py
カタカナ商品名を graph.json / graph-light.json の names_alt に追加するパッチスクリプト。
冪等: 何度実行しても同じ結果になる。
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
BRAND_FILE = DATA_DIR / "brand_names_ja.json"
GRAPH_FILES = [
    DATA_DIR / "graph" / "graph.json",
    DATA_DIR / "graph" / "graph-light.json",
]


def main():
    # ブランド名マッピング読み込み
    with open(BRAND_FILE, encoding="utf-8") as f:
        brand_map: dict[str, list[str]] = json.load(f)

    print(f"ブランド名マッピング: {len(brand_map)} 薬品, "
          f"{sum(len(v) for v in brand_map.values())} 商品名")

    for graph_path in GRAPH_FILES:
        if not graph_path.exists():
            print(f"SKIP: {graph_path} not found")
            continue

        with open(graph_path, encoding="utf-8") as f:
            graph = json.load(f)

        added_count = 0
        skipped_count = 0

        for node in graph["nodes"]:
            if node.get("type") != "drug":
                continue
            kegg_id = node["id"]
            if kegg_id not in brand_map:
                continue

            names_alt = node.get("names_alt", [])
            existing_lower = {n.lower() for n in names_alt}

            for brand_name in brand_map[kegg_id]:
                if brand_name.lower() not in existing_lower:
                    names_alt.append(brand_name)
                    added_count += 1
                else:
                    skipped_count += 1

            node["names_alt"] = names_alt

        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, ensure_ascii=False)

        print(f"{graph_path.name}: +{added_count} 追加, {skipped_count} 重複スキップ")

    print("完了")


if __name__ == "__main__":
    main()
