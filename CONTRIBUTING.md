# Contributing to SuppDB

Thanks for your interest! This repository is the **public showcase** for the
SuppDB supplements & nootropics dataset — it holds a free sample, documentation,
and a starter notebook. The data pipeline itself is not open source, so
contributions here focus on **data quality, docs, and examples**.

## Ways to help

### 🐛 Report a data issue
Spotted a wrong dosage, ingredient, form, or blend flag in the sample? Open an
issue with:
- the `product_id` and `brand`,
- what's wrong and what it should be,
- ideally the `source_url` (the NIH DSLD label) so we can re-verify.

### ✏️ Improve docs or examples
Typos, clearer explanations, or a better `examples/load_sample.py` / notebook
are welcome via pull request.

### 💡 Request a field or feature
Want a column the dataset doesn't have yet, or a specific set of brands /
ingredient categories? Open an issue describing the use case — it helps
prioritize snapshots and informs custom builds.

## Brands / manufacturers: correction or removal requests

If you represent a brand and want a record corrected or removed, please email
**suppdb.doorframe589@simplelogin.com** (or open an issue). Note that the underlying records come
from the public NIH DSLD label database.

## Pull request guidelines

- Keep PRs focused and describe the *why*.
- Docs/examples only — please don't add ingestion/pipeline code here.
- Data changes to the sample should preserve the schema in
  [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

## Licensing of contributions

By contributing, you agree that your contributions to the sample and docs are
licensed under **CC-BY-NC-4.0**, the same license as this repository (see
[`LICENSE`](LICENSE)).

Questions? **suppdb.doorframe589@simplelogin.com** · full dataset: [suppdb.net](https://supplements-nootropics-suppdb.pages.dev)
