# Changelog

All notable changes to the SuppDB dataset snapshots.

> Counts are stated as **minimums** (e.g. `17,000+`). The dataset is refreshed on a
> recurring schedule, so the live figures only grow — the numbers below stay
> accurate between snapshots.

## 2026.07 — 2026-07-06

- Initial public snapshot.
- **17,000+** real supplement & nootropic products from **2,000+** brands.
- **115,000+** active-ingredient records, every dose **normalized to milligrams** (substance-specific IU handling).
- **40,000+** proprietary-blend ingredient flags (undisclosed per-serving dose).
- **NIH PubChem chemistry** on 4,000+ compounds: CID, molecular formula, molecular weight, canonical SMILES, InChIKey (+ InChIKey canonicalization of name variants).
- **NIH DRI reference intakes** (RDA / upper limit) where an official value exists; NULL otherwise.
- Built exclusively from public-domain **NIH DSLD** labels; per-record provenance via `dsld_label_id`, `source_url`, `dataset_version`.

Full dataset & updates: [suppdb.net](https://supplements-nootropics-suppdb.pages.dev)
