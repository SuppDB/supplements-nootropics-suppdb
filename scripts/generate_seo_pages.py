import csv
import os
import re
import datetime
import html
from collections import defaultdict, Counter

def slugify(text):
    if not text:
        return 'unknown'
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def _mg(x):
    # integers for >=1 mg; keep sub-mg values (e.g. 0.5) instead of rounding to 0
    return f"{x:.0f}" if x >= 1 else f"{x:g}"

def _oxford(items):
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"

def _is_prop(v):
    return str(v).strip() in ('1', 'true', 'True', 'Yes', 'yes')

def _cid_ok(v):
    v = str(v or '').strip()
    return v.replace('.', '', 1).isdigit()

def product_profile(rows, brand, pname, form_type, serving_count, serving_unit):
    """Unique, data-derived formulation summary for a product page."""
    esc = html.escape
    n = len(rows)
    ing = "ingredient" if n == 1 else "ingredients"
    doses = [d for d in (_num(r.get('amount_per_serving_mg')) for r in rows) if d and d > 0]
    total = sum(doses)
    prop = sum(1 for r in rows if _is_prop(r.get('is_proprietary_blend')))
    with_cid = sum(1 for r in rows if _cid_ok(r.get('pubchem_cid')))
    spc = (rows[0].get('servings_per_container') or '').strip()
    p = (f"This SuppDB record normalizes {n} active {ing} from {esc(brand)}'s {esc(pname)} label "
         f"as a {esc(form_type)} supplement at {esc(str(serving_count))} {esc(serving_unit)} per serving")
    if spc and spc not in ('', '0', '0.0'):
        p += f", {esc(spc)} servings per container"
    p += "."
    if doses:
        p += f" {len(doses)} of {n} {ing} carry an exact per-serving dose"
        p += f", together totalling {_mg(total)} mg." if total else "."
    if prop:
        p += f" {prop} {'sits' if prop == 1 else 'sit'} inside a proprietary blend where the label withholds the exact split."
    if with_cid:
        iw = "ingredient" if with_cid == 1 else "ingredients"
        p += f" {with_cid} {iw} {'is' if with_cid == 1 else 'are'} cross-referenced to NIH PubChem chemistry."
    return f'<p style="color:var(--text-muted); font-size:1.02rem; margin-top:20px; max-width:72ch;">{p}</p>'

