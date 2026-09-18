# Changelog

All notable changes to the SuppDB dataset snapshots.

> Counts are stated as **minimums** (e.g. `17,000+`). The dataset is refreshed on a
> recurring schedule, so the live figures only grow — the numbers below stay
> accurate between snapshots.

## 2026.09 — 2026-09-18

- Manifest grown to 26,500 NIH DSLD labels (25,631 ingested; 841 skipped for having no active ingredients, 28 refused for an unknown IU→mg factor); **18,000+** products from **2,200+** brands after de-duplication.
- **144,000+** active-ingredient records, **86,000+** compound name variants, **17,000+** compounds.
- Safety layer rebuilt: 8,575 products scored against NIH DRI upper limits (1,434 over a limit), 7,038 interaction rows, 956 contraindications, 45 WADA compound flags.
- `/stats/` regenerated from this snapshot (retrieved 2026-09-18).

## 2026.07 — 2026-07-06

- Initial public snapshot.
- **17,000+** real supplement & nootropic products from **2,000+** brands.
- **115,000+** active-ingredient records, every dose **normalized to milligrams** (substance-specific IU handling).
- **40,000+** proprietary-blend ingredient flags (undisclosed per-serving dose).
- **NIH PubChem chemistry** on 4,000+ compounds: CID, molecular formula, molecular weight, canonical SMILES, InChIKey (+ InChIKey canonicalization of name variants).
- **NIH DRI reference intakes** (RDA / upper limit) where an official value exists; NULL otherwise.
- Built exclusively from public-domain **NIH DSLD** labels; per-record provenance via `dsld_label_id`, `source_url`, `dataset_version`.

Full dataset & updates: [suppdb.net](https://suppdb.dataengineered.io)
