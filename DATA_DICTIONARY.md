# SuppDB — Data Dictionary

Field reference for the SuppDB supplements & nootropics dataset (snapshot `2026.07`).
The free sample (`samples/suppdb_sample.csv`) is a **flat, one-row-per-active-ingredient**
table using the columns below. The full dataset ships the same fields in CSV and JSON,
plus a relational SQLite build.

## Columns

| Column | Type | Description | Coverage* |
| :--- | :--- | :--- | ---: |
| `product_id` | integer | SuppDB product identifier (stable within a snapshot) | 100% |
| `brand` | string | Brand / manufacturer as printed on the label | 100% |
| `product_name` | string | Product name as listed on the NIH DSLD label | 100% |
| `upc_barcode` | string | UPC / GTIN barcode; a `DSLD-<id>` placeholder is used where the label has no barcode | 86%† |
| `form_type` | string | Physical form: `Capsule` · `Tablet` · `Powder` · `Softgel` · `Liquid` · … | 100% |
| `serving_size_count` | number | Units per serving (e.g. `2` capsules) | 100% |
| `serving_size_unit` | string | Unit of the serving (`capsule`, `softgel`, `scoop`, …) | 100% |
| `servings_per_container` | integer | Servings per container, from the label where stated | 85% |
| `ingredient` | string | Canonical ingredient name (DSLD ingredient group), e.g. `Magnesium` | 100% |
| `ingredient_form` | string | Specific form as listed, e.g. `Magnesium Bisglycinate` | 100% |
| `ingredient_category` | string | DSLD category: `mineral` · `vitamin` · `botanical` · `amino acid` · … | 100% |
| `amount_per_serving_mg` | number | Dose per serving **normalized to milligrams** | 100%‡ |
| `is_proprietary_blend` | 0/1 | `1` = per-ingredient dose is undisclosed on the label (dose hidden in a blend) | 100% (37% are `1`) |
| `recommended_daily_mg` | number | NIH DRI recommended daily intake (mg); NULL where none is established | ~9% |
| `upper_safety_limit_mg` | number | NIH DRI Tolerable Upper Intake Level (mg); NULL where none is established | ~7% |
| `pubchem_cid` | integer | NIH PubChem Compound ID; NULL for botanicals / multi-component blends | ~25% |
| `molecular_formula` | string | PubChem molecular formula, e.g. `C8H10N4O2` | ~25% |
| `molecular_weight` | number | PubChem molecular weight (g/mol) | ~25% |
| `canonical_smiles` | string | PubChem canonical SMILES structure string | ~25% |
| `inchikey` | string | PubChem InChIKey — a canonical chemical key (same molecule → same key) | ~25% |
| `dsld_label_id` | string | NIH DSLD label identifier (provenance) | 100% |
| `source_url` | string | Exact NIH DSLD label URL the record was extracted from | 100% |
| `dataset_version` | string | Snapshot id, e.g. `2026.07` | 100% |

\* Share of the full dataset (17,000+ products / 115,000+ ingredient rows) with a non-empty value.
† `upc_barcode` is present on 100% of rows; 86% are real barcodes, the rest use a `DSLD-<id>` placeholder for labels with no printed UPC.
‡ `amount_per_serving_mg` is `0` where the ingredient sits inside a **proprietary blend** (dose undisclosed); flagged by `is_proprietary_blend = 1`.

## Notes

- **Coverage is honest and uneven.** Reference intakes (RDA/UL) exist only for vitamins/minerals with an official NIH DRI; chemistry (CID/formula/SMILES/InChIKey) exists only for compounds PubChem resolves to a single molecule. Botanicals and blends are legitimately NULL — never invented.
- **Unit normalization.** All doses are converted to milligrams: `mcg`, `g`, and **substance-specific `IU`** (e.g. Vitamin D 1,000 IU → 0.025 mg; Vitamin E natural 1 IU → 0.67 mg) — not a single wrong flat factor.
- **Canonicalization.** Rows sharing an `inchikey` are the **same molecule** under different label names (e.g. `Vitamin C` and `Ascorbic Acid` → `CIWBSHSKHKDKBQ-JLAZNSOCSA-N`). Group on `inchikey` to canonicalize deterministically.
- **No price.** DSLD labels do not carry a retail price, so there is no price column — we don't fabricate one.
- **Provenance.** `source_url` + `dsld_label_id` let you trace and re-verify any record against the original NIH DSLD label.
- **Relational build (full dataset).** The SQLite export normalizes into `supplement_brands`, `supplement_products`, `active_compounds`, `product_compounds`, `compound_synonyms`, and `data_sources`.

Sources: **NIH DSLD** (labels) + **NIH PubChem** (chemistry) — U.S. Government public domain.
Full dataset: **[suppdb.net](https://supplements-nootropics-suppdb.pages.dev)** · Questions: **[suppdb.doorframe589@simplelogin.com](mailto:suppdb.doorframe589@simplelogin.com)**
