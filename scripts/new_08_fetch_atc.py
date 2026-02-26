#!/usr/bin/env python3
"""
new_08_fetch_atc.py
Wikidata SPARQL から DrugBank ID → ATC コードを一括取得。

出力:
  data/wikidata_atc.json — { "DB00001": ["B01AE02"], ... }
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
OUTPUT = DATA_DIR / "wikidata_atc.json"

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

QUERY = """
SELECT ?drugbankId ?atc WHERE {
  ?item wdt:P715 ?drugbankId .
  ?item wdt:P267 ?atc .
}
"""


def fetch_wikidata_atc() -> dict:
    """Wikidata SPARQL で DrugBank ID → ATC コードを一括取得"""
    print("Wikidata SPARQL クエリ実行中...")

    params = urllib.parse.urlencode({
        "query": QUERY.strip(),
        "format": "json",
    })
    url = f"{SPARQL_ENDPOINT}?{params}"

    req = urllib.request.Request(url)
    req.add_header("User-Agent", "KusuriGraph/1.0 (drug interaction graph builder)")
    req.add_header("Accept", "application/sparql-results+json")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 10
                print(f"  リトライ {attempt+1}/{max_retries} ({e})... {wait}秒待機")
                time.sleep(wait)
            else:
                raise

    results = data.get("results", {}).get("bindings", [])
    print(f"  取得件数: {len(results)} マッピング")

    # DrugBank ID → ATC コードリスト
    db_to_atc = {}
    for r in results:
        db_id = r["drugbankId"]["value"]
        atc = r["atc"]["value"]
        db_to_atc.setdefault(db_id, [])
        if atc not in db_to_atc[db_id]:
            db_to_atc[db_id].append(atc)

    print(f"  ユニーク DrugBank ID: {len(db_to_atc)}")
    total_atc = sum(len(v) for v in db_to_atc.values())
    print(f"  合計 ATC コード: {total_atc}")

    return db_to_atc


def main():
    print("=== Wikidata DrugBank→ATC 取得 ===\n")

    # キャッシュがあればスキップ（強制再取得は --force で）
    import sys
    if OUTPUT.exists() and "--force" not in sys.argv:
        with open(OUTPUT) as f:
            cached = json.load(f)
        print(f"キャッシュあり: {OUTPUT.name} ({len(cached)} entries)")
        print("再取得するには --force を指定してください")
        return

    db_to_atc = fetch_wikidata_atc()

    # 保存
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(db_to_atc, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"\n保存: {OUTPUT} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