def ingredient_profile(ing_name, rows, category, formula, weight, inchikey):
    """Unique, data-derived occurrence + chemistry summary for an ingredient page."""
    esc = html.escape
    prods, brands, doses, forms, rec, ul = set(), set(), [], Counter(), [], []
    for r in rows:
        b = (r.get('brand') or '').strip()
        pn = (r.get('product_name') or '').strip()
        if pn:
            prods.add((b, pn))
        if b:
            brands.add(b)
        d = _num(r.get('amount_per_serving_mg'))
        if d and d > 0:
            doses.append(d)
        fm = (r.get('ingredient_form') or '').strip()
        if fm and fm.lower() != (ing_name or '').lower():
            forms[fm] += 1
        rd = _num(r.get('recommended_daily_mg'))
        if rd and rd > 0:
            rec.append(rd)
        u = _num(r.get('upper_safety_limit_mg'))
        if u and u > 0:
            ul.append(u)
    np_ = len(prods) or len(rows)
    nb = len(brands)
    p = f"{esc(ing_name)} appears in {np_} commercial supplement {'product' if np_ == 1 else 'products'}"
    if nb:
        p += f" across {nb} {'brand' if nb == 1 else 'brands'}"
    p += " in this SuppDB sample"
    if doses:
        lo, hi = min(doses), max(doses)
        p += (f", at a per-serving dose of {_mg(lo)} mg" if lo == hi
              else f", at per-serving doses ranging {_mg(lo)}–{_mg(hi)} mg")
    p += "."
    if category:
        p += f" It is catalogued as a {esc(category)} ingredient"
        if forms:
            p += ", supplied in forms such as " + _oxford([esc(f) for f, _ in forms.most_common(3)])
        p += "."
    chem = []
    if formula and formula != 'N/A':
        chem.append(f"molecular formula {esc(formula)}")
    if weight and weight != 'N/A':
        chem.append(f"a molecular weight of {esc(str(weight))} g/mol")
    if inchikey and inchikey != 'N/A':
        chem.append(f"InChIKey {esc(inchikey)}")
    if chem:
        p += " Its NIH PubChem record lists " + _oxford(chem) + "."
    refs = []
    if rec:
        refs.append(f"a recommended intake of {_mg(min(rec))} mg" if min(rec) == max(rec)
                    else f"recommended intakes of {_mg(min(rec))}–{_mg(max(rec))} mg")
    if ul:
        refs.append(f"an upper safety limit up to {_mg(max(ul))} mg")
    if refs:
        p += " Label reference values in the sample record " + _oxford(refs) + "."
    return f'<p style="color:var(--text-muted); font-size:1.02rem; margin-top:20px; max-width:72ch;">{p}</p>'

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_csv = os.path.join(root_dir, 'samples', 'suppdb_sample.csv')
    products_dir = os.path.join(root_dir, 'products')
    ingredients_dir = os.path.join(root_dir, 'ingredients')

    os.makedirs(products_dir, exist_ok=True)
    os.makedirs(ingredients_dir, exist_ok=True)

    products = defaultdict(list)
    ingredients = defaultdict(list)

    if os.path.exists(sample_csv):
        with open(sample_csv, mode='r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get('product_id', '').strip()
                if pid:
                    products[pid].append(row)
                
                ing = row.get('ingredient', '').strip()
                if ing and len(ing) > 1:
                    ingredients[ing].append(row)

    print(f"Loaded {len(products)} distinct products and {len(ingredients)} unique active ingredients from CSV.")

    sitemap_urls = [
        ("https://supplements-nootropics-suppdb.pages.dev/", "1.0", "weekly")
    ]

    # Generate Product Monograph Pages (top products or all products in sample)
    generated_products = 0
    for pid, rows in products.items():
        if not rows:
            continue
        first = rows[0]
        brand = first.get('brand', 'Unknown Brand').strip()
        pname = first.get('product_name', 'Unnamed Supplement').strip()
        upc = first.get('upc_barcode', '').strip()
        form_type = first.get('form_type', 'Capsule').strip()
        serving_count = first.get('serving_size_count', '1').strip()
        serving_unit = first.get('serving_size_unit', 'Capsule(s)').strip()
        dsld_id = first.get('dsld_label_id', '').strip()
        source_url = first.get('source_url', 'https://dsld.od.nih.gov/').strip()

        slug = slugify(f"{brand}-{pname}")
        if not slug or len(slug) < 3:
            continue
        page_url = f"https://supplements-nootropics-suppdb.pages.dev/products/{slug}"
        sitemap_urls.append((page_url, "0.8", "monthly"))
        generated_products += 1

        # Table of ingredients
        ing_rows_html = ""
        for r in rows:
            ing_name = r.get('ingredient', '').strip()
            ing_slug = slugify(ing_name)
            ing_form = r.get('ingredient_form', '').strip() or ing_name
            amount = r.get('amount_per_serving_mg', '').strip()
            is_prop = "Yes" if str(r.get('is_proprietary_blend', '')).strip() in ['1', 'true', 'Yes'] else "No"
            cid = r.get('pubchem_cid', '').strip()
            if cid and cid.replace('.','',1).isdigit():
                cid_clean = cid.split('.')[0]
                cid_link = f'<a href="https://pubchem.ncbi.nlm.nih.gov/compound/{cid_clean}" target="_blank" rel="noopener noreferrer" style="color:var(--accent); text-decoration:none;">CID {cid_clean} ↗</a>'
            else:
                cid_link = '—'

            ing_link = f'<a href="../ingredients/{ing_slug}" style="color:var(--text-ink); font-weight:600; text-decoration:none;">{ing_name}</a>'
            amount_display = f"{amount} mg" if amount else "Blend / Variable"

            ing_rows_html += f"""
          <tr style="border-bottom: 1px solid var(--rule-color);">
            <td style="padding: 12px 14px;">{ing_link}<br><span style="font-size:0.8rem; color:var(--text-muted);">{ing_form}</span></td>
            <td style="padding: 12px 14px; font-family:'JetBrains Mono', monospace; font-weight:600; color:var(--accent);">{amount_display}</td>
            <td style="padding: 12px 14px; text-align:center;">{is_prop}</td>
            <td style="padding: 12px 14px;">{cid_link}</td>
          </tr>"""

        html_content = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{pname} by {brand} — Supplement Facts &amp; Normalized mg Dosages — SuppDB</title>
  <meta name="description" content="Complete supplement facts for {pname} by {brand} ({form_type}, {serving_count} {serving_unit} serving). Exact mg ingredient normalization, proprietary blend flags, and NIH PubChem chemical CIDs." />
  <meta name="keywords" content="{pname}, {brand}, supplement facts, {form_type}, mg dosage, proprietary blend, NIH DSLD {dsld_id}" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{page_url}" />
  <link rel="alternate" hreflang="en" href="{page_url}" />
  <link rel="alternate" hreflang="x-default" href="{page_url}" />

  <meta property="og:title" content="{pname} by {brand} — Normalized Supplement Facts" />
  <meta property="og:description" content="Exact mg ingredient dosages, chemical formulations, and NIH DSLD verification record for {pname}." />
  <meta property="og:url" content="{page_url}" />
  <meta property="og:type" content="article" />

  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "{pname} by {brand}",
    "description": "Normalized supplement facts record for {pname}: {form_type}, {serving_count} {serving_unit} serving size, verified against NIH DSLD label #{dsld_id}.",
    "brand": {{"@type": "Brand", "name": "{brand}"}},
    "category": "Health & Beauty > Health Care > Fitness & Nutrition > Vitamins & Supplements"
  }}
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://supplements-nootropics-suppdb.pages.dev/"}},
      {{"@type": "ListItem", "position": 2, "name": "Products Index", "item": "https://supplements-nootropics-suppdb.pages.dev/#explorer"}},
      {{"@type": "ListItem", "position": 3, "name": "{pname}", "item": "{page_url}"}}
    ]
  }}
  </script>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
  <noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet"></noscript>

  <style>
    :root {{
      --bg-paper: #0b0e0f;
      --bg-paper-2: #121618;
      --text-ink: #eef1f2;
      --text-muted: #97a1a3;
      --rule-color: rgba(238, 241, 242, 0.18);
      --accent: #2fd4a3;
      --card-bg: #161a1d;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Outfit', sans-serif; background: var(--bg-paper); color: var(--text-ink); line-height: 1.6; padding-bottom: 60px; }}
    .mono {{ font-family: 'JetBrains Mono', monospace; }}
    header {{ border-bottom: 1px solid var(--rule-color); padding: 20px 0; background: rgba(18, 22, 24, 0.85); backdrop-filter: blur(10px); }}
    .container {{ max-width: 1000px; margin: 0 auto; padding: 0 24px; }}
    .nav-bar {{ display: flex; justify-content: space-between; align-items: center; }}
    .brand {{ font-size: 1.5rem; font-weight: 700; color: var(--text-ink); text-decoration: none; }}
    .brand span {{ color: var(--accent); }}
    .btn-link {{ color: var(--text-ink); text-decoration: none; font-size: 0.88rem; border: 1px solid var(--rule-color); padding: 8px 16px; border-radius: 6px; transition: all 0.2s; }}
    .btn-link:hover {{ background: var(--accent); color: #0b0e0f; border-color: var(--accent); }}
    .hero {{ padding: 44px 0; border-bottom: 1px solid var(--rule-color); }}
    .badge {{ display: inline-block; background: rgba(47, 212, 163, 0.15); color: var(--accent); padding: 4px 12px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; margin-bottom: 12px; border: 1px solid rgba(47, 212, 163, 0.3); }}
    .card {{ background: var(--card-bg); border: 1px solid var(--rule-color); padding: 28px; border-radius: 10px; margin-top: 32px; }}
    table {{ width: 100%; border-collapse: collapse; text-align: left; margin-top: 16px; }}
    th {{ padding: 12px 14px; border-bottom: 2px solid var(--rule-color); color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; }}
    footer {{ margin-top: 60px; border-top: 1px solid var(--rule-color); padding: 32px 0; text-align: center; font-size: 0.85rem; color: var(--text-muted); }}
  </style>
</head>
<body>
  <header>
    <div class="container nav-bar">
      <a href="/" class="brand">Supp<span>DB</span></a>
      <div>
        <a href="/#explorer" class="btn-link">← Explorer</a>
        <a href="/#pricing" class="btn-link" style="margin-left: 10px; background: rgba(47, 212, 163, 0.1);">License Snapshot ($49)</a>
      </div>
    </div>
  </header>

  <main class="container">
    <section class="hero">
      <span class="badge mono">NIH DSLD LABEL #{dsld_id or '1001'} · {form_type.upper()}</span>
      <h1 style="font-size: 2.4rem; font-weight: 700; margin-top: 6px;">{pname}</h1>
      <p style="color: var(--text-muted); font-size: 1.15rem; margin-top: 6px;">Manufactured by <strong style="color: var(--text-ink);">{brand}</strong> · Serving Size: {serving_count} {serving_unit}</p>
    </section>
    {product_profile(rows, brand, pname, form_type, serving_count, serving_unit)}
    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <h3 style="font-size: 1.35rem; color: var(--accent);">Normalized Supplement Facts &amp; Chemistry</h3>
        <a href="{source_url}" target="_blank" rel="noopener noreferrer" class="btn-link" style="font-size:0.8rem;">🔬 Verify on NIH DSLD ↗</a>
      </div>
      <p style="color:var(--text-muted); font-size:0.88rem; margin-top:6px;">All dosage quantities standardized to exact milligrams (mg). Chemical identifiers cross-referenced via NIH PubChem.</p>

      <div style="overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>Ingredient / Chemical Form</th>
              <th>mg / Serving</th>
              <th style="text-align:center;">Proprietary Blend?</th>
              <th>PubChem CID</th>
            </tr>
          </thead>
          <tbody>
            {ing_rows_html}
          </tbody>
        </table>
      </div>
    </div>
  </main>

  <footer>
    <div class="container">
      <p>SuppDB — Supplements &amp; Nootropics Normalized Dataset · <a href="/#pricing" style="color:var(--accent); text-decoration:none;">Download Complete 17,000+ Product Snapshot ($49)</a></p>
    </div>
  </footer>
</body>
</html>"""
        with open(os.path.join(products_dir, f"{slug}.html"), mode='w', encoding='utf-8') as f_out:
            f_out.write(html_content)

    # Generate Active Ingredient Monograph Pages (top unique active ingredients)
    generated_ingredients = 0
    for ing_name, rows in ingredients.items():
        if not rows:
            continue
        slug = slugify(ing_name)
        if not slug or len(slug) < 2 or slug in ['unspecified', 'other']:
            continue

        first = rows[0]
        ing_form = first.get('ingredient_form', ing_name).strip() or ing_name
        category = first.get('ingredient_category', 'botanical/supplement').strip()
        cid = first.get('pubchem_cid', '').strip()
        formula = first.get('molecular_formula', '').strip() or 'N/A'
        weight = first.get('molecular_weight', '').strip() or 'N/A'
        inchikey = first.get('inchikey', '').strip() or 'N/A'
        smiles = first.get('canonical_smiles', '').strip() or 'N/A'

        page_url = f"https://supplements-nootropics-suppdb.pages.dev/ingredients/{slug}"
        sitemap_urls.append((page_url, "0.9", "monthly"))
        generated_ingredients += 1

        # Matching products
        prod_links_html = ""
        seen_p = set()
        for r in rows:
            p_brand = r.get('brand', '').strip()
            p_name = r.get('product_name', '').strip()
            p_slug = slugify(f"{p_brand}-{p_name}")
            if p_slug in seen_p or not p_slug:
                continue
            seen_p.add(p_slug)
            amt = r.get('amount_per_serving_mg', 'Variable')
            prod_links_html += f"""
          <div style="padding: 14px 0; border-bottom: 1px dashed var(--rule-color); display:flex; justify-content:space-between; align-items:center;">
            <div>
              <a href="../products/{p_slug}" style="color:var(--text-ink); font-weight:600; text-decoration:none; font-size:1rem;">{p_name}</a>
              <div style="font-size:0.82rem; color:var(--text-muted);">{p_brand}</div>
            </div>
            <span class="mono" style="color:var(--accent); font-weight:600;">{amt} mg</span>
          </div>"""

        cid_display = f'<a href="https://pubchem.ncbi.nlm.nih.gov/compound/{cid.split(".")[0]}" target="_blank" rel="noopener noreferrer" style="color:var(--accent); text-decoration:none;">CID {cid.split(".")[0]} ↗</a>' if (cid and cid.replace('.','',1).isdigit()) else 'Not assigned / Complex botanical extract'

        html_content = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{ing_name} ({ing_form}) Supplement Facts &amp; PubChem Monograph — SuppDB</title>
  <meta name="description" content="Chemical determination &amp; supplement facts for {ing_name} ({category}): formula {formula}, weight {weight} g/mol, PubChem {cid.split('.')[0] if cid else 'verified'}, exact InChIKey, and commercial product dosages." />
  <meta name="keywords" content="{ing_name}, {ing_form}, {formula}, PubChem {cid.split('.')[0] if cid else ''}, nootropics dosage, supplement chemistry" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{page_url}" />
  <link rel="alternate" hreflang="en" href="{page_url}" />
  <link rel="alternate" hreflang="x-default" href="{page_url}" />

  <meta property="og:title" content="{ing_name} ({ing_form}) Chemical &amp; Dosage Monograph — SuppDB" />
  <meta property="og:description" content="Formula: {formula} · Weight: {weight} · InChIKey: {inchikey}" />
  <meta property="og:url" content="{page_url}" />
  <meta property="og:type" content="article" />

  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "ChemicalSubstance",
    "name": "{ing_name}",
    "alternateName": "{ing_form}",
    "chemicalRole": "{category}",
    "molecularFormula": "{formula}",
    "molecularWeight": "{weight}"
  }}
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://supplements-nootropics-suppdb.pages.dev/"}},
      {{"@type": "ListItem", "position": 2, "name": "Ingredients Index", "item": "https://supplements-nootropics-suppdb.pages.dev/#explorer"}},
      {{"@type": "ListItem", "position": 3, "name": "{ing_name}", "item": "{page_url}"}}
    ]
  }}
  </script>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
  <noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet"></noscript>

  <style>
    :root {{
      --bg-paper: #0b0e0f;
      --bg-paper-2: #121618;
      --text-ink: #eef1f2;
      --text-muted: #97a1a3;
      --rule-color: rgba(238, 241, 242, 0.18);
      --accent: #2fd4a3;
      --card-bg: #161a1d;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Outfit', sans-serif; background: var(--bg-paper); color: var(--text-ink); line-height: 1.6; padding-bottom: 60px; }}
    .mono {{ font-family: 'JetBrains Mono', monospace; }}
    header {{ border-bottom: 1px solid var(--rule-color); padding: 20px 0; background: rgba(18, 22, 24, 0.85); backdrop-filter: blur(10px); }}
    .container {{ max-width: 1000px; margin: 0 auto; padding: 0 24px; }}
    .nav-bar {{ display: flex; justify-content: space-between; align-items: center; }}
    .brand {{ font-size: 1.5rem; font-weight: 700; color: var(--text-ink); text-decoration: none; }}
    .brand span {{ color: var(--accent); }}
    .btn-link {{ color: var(--text-ink); text-decoration: none; font-size: 0.88rem; border: 1px solid var(--rule-color); padding: 8px 16px; border-radius: 6px; transition: all 0.2s; }}
    .btn-link:hover {{ background: var(--accent); color: #0b0e0f; border-color: var(--accent); }}
    .hero {{ padding: 44px 0; border-bottom: 1px solid var(--rule-color); }}
    .badge {{ display: inline-block; background: rgba(47, 212, 163, 0.15); color: var(--accent); padding: 4px 12px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; margin-bottom: 12px; border: 1px solid rgba(47, 212, 163, 0.3); }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 28px; margin-top: 32px; }}
    @media(max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    .card {{ background: var(--card-bg); border: 1px solid var(--rule-color); padding: 28px; border-radius: 10px; }}
    .metric-row {{ display: flex; justify-content: space-between; border-bottom: 1px dashed rgba(238,241,242,0.12); padding: 12px 0; font-size:0.92rem; }}
    .metric-row:last-child {{ border-bottom: none; }}
    footer {{ margin-top: 60px; border-top: 1px solid var(--rule-color); padding: 32px 0; text-align: center; font-size: 0.85rem; color: var(--text-muted); }}
  </style>
</head>
<body>
  <header>
    <div class="container nav-bar">
      <a href="/" class="brand">Supp<span>DB</span></a>
      <div>
        <a href="/#explorer" class="btn-link">← Explorer</a>
        <a href="/#pricing" class="btn-link" style="margin-left: 10px; background: rgba(47, 212, 163, 0.1);">Full Dataset ($49)</a>
      </div>
    </div>
  </header>

  <main class="container">
    <section class="hero">
      <span class="badge mono">CHEMICAL MONOGRAPH · {category.upper()}</span>
      <h1 style="font-size: 2.4rem; font-weight: 700; margin-top: 6px;">{ing_name}</h1>
      <p style="color: var(--text-muted); font-size: 1.15rem; margin-top: 6px;">Chemical determination, molecular structure, and commercial supplement product occurrences.</p>
    </section>
    {ingredient_profile(ing_name, rows, category, formula, weight, inchikey)}
    <div class="grid">
      <div class="card">
        <h3 style="font-size: 1.3rem; color: var(--accent); margin-bottom: 16px; border-bottom: 1px solid var(--rule-color); padding-bottom: 10px;">NIH PubChem Chemistry</h3>
        <div class="metric-row">
          <span style="color:var(--text-muted);">PubChem Record</span>
          <span>{cid_display}</span>
        </div>
        <div class="metric-row">
          <span style="color:var(--text-muted);">Molecular Formula</span>
          <span class="mono" style="font-weight:600;">{formula}</span>
        </div>
        <div class="metric-row">
          <span style="color:var(--text-muted);">Molecular Weight</span>
          <span class="mono">{weight} g/mol</span>
        </div>
        <div class="metric-row" style="flex-direction:column; gap:4px;">
          <span style="color:var(--text-muted);">InChIKey</span>
          <span class="mono" style="font-size:0.78rem; word-break:break-all; color:var(--accent);">{inchikey}</span>
        </div>
        <div class="metric-row" style="flex-direction:column; gap:4px;">
          <span style="color:var(--text-muted);">Canonical SMILES</span>
          <span class="mono" style="font-size:0.75rem; word-break:break-all; color:var(--text-muted);">{smiles}</span>
        </div>
      </div>

      <div class="card">
        <h3 style="font-size: 1.3rem; color: var(--accent); margin-bottom: 16px; border-bottom: 1px solid var(--rule-color); padding-bottom: 10px;">Commercial Product Dosages</h3>
        <div style="max-height: 340px; overflow-y: auto; padding-right: 8px;">
          {prod_links_html}
        </div>
      </div>
    </div>
  </main>

  <footer>
    <div class="container">
      <p>SuppDB — Supplements &amp; Nootropics Normalized Dataset · <a href="/#pricing" style="color:var(--accent); text-decoration:none;">Download Complete 17,000+ Product Snapshot ($49)</a></p>
    </div>
  </footer>
</body>
</html>"""
        with open(os.path.join(ingredients_dir, f"{slug}.html"), mode='w', encoding='utf-8') as f_out:
            f_out.write(html_content)

    # Generate updated sitemap.xml
    sitemap_path = os.path.join(root_dir, 'sitemap.xml')
    today_str = datetime.date.today().isoformat()
    sitemap_xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, prio, freq in sitemap_urls:
        sitemap_xml.append(f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today_str}</lastmod>\n    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>")
    sitemap_xml.append('</urlset>')

    with open(sitemap_path, mode='w', encoding='utf-8') as f_sitemap:
        f_sitemap.write("\n".join(sitemap_xml) + "\n")

    print(f"Successfully generated {generated_products} product monographs (`products/*.html`), {generated_ingredients} chemical monographs (`ingredients/*.html`), and updated sitemap.xml with {len(sitemap_urls)} URLs!")

if __name__ == '__main__':
    main()
