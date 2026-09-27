# Changelog

All notable changes to the SuppDB dataset snapshots.

> Counts are stated as **minimums** (e.g. `17,000+`). The dataset is refreshed on a
> recurring schedule, so the live figures only grow — the numbers below stay
> accurate between snapshots.

## Site update — 2026-09-28

- **Chart titles on `/stats/`**: every chart's built-in title and description (what a screen reader announces for the chart) used the same two ids, `t` and `d`, repeated once per chart, so the page had duplicate ids and every chart was announced with the first chart's title. The ids now carry the chart's name (`t-top-ingredients` / `d-top-ingredients`, and so on) on the page and in the downloadable SVGs under `/stats/charts/`. `scripts/stats_common.py` is the current portfolio copy, which writes them on the next regeneration; the committed page and SVGs were patched to exactly what it writes, without regenerating (no figure, date or `data.json` changes).

## Site update — 2026-09-27

- **Translated Dataset markup**: on the Spanish, German, French and Portuguese pages the Dataset structured data now names its English original in `sameAs` (next to any existing `sameAs` links), so dataset search can tie the language copies to one canonical entry. English pages and all visible text are unchanged (2026-09-27).
- **Section links**: the homepage (English + 4 languages) and the `/stats/` pages carry the shared portfolio section-links snippet (`scripts/section_links.py`). It sets `scroll-padding-top` to the sticky header's live height, so `#metrics`, `#explorer`, `#pricing` and the other sections are no longer hidden under the header on arrival (desktop and phones). On a fresh navigation it also lands the visitor on the section again after the web fonts swap in. The "Embed this chart" snippets on `/stats/` now link each chart's own anchor `#fig-<slug>`. Before, 8 of the 9 charts' `#<slug>` matched no element, and `#forms` hit the section rather than the chart. `scripts/stats_common.py` was re-copied from the portfolio, which added `scripts/section_links.py`; the stats page was patched in place, not regenerated, so no figures or dates changed. Visible text is unchanged (2026-09-27).

## Site update — 2026-09-20

- **Sale attribution**: every Stripe buy link carries `?client_reference_id=<brand>_<lang>_<surface>` (`home` / `landing`); the i18n build swaps the language token per locale and the delivery worker prints the id in the order email. Stripe does not store UTM parameters, so this is the only per-page attribution that reaches the order record (2026-09-20).

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
