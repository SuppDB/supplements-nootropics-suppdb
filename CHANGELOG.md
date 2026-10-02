# Changelog

All notable changes to the SuppDB dataset snapshots.

> Counts are stated as **minimums** (e.g. `17,000+`). The dataset is refreshed on a
> recurring schedule, so the live figures only grow — the numbers below stay
> accurate between snapshots.

## Site update — 2026-10-02

- **Kaggle starter notebook prints the file name, not the full path**: Kaggle now mounts an attached dataset under a path that includes the owner's account name, and the notebook's first cell printed that whole path. It now prints only the sample's file name (`Loaded: suppdb_sample.csv`). That one line of `kaggle/notebook/suppdb-starter-notebook.ipynb` changed, and the notebook was re-run on Kaggle (version 7) (2026-10-02).

## Site update — 2026-10-01

- **Sitemap dates follow page content**: `scripts/seo_common.py` (shared by the DataEngineered sites) dates each sitemap entry by the last commit that changed the page itself. It compares pages without line-ending differences and without the markup the translation build owns (language alternates and the header and footer language menus), and skips commits that only moved that markup, so regenerating an unchanged page keeps its date instead of taking the day of the run. No page or sitemap change in this update (2026-10-01).

## Site update — 2026-09-29

- **Kaggle metadata file**: `kaggle/dataset/dataset-metadata.json` now carries the live Kaggle subtitle, description (with the Safety layer section), keyword order, sources list and update frequency. Its column list follows the actual CSV: the three Safety-layer teaser columns (`product_max_pct_ul`, `product_over_ul_flag`, `product_interaction_count`) and `interactions_sample.csv` are now described (2026-09-29).
- **Site name**: the licence attribution, the Kaggle dataset description and starter notebook, and `assets/README.md` now name `suppdb.dataengineered.io` instead of `suppdb.net`. No page or data change (2026-09-29).
- **Security policy link**: `SECURITY.md` showed the site link as `suppdb.net`; it now shows `suppdb.dataengineered.io`, the address the link already pointed to (2026-09-29).
- **Visit counts**: Cloudflare Web Analytics adds its cookie-free page-view beacon to every page. The beacon loaded, but the Content-Security-Policy in `_headers` did not list the address it reports to, so browsers blocked every report and no visits were counted since Web Analytics was switched on (2026-09-05). `connect-src` now also allows `https://cloudflareinsights.com`. No other source is added.
- **Safety layer description names all its automated sources**: the homepage (English + 4 languages) and README now say the hand-verified core is joined by entries auto-extracted from FDA drug labels **and NIH ODS fact sheets**. The current Safety download (Snapshot 2026.09) holds 1,326 fact-sheet rows that the description did not mention. The README no longer says every interaction names a mechanism: the hand-verified core does, the automated rows leave it empty. In the 2026.09 download the fact-sheet rows share the `clinical` evidence grade with the hand-verified core, so filter on a non-empty `mechanism` to get the hand-verified set there. No figure changed (2026-09-29).

## Site update — 2026-09-28

- **Chart titles on `/stats/`**: every chart's built-in title and description (what a screen reader announces for the chart) used the same two ids, `t` and `d`, repeated once per chart, so the page had duplicate ids and every chart was announced with the first chart's title. The ids now carry the chart's name (`t-top-ingredients` / `d-top-ingredients`, and so on) on the page and in the downloadable SVGs under `/stats/charts/`. `scripts/stats_common.py` is the current portfolio copy, which writes them on the next regeneration; the committed page and SVGs were patched to exactly what it writes, without regenerating (no figure, date or `data.json` changes).
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

Full dataset & updates: [suppdb.dataengineered.io](https://suppdb.dataengineered.io)
