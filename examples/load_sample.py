"""Load the SuppDB free sample and print a quick summary.

    python examples/load_sample.py

The sample is one row per (product x active ingredient). No dependencies beyond
the Python standard library.
Full dataset: https://supplements-nootropics-suppdb.pages.dev
"""

import csv
import os
from collections import Counter

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "samples", "suppdb_sample.csv")


def main() -> None:
    with open(SAMPLE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    products = {r["product_id"] for r in rows}
    brands = {r["brand"] for r in rows}
    print(f"{len(rows)} ingredient records across {len(products)} products from {len(brands)} brands\n")

    print("Top ingredient categories:")
    for cat, n in Counter(r["ingredient_category"] for r in rows if r["ingredient_category"]).most_common(6):
        print(f"  {cat:16} {n}")

    print("\nTop ingredients:")
    for ing, n in Counter(r["ingredient"] for r in rows).most_common(6):
        print(f"  {ing:24} {n}")

    blend = sum(1 for r in rows if r["is_proprietary_blend"] == "1")
    with_chem = sum(1 for r in rows if r["pubchem_cid"])
    print(f"\nProprietary-blend (dose undisclosed) rows: {blend} / {len(rows)}")
    print(f"Rows with PubChem chemical identity:       {with_chem} / {len(rows)}")

    print("\nExample — a disclosed dose with chemistry + provenance:")
    r = next(x for x in rows if x["amount_per_serving_mg"] not in ("", "0") and x["inchikey"])
    print(f"  {r['brand']} — {r['product_name']}")
    print(f"    {r['ingredient']} ({r['ingredient_form']}): {r['amount_per_serving_mg']} mg")
    print(f"    chem  : CID {r['pubchem_cid']} · {r['molecular_formula']} · InChIKey {r['inchikey']}")
    print(f"    source: {r['source_url']}")


if __name__ == "__main__":
    main()
