#!/usr/bin/env python3
"""
SuppDB statistics page generator (`SuppDB-public`).

Reads the FULL private snapshot (the private pipeline's enterprise_release/suppdb_master.sqlite,
never the public sample) and writes a citable, embeddable statistics page:

    stats/index.html          the page (URL /stats/)
    stats/charts/<slug>.svg   one standalone SVG per chart (for <img> embeds elsewhere)
    stats/data.json           every figure on the page, machine-readable

Only aggregates leave the private database -- no row-level data is written. Every figure
states its denominator; label facts come from the NIH Dietary Supplement Label Database
(public domain), reference intakes from the NIH Office of Dietary Supplements.

Re-run after each local refresh, then `python scripts/generate_hubs.py` (sitemap),
`python scripts/i18n_common.py build` and `... check`.

Usage:
    python scripts/generate_stats.py                 # ../../03_Supplements_Nootropics_SuppDB/enterprise_release/suppdb_master.sqlite
    python scripts/generate_stats.py --db PATH       # or SUPPDB_SQLITE=PATH
"""
import argparse
import datetime as dt
import os
import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_common import (Site, esc, n, pct, data, svg_hbar, figure, table, section, toc, tiles,
                          article_ld, COPY_JS, STATS_CSS, write_outputs)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "stats"
FIRST_PUBLISHED = "2026-09-18"
DEFAULT_DB = BASE_DIR.parent / "03_Supplements_Nootropics_SuppDB" / "enterprise_release" / "suppdb_master.sqlite"

SITE = Site(base_url="https://suppdb.dataengineered.io", brand="SuppDB",
            snippet_label="SuppDB supplement statistics",
            surface="#0b0e0f", surface2="#121618", ink="#eef1f2", muted="#97a1a3", grid="#22282b", accent="#2fd4a3",
            font="'Outfit', 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
            mono="'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace", heading_class="font-display")

COUNT_BUCKETS = [("1", 1, 1), ("2 to 3", 2, 3), ("4 to 6", 4, 6), ("7 to 10", 7, 10), ("11 to 20", 11, 20), ("21 or more", 21, 10 ** 6)]


