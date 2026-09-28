# Changelog

All notable changes to the SuppDB dataset snapshots.

> Counts are stated as **minimums** (e.g. `17,000+`). The dataset is refreshed on a
> recurring schedule, so the live figures only grow — the numbers below stay
> accurate between snapshots.

## Site update — 2026-09-29

- **Visit counts**: Cloudflare Web Analytics adds its cookie-free page-view beacon to every page. The beacon loaded, but the Content-Security-Policy in `_headers` did not list the address it reports to, so browsers blocked every report and no visits were counted since Web Analytics was switched on (2026-09-05). `connect-src` now also allows `https://cloudflareinsights.com`. No other source is added.
- **Safety layer description names all its automated sources**: the homepage (English + 4 languages) and README now say the hand-verified core is joined by entries auto-extracted from FDA drug labels **and NIH ODS fact sheets**. The current Safety download (Snapshot 2026.09) holds 1,326 fact-sheet rows that the description did not mention. The README no longer says every interaction names a mechanism: the hand-verified core does, the automated rows leave it empty. In the 2026.09 download the fact-sheet rows share the `clinical` evidence grade with the hand-verified core, so filter on a non-empty `mechanism` to get the hand-verified set there. No figure changed (2026-09-29).

## Site update — 2026-09-28

- **Repository files off the website**: the translation catalogs (`/locales/`), the build scripts (`/scripts/`), `i18n.config.json`, `README.md`, `vercel.json` and the dotfiles belong to this repository, not to the website, but the site served them as plain files. They now answer the site's normal 404 page (also when requested as `/locales%2Fes.json` or `//locales/es.json`) and stay available here on GitHub. Pages, data files, samples, `llms.txt` and the sitemap are unchanged (2026-09-28).
- **Safety layer claim corrected to 8,300+ interactions (was 8,800+)** on the homepage (English + 4 languages), README and `llms.txt`. The Safety download buyers receive (Snapshot 2026.09, built 2026-09-20) holds 8,364 interaction rows: 2,678 hand-verified, 4,360 cited from FDA (DailyMed) drug labels and 1,326 extracted from NIH ODS fact sheets. 2026.08 held 8,827; 2026.09 drew its label-cited rows from 300 FDA drug labels instead of 500. The 7,038 rows in the 2026.09 entry below describe the 2026-09-18 build; the Safety download comes from the 2026-09-20 rebuild. No other figure changed (2026-09-28).

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
