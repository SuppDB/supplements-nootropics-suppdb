# Site page generation (maintainers)

## Regenerating the English pages

The product and ingredient pages (`products/*.html`, `ingredients/*.html`) are generated
from `samples/suppdb_sample.csv`; the directory hubs (`products/index.html`,
`ingredients/index.html`, the letter-range hubs), the homepage link block and
`sitemap.xml` are written by `generate_hubs.py`, which must run second:

```bash
python scripts/generate_seo_pages.py
python scripts/generate_hubs.py
```

`seo_common.git_lastmod` shells out to `git`, so `git` must be on PATH.

## Localized pages (i18n)

English at the site root is the source of truth. `/es/`, `/de/`, `/fr/` and `/pt-br/`
are generated copies; never edit them by hand. `scripts/i18n_common.py` is a
byte-identical copy of the portfolio tool (do not modify it here: segment ids depend on
it). Configuration is in `i18n.config.json`, translations in `locales/<lang>.json`,
kept-verbatim terms in `locales/glossary.json`.

After regenerating or editing any English page (including `index.html`, `404.html` and
the `#i18n-strings` table its scripts read their UI text from):

```bash
python scripts/i18n_common.py build
python scripts/i18n_common.py check      # must report 0 errors
```

`build` rewrites every locale page, the hreflang blocks and language switcher on the
English pages, and `sitemap.xml` (with every locale URL), so always run it after
`generate_hubs.py`. A page whose copy is not fully translated is simply not published in
that language (the build output lists them).

When copy is new or changed:

1. `python scripts/i18n_common.py extract`, then `python scripts/i18n_common.py todo --lang <lang>`
   for each of es, de, fr, pt-br (writes `locales/_work/todo/`, which is gitignored).
2. Translate following the portfolio style guide `scripts/i18n_style.md`. Data values
   (product, brand and ingredient names, forms, formulas, InChIKeys) belong in
   `translate="no"` markup in the generators, not in the catalogs.
3. `python scripts/i18n_common.py merge --lang <lang> --prune <done-file>.json`
   (`--prune` drops catalog entries whose English source no longer exists).
4. `build`, then `check`.

After a content refresh goes live, re-submit IndexNow deliberately
(`node scripts/indexnow-submit.mjs suppdb` from the portfolio root).