def compute(db_path):
    con = sqlite3.connect(str(db_path))
    q = lambda sql, *a: con.execute(sql, a).fetchall()
    s = {}
    s["snapshot_date"] = q("select max(date(retrieved_at)) from data_sources")[0][0]
    P = q("select count(*) from supplement_products")[0][0]
    s["products"] = P
    s["brands"] = q("select count(distinct brand_id) from supplement_products")[0][0]
    s["rows"] = q("select count(*) from product_compounds")[0][0]
    s["compounds"] = q("select count(distinct compound_id) from product_compounds")[0][0]

    top = q("select a.canonical_name, count(distinct pc.product_id) from product_compounds pc join active_compounds a using(compound_id) "
            "group by 1 order by 2 desc limit 20")
    s["top_compounds"] = [(nm, c, pct(c, P)) for nm, c in top]
    cats = q("select a.category, count(distinct pc.product_id) from product_compounds pc join active_compounds a using(compound_id) "
             "where a.category is not null group by 1 order by 2 desc limit 12")
    s["categories"] = [(c.capitalize() if c != "non-nutrient/non-botanical" else "Non-nutrient, non-botanical", v, pct(v, P)) for c, v in cats]

    # proprietary blends and undisclosed amounts
    s["blend_products"] = q("select count(distinct product_id) from product_compounds where is_proprietary_blend = 1")[0][0]
    s["blend_products_pct"] = pct(s["blend_products"], P)
    s["blend_rows"] = q("select count(*) from product_compounds where is_proprietary_blend = 1")[0][0]
    s["blend_rows_pct"] = pct(s["blend_rows"], s["rows"])
    s["no_amount_rows"] = q("select count(*) from product_compounds where amount_per_serving_mg is null or amount_per_serving_mg <= 0")[0][0]
    s["no_amount_pct"] = pct(s["no_amount_rows"], s["rows"])
    bf = q("select p.form_type, count(*), sum(p.product_id in (select product_id from product_compounds where is_proprietary_blend = 1)) "
           "from supplement_products p where p.form_type is not null and p.form_type <> 'Unknown' group by 1 having count(*) >= 100")
    s["blend_by_form"] = sorted([(f, c, b, pct(b, c)) for f, c, b in bf], key=lambda t: -t[3])

    # forms
    forms = q("select coalesce(form_type, 'Unknown'), count(*) from supplement_products group by 1 order by 2 desc")
    s["forms"] = [(f, c, pct(c, P)) for f, c in forms]

    # doses vs reference intakes (NIH ODS adult values stored per compound)
    rda = q("select a.canonical_name, count(*) nn, sum(pc.amount_per_serving_mg > a.recommended_daily_mg), a.recommended_daily_mg "
            "from product_compounds pc join active_compounds a using(compound_id) "
            "where a.recommended_daily_mg is not null and pc.amount_per_serving_mg > 0 group by 1 having nn >= 200")
    s["above_rda"] = sorted([(nm, c, o, pct(o, c), r) for nm, c, o, r in rda], key=lambda t: -t[3])
    s["rda_rows"] = sum(c for _, c, *_ in s["above_rda"])
    ul = q("select a.canonical_name, count(*) nn, sum(pc.amount_per_serving_mg > a.upper_safety_limit_mg), a.upper_safety_limit_mg "
           "from product_compounds pc join active_compounds a using(compound_id) "
           "where a.upper_safety_limit_mg is not null and pc.amount_per_serving_mg > 0 group by 1 having nn >= 100")
    s["above_ul"] = sorted([(nm, c, o, pct(o, c), u) for nm, c, o, u in ul], key=lambda t: -t[3])

    # magnesium forms and caffeine
    mg = q("select a.specific_form, count(*) from product_compounds pc join active_compounds a using(compound_id) "
           "where a.canonical_name = 'Magnesium' group by 1 order by 2 desc limit 8")
    mg_total = q("select count(*) from product_compounds pc join active_compounds a using(compound_id) where a.canonical_name = 'Magnesium'")[0][0]
    s["magnesium_forms"] = [(f, c, pct(c, mg_total)) for f, c in mg]
    s["magnesium_rows"] = mg_total
    caf = [v for (v,) in q("select pc.amount_per_serving_mg from product_compounds pc join active_compounds a using(compound_id) "
                           "where a.canonical_name = 'Caffeine' and pc.amount_per_serving_mg > 0")]
    s["caffeine"] = dict(products=len(caf), mean=int(round(statistics.mean(caf))), median=int(statistics.median(caf)), max=int(max(caf)),
                         over_200=sum(1 for v in caf if v > 200))

    # compounds per product
    counts = [c for (c,) in q("select count(*) from product_compounds group by product_id")]
    s["cpp_mean"] = round(statistics.mean(counts), 1)
    s["cpp_median"] = int(statistics.median(counts))
    s["cpp_max"] = max(counts)
    s["cpp_buckets"] = [(lbl, sum(1 for c in counts if lo <= c <= hi), pct(sum(1 for c in counts if lo <= c <= hi), len(counts)))
                        for lbl, lo, hi in COUNT_BUCKETS]
    s["single_ingredient_pct"] = s["cpp_buckets"][0][2]

    # servings per container
    sv = [v for (v,) in q("select servings_per_container from supplement_products where servings_per_container > 0")]
    s["servings"] = dict(products=len(sv), median=int(statistics.median(sv)), p25=int(statistics.quantiles(sv, n=4)[0]), p75=int(statistics.quantiles(sv, n=4)[2]))

    # brands
    s["top_brands"] = [(b, c) for b, c in q("select b.name, count(*) from supplement_products p join supplement_brands b using(brand_id) group by 1 order by 2 desc limit 15")]

    # chemistry coverage
    s["pubchem_compounds"] = q("select count(*) from active_compounds where pubchem_cid is not null")[0][0]
    s["pubchem_rows"] = q("select count(*) from product_compounds pc join active_compounds a using(compound_id) where a.pubchem_cid is not null")[0][0]
    s["compounds_total"] = q("select count(*) from active_compounds")[0][0]
    con.close()
    return s


CSS = """
    :root { --bg-paper: #0b0e0f; --bg-paper-2: #121618; --text-ink: #eef1f2; --text-muted: #97a1a3;
            --rule-color: rgba(238, 241, 242, 0.18); --accent: #2fd4a3; --radius: 0; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body { background: var(--bg-paper); color: var(--text-ink); font-family: 'JetBrains Mono', monospace; line-height: 1.6; padding: 40px 20px; }
    .container { max-width: 1000px; margin: 0 auto; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .font-display { font-family: 'Outfit', sans-serif; }
    .header-bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; border-bottom: 1px solid var(--rule-color); padding-bottom: 20px; margin-bottom: 40px; }
    h1 { font-size: 2.2rem; line-height: 1.15; }
    h2 { font-size: 1.45rem; }
    h3 { font-size: 1rem; margin-top: 24px; }
    .lede { color: var(--text-muted); margin-top: 14px; font-size: 0.95rem; max-width: 72ch; }
    .tiles strong { font-family: 'Outfit', sans-serif; font-weight: 600; }
    .cta { margin-top: 60px; padding: 32px; background: var(--bg-paper-2); border: 1px solid var(--rule-color); text-align: center; }
    .btn { display: inline-block; background: var(--accent); color: #05110c; font-weight: bold; padding: 14px 28px; border-radius: 4px; margin-top: 16px; }
    .btn:hover { text-decoration: none; opacity: .92; }
    @media (max-width: 640px) { body { padding: 24px 16px; } h1 { font-size: 1.7rem; } }
"""


def build_page(s, charts):
    site = SITE
    snap = s["snapshot_date"]
    P = s["products"]
    src_note = f"Source: SuppDB, suppdb.dataengineered.io/stats · NIH DSLD labels · snapshot {snap} · CC BY 4.0"
    sections = []

    tc = s["top_compounds"]
    charts["top-ingredients"] = svg_hbar(site, "The most common supplement ingredients", f"Share of {n(P)} supplement labels listing the ingredient",
                                         [(nm, c, f"{p}%") for nm, c, p in tc[:15]], src_note, label_w=200)
    bot = next((nm, p) for nm, _, p in tc if nm not in ("Vitamin C", "Calcium", "Magnesium", "Vitamin D", "Zinc", "Sodium", "Vitamin B6", "Vitamin B12", "Potassium",
                                                          "Niacin", "Vitamin E", "Thiamin", "Riboflavin", "Biotin", "Chromium", "Manganese", "Selenium", "Copper", "Vitamin A", "Folate", "Iron"))
    sections.append(section(
        site, "ingredients", "The most common supplement ingredients",
        f"{data(tc[0][0])} is on <strong>{tc[0][2]}%</strong> of supplement labels, {data(tc[1][0])} on {tc[1][2]}% and {data(tc[2][0])} on {tc[2][2]}%. "
        f"The most common botanical is {data(bot[0])} at {bot[1]}%.",
        figure(site, "top-ingredients", charts["top-ingredients"], "The most common supplement ingredients", f"{n(P)} labels"),
        table(["Ingredient", "Products", "Share of products"], [(nm, n(c), f"{p}%") for nm, c, p in tc], {1, 2}),
        "Share of labels listing the ingredient as an active (Supplement Facts panel), counted once per product whatever the specific form; "
        "Vitamin D covers cholecalciferol and ergocalciferol, Magnesium every salt. Excipients and other ingredients are not counted."))

    ca = s["categories"]
    charts["categories"] = svg_hbar(site, "Ingredient types by share of products", f"Share of {n(P)} labels listing at least one ingredient of the type",
                                    [(c, v, f"{p}%") for c, v, p in ca], src_note, label_w=210)
    sections.append(section(
        site, "types", "What kinds of ingredients supplements contain",
        f"<strong>{ca[0][2]}%</strong> of labels list at least one {data(ca[0][0].lower())} ingredient, {ca[1][2]}% a {data(ca[1][0].lower())} and {ca[2][2]}% a {data(ca[2][0].lower())}. "
        f"Probiotic bacteria appear on {next(p for c, _, p in ca if c == 'Bacteria')}% of labels.",
        figure(site, "categories", charts["categories"], "Ingredient types by share of products", f"{n(P)} labels"),
        table(["Ingredient type", "Products", "Share"], [(c, n(v), f"{p}%") for c, v, p in ca], {1, 2}),
        "Ingredient type is the NIH DSLD ingredient group of each active. A product counts once per type it contains, so shares sum to more than 100%."))

    bf = s["blend_by_form"]
    charts["proprietary-blends"] = svg_hbar(site, "Proprietary blends by product form", "Share of labels that hide at least one dose inside a proprietary blend",
                                            [(f, p, f"{p}%") for f, _, _, p in bf], src_note, label_w=170)
    sections.append(section(
        site, "blends", "How often the dose is hidden",
        f"<strong>{s['blend_products_pct']}%</strong> of supplement labels use a proprietary blend, which lists ingredients without their individual amounts. "
        f"As a result <strong>{s['no_amount_pct']}%</strong> of all {n(s['rows'])} ingredient listings carry no per-ingredient dose. "
        f"{data(bf[0][0])} products hide doses most often ({bf[0][3]}%), {data(bf[-1][0])} least ({bf[-1][3]}%).",
        figure(site, "proprietary-blends", charts["proprietary-blends"], "Proprietary blends by product form", f"{n(sum(c for _, c, _, _ in bf))} labels with a stated form"),
        table(["Product form", "Products", "With a proprietary blend", "Share"], [(f, n(c), n(b), f"{p}%") for f, c, b, p in bf], {1, 2, 3}),
        "A listing is flagged as a proprietary blend when the label groups it under a blend total instead of stating its own amount; the blend flag and the missing "
        "amount are both taken from the NIH DSLD label record. Forms with fewer than 100 products are omitted."))

    ar = s["above_rda"]
    charts["above-daily-value"] = svg_hbar(site, "Share of listings above the adult daily reference intake", "Nutrients with 200+ dosed listings; per serving, adult RDA or AI",
                                           [(nm, p, f"{p}%") for nm, _, _, p, _ in ar[:15]], src_note, label_w=150)
    au = s["above_ul"]
    charts["above-upper-limit"] = svg_hbar(site, "Share of listings above the tolerable upper intake level", "Nutrients with 100+ dosed listings; per serving, adult UL",
                                           [(nm, p, f"{p}%") for nm, _, _, p, _ in au[:12]], src_note, label_w=150)
    sections.append(section(
        site, "doses", "How doses compare with reference intakes",
        f"Per serving, <strong>{ar[0][3]}%</strong> of {data(ar[0][0])} listings exceed the adult daily reference intake, as do {ar[1][3]}% of {data(ar[1][0])} and {ar[2][3]}% of {data(ar[2][0])} listings. "
        f"Against the tolerable upper intake level, the line most often crossed is {data(au[0][0])}: <strong>{au[0][3]}%</strong> of its dosed listings exceed the adult UL per serving, "
        f"followed by {data(au[1][0])} ({au[1][3]}%) and {data(au[2][0])} ({au[2][3]}%).",
        figure(site, "above-daily-value", charts["above-daily-value"], "Share of listings above the adult daily reference intake", f"{n(s['rda_rows'])} dosed listings with a reference value")
        + figure(site, "above-upper-limit", charts["above-upper-limit"], "Share of listings above the tolerable upper intake level", f"{len(au)} nutrients with an adult UL"),
        table(["Nutrient", "Dosed listings", "Above daily reference", "Share", "Reference (mg per day)"],
              [(nm, n(c), n(o), f"{p}%", f"{r:g}") for nm, c, o, p, r in ar], {1, 2, 3, 4})
        + "<h3 class=\"font-display\">Above the tolerable upper intake level</h3>"
        + table(["Nutrient", "Dosed listings", "Above UL", "Share", "UL (mg per day)"],
                [(nm, n(c), n(o), f"{p}%", f"{u:g}") for nm, c, o, p, u in au], {1, 2, 3, 4}),
        "Reference values are the NIH Office of Dietary Supplements adult RDA or AI and tolerable upper intake level (UL), stored per nutrient in milligrams. "
        "Comparisons are per labelled serving, not per day, and only listings with a stated amount are counted. Exceeding the RDA is common and often intended; "
        "the UL for magnesium applies to supplemental intake only and the UL for niacin to nicotinic acid, so read these as label facts, not as a safety verdict. "
        "Some products are formulated for use under medical supervision."))

    fo = s["forms"]
    plural = {"Capsule": "capsules", "Powder": "powders", "Tablet or Pill": "tablets or pills", "Softgel Capsule": "softgel capsules",
              "Liquid": "liquids", "Gummy or Jelly": "gummies or jellies", "Lozenge": "lozenges"}
    charts["forms"] = svg_hbar(site, "Supplement forms", f"Share of {n(P)} products by labelled form",
                               [(f, c, f"{p}%") for f, c, p in fo], src_note, label_w=170)
    cb = s["cpp_buckets"]
    charts["ingredients-per-product"] = svg_hbar(site, "How many active ingredients a product lists", f"Share of {n(P)} products by number of actives",
                                                 [(lbl, c, f"{p}%") for lbl, c, p in cb], src_note, label_w=110)
    sections.append(section(
        site, "forms", "Forms and formula size",
        f"<strong>{fo[0][2]}%</strong> of products are {data(plural.get(fo[0][0], fo[0][0].lower()))}, {fo[1][2]}% {data(plural.get(fo[1][0], fo[1][0].lower()))} "
        f"and {fo[2][2]}% {data(plural.get(fo[2][0], fo[2][0].lower()))}. "
        f"<strong>{s['single_ingredient_pct']}%</strong> of products contain a single active ingredient; the median product has {s['cpp_median']}, the mean {s['cpp_mean']}, "
        f"and the most complex formula lists {n(s['cpp_max'])}. A container holds a median of {s['servings']['median']} servings.",
        figure(site, "forms", charts["forms"], "Supplement forms", f"{n(P)} products")
        + figure(site, "ingredients-per-product", charts["ingredients-per-product"], "How many active ingredients a product lists", f"{n(P)} products"),
        table(["Form", "Products", "Share"], [(f, n(c), f"{p}%") for f, c, p in fo], {1, 2})
        + "<h3 class=\"font-display\">Actives per product</h3>"
        + table(["Actives", "Products", "Share"], [(lbl, n(c), f"{p}%") for lbl, c, p in cb], {1, 2}),
        f"Form is the label's own dosage form as recorded by NIH DSLD. Servings per container are stated on {n(s['servings']['products'])} of {n(P)} labels "
        f"(interquartile range {s['servings']['p25']} to {s['servings']['p75']})."))

    mg = s["magnesium_forms"]
    charts["magnesium-forms"] = svg_hbar(site, "Which magnesium supplements actually contain", f"Share of {n(s['magnesium_rows'])} magnesium listings by chemical form",
                                         [(f, c, f"{p}%") for f, c, p in mg], src_note, label_w=230)
    caf = s["caffeine"]
    sections.append(section(
        site, "forms-detail", "Two ingredients up close: magnesium and caffeine",
        f"{data(mg[0][0])} is the most common magnesium form at <strong>{mg[0][2]}%</strong> of magnesium listings, ahead of {data(mg[2][0] if mg[1][0] == 'Magnesium' else mg[1][0])} "
        f"({(mg[2][2] if mg[1][0] == 'Magnesium' else mg[1][2])}%) and {data('Magnesium Glycinate')} ({next(p for f, _, p in mg if f == 'Magnesium Glycinate')}%); "
        f"{next(p for f, _, p in mg if f == 'Magnesium')}% of listings name no salt at all. "
        f"Caffeine is dosed on {n(caf['products'])} labels at a median of <strong>{caf['median']} mg</strong> per serving (mean {caf['mean']} mg, maximum {caf['max']} mg); "
        f"{n(caf['over_200'])} of them exceed 200 mg in one serving.",
        figure(site, "magnesium-forms", charts["magnesium-forms"], "Which magnesium supplements actually contain", f"{n(s['magnesium_rows'])} magnesium listings"),
        table(["Magnesium form", "Listings", "Share"], [(f, n(c), f"{p}%") for f, c, p in mg], {1, 2}),
        "Magnesium form is the specific ingredient named on the label; a label that lists the element without a salt is shown as Magnesium. "
        "Caffeine figures use listings with a stated amount, whether from caffeine anhydrous or a caffeine-standardised extract."))

    tb = s["top_brands"]
    charts["top-brands"] = svg_hbar(site, "Brands with the most products on file", f"Products per brand, top 15 of {n(s['brands'])} brands",
                                    [(b, c, n(c)) for b, c in tb], src_note, label_w=240)
    sections.append(section(
        site, "brands", "Brands with the most products on file",
        f"{data(tb[0][0])} has the most labels on file with <strong>{n(tb[0][1])}</strong>, ahead of {data(tb[1][0])} ({n(tb[1][1])}) and {data(tb[2][0])} ({n(tb[2][1])}). "
        f"The catalogue spans {n(s['brands'])} brands; most have a handful of products.",
        figure(site, "top-brands", charts["top-brands"], "Brands with the most products on file", f"top 15 of {n(s['brands'])} brands"),
        table(["Brand", "Products"], [(b, n(c)) for b, c in tb], {1}),
        "Brand names are as printed on the label and recorded by NIH DSLD. Counts reflect how many of a brand's labels are in the database, not its market share."))

    contents = toc([("ingredients", "Most common ingredients"), ("types", "Ingredient types"), ("blends", "Proprietary blends"), ("doses", "Doses vs reference intakes"),
                    ("forms", "Forms and formula size"), ("forms-detail", "Magnesium and caffeine"), ("brands", "Brands"), ("method", "Method, reuse and citation")])
    tile_html = tiles([("Supplement labels", n(P)), ("Brands", n(s["brands"])), ("Ingredient listings", n(s["rows"])), ("Distinct ingredients", n(s["compounds"])),
                       ("Proprietary blends", f"{s['blend_products_pct']}%"), ("Snapshot", snap)])
    title_tag = f"Supplement Statistics {snap[:4]} — Most Common Ingredients, Proprietary Blends, Doses vs RDA | SuppDB"
    desc = (f"Supplements in numbers from {n(P)} NIH DSLD labels: the most common ingredients, share of products using proprietary blends, doses versus the daily reference "
            f"intake and the upper limit, forms, magnesium forms, caffeine per serving. Free to cite and embed.")
    ld = article_ld(site, "Dietary supplements in numbers: statistics from the SuppDB label database", desc, FIRST_PUBLISHED,
                    f"{site.base_url}/og-image.png", ["dietary supplements", "nootropics", "proprietary blends", "vitamin doses", "NIH DSLD"])

    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title_tag)}</title>
  <meta name="description" content="{esc(desc)}" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{site.page_url}" />
  <link rel="alternate" hreflang="en" href="{site.page_url}" />
  <link rel="icon" href="/favicon.ico" type="image/x-icon" />
  <meta property="og:title" content="Supplements in numbers — SuppDB statistics {snap[:4]}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{site.page_url}" />
  <meta property="og:type" content="article" />
  <meta property="og:image" content="{site.base_url}/og-image.png" />
  <meta name="twitter:card" content="summary_large_image" />

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
  <noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet"></noscript>
{ld}
  <style>{CSS}{STATS_CSS}  </style>
</head>
<body>
  <div class="container">
    <div class="header-bar">
      <div>
        <a href="/" translate="no" style="font-weight: 700; letter-spacing: -0.02em; color: var(--text-ink);">SUPPDB</a>
        <span style="opacity: 0.6; font-size: 0.75rem; margin-left: 12px;">| Market statistics</span>
      </div>
      <a href="/" style="font-size: 0.85rem;">← Back to Main Explorer</a>
    </div>

    <h1 class="font-display">Dietary supplements in numbers</h1>
    <p class="lede">Aggregate statistics computed from the full SuppDB catalogue: {n(P)} supplement and nootropic labels from the NIH Dietary Supplement Label Database, {n(s['rows'])} active-ingredient listings normalised to milligrams, with a label ID and URL on every record. Snapshot of {snap}. Every figure is free to cite, quote and embed with a link to this page.</p>
    <ul class="tiles">{tile_html}</ul>
    <nav class="toc" aria-label="Contents"><strong>On this page</strong><ol>{contents}</ol></nav>

{"".join(sections)}

    <section class="stat" id="method">
      <h2 class="font-display">Method, reuse and citation</h2>
      <ul class="method">
        <li><strong>Source.</strong> The full SuppDB snapshot of {snap}: {n(P)} product labels from the <a href="https://dsld.od.nih.gov/">NIH Dietary Supplement Label Database</a> (U.S. Government, public domain), each with its DSLD label ID and URL. Active ingredients are normalised to milligrams per serving; chemistry for {n(s['pubchem_compounds'])} of {n(s['compounds_total'])} distinct ingredients comes from NIH PubChem.</li>
        <li><strong>Nothing is estimated.</strong> Amounts, forms, blend flags and serving counts are the label's own values as recorded by DSLD. Where a label states no amount the listing is excluded from dose figures, and every section states its denominator.</li>
        <li><strong>Labels, not sales.</strong> DSLD holds labels submitted or collected by NIH, so shares describe what is on the market's labels, not what is sold or consumed, and reference-intake comparisons are per serving as labelled.</li>
        <li><strong>Refresh.</strong> SuppDB is rebuilt from the DSLD manifest on a monthly cadence; this page and its charts are regenerated with each snapshot, so figures move. Cite the snapshot date.</li>
        <li><strong>Reuse.</strong> The figures and charts on this page are published under <a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>: use them in articles, slides and posts with a link to <span translate="no">{site.page_url}</span>. The machine-readable version is <a href="/stats/data.json">data.json</a>. The underlying row-level catalogue is a separate <a href="/#pricing">commercial product</a>; a free sample is in the <a href="https://github.com/SuppDB/supplements-nootropics-suppdb">public repository</a>.</li>
        <li><strong>Suggested citation.</strong> <span translate="no">SuppDB ({snap[:4]}). <em>Dietary supplements in numbers</em>, snapshot {snap}. DataEngineered. {site.page_url}</span></li>
        <li><strong>Questions or corrections:</strong> <a href="/#support">contact form</a> or suppdb@dataengineered.io.</li>
      </ul>
    </section>

    <div class="cta">
      <h3 class="font-display" style="font-size: 1.4rem;">Need the row-level catalogue behind these numbers?</h3>
      <p style="color: var(--text-muted); margin-top: 8px; font-size: 0.85rem;">Every label with its ingredients, milligram doses, blend flags, forms, serving counts and PubChem chemistry, as SQLite, CSV and JSON.</p>
      <a href="/#pricing" class="btn">Get the full dataset ($49) →</a>
    </div>
  </div>
  <footer style="border-top:1px solid var(--rule-color); margin-top:40px; padding:24px 16px; text-align:center;">
    <div class="catalog-line" style="text-align:center; margin-top:14px; font-size:0.85rem; opacity:0.85;"><a href="https://dataengineered.io/">Part of the DataEngineered catalog →</a> · <a href="https://dataengineered.io/about">About</a> · <a href="https://dataengineered.io/terms">Terms</a> · <a href="https://dataengineered.io/privacy">Privacy</a> · <a href="https://dataengineered.io/refund-policy">Refund policy</a></div>
  </footer>
{COPY_JS}
</body>
</html>
"""


def build_data_json(s):
    return {
        "dataset": SITE.brand, "page": SITE.page_url, "generated": dt.date.today().isoformat(), "snapshot": s["snapshot_date"],
        "license": "CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/) - attribute with a link to the page; label facts are NIH DSLD, public domain",
        "totals": {k: s[k] for k in ("products", "brands", "rows", "compounds", "compounds_total", "pubchem_compounds", "pubchem_rows")},
        "top_ingredients": [dict(ingredient=nm, products=c, share_pct=p) for nm, c, p in s["top_compounds"]],
        "ingredient_types": [dict(type=c, products=v, share_pct=p) for c, v, p in s["categories"]],
        "proprietary_blends": {"products": s["blend_products"], "products_pct": s["blend_products_pct"], "listings": s["blend_rows"], "listings_pct": s["blend_rows_pct"],
                               "listings_without_amount": s["no_amount_rows"], "listings_without_amount_pct": s["no_amount_pct"],
                               "by_form": [dict(form=f, products=c, with_blend=b, share_pct=p) for f, c, b, p in s["blend_by_form"]]},
        "doses": {"reference": "NIH ODS adult RDA/AI and UL, mg per day; comparisons per labelled serving, dosed listings only",
                  "above_daily_reference": [dict(nutrient=nm, listings=c, above=o, share_pct=p, reference_mg=r) for nm, c, o, p, r in s["above_rda"]],
                  "above_upper_limit": [dict(nutrient=nm, listings=c, above=o, share_pct=p, ul_mg=u) for nm, c, o, p, u in s["above_ul"]]},
        "forms": [dict(form=f, products=c, share_pct=p) for f, c, p in s["forms"]],
        "actives_per_product": {"median": s["cpp_median"], "mean": s["cpp_mean"], "max": s["cpp_max"],
                                "buckets": [dict(bucket=lbl, products=c, share_pct=p) for lbl, c, p in s["cpp_buckets"]]},
        "servings_per_container": s["servings"],
        "magnesium_forms": {"listings": s["magnesium_rows"], "rows": [dict(form=f, listings=c, share_pct=p) for f, c, p in s["magnesium_forms"]]},
        "caffeine_mg_per_serving": s["caffeine"],
        "top_brands": [dict(brand=b, products=c) for b, c in s["top_brands"]],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", default=os.environ.get("SUPPDB_SQLITE", str(DEFAULT_DB)))
    args = ap.parse_args()
    db = Path(args.db)
    if not db.is_file():
        raise SystemExit(f"SQLite snapshot not found: {db}")
    s = compute(db)
    charts = {}
    page = build_page(s, charts)
    write_outputs(OUT_DIR, page, charts, build_data_json(s))
    print(f"stats/index.html + {len(charts)} charts + data.json  (snapshot {s['snapshot_date']}, {s['products']:,} products)")


if __name__ == "__main__":
    main()
