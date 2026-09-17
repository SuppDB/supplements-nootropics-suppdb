import csv
import os
import re
import sys
import html
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import fit_title, fit_desc, related_block, _cut

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

# Data values carry translate="no" (see scripts/i18n_common.py): localized copies keep them
# verbatim and translate only the sentence around them. Rendering is unchanged.
def _data(value):
    return f'<span translate="no">{html.escape(str(value))}</span>'

def _sentences(sentences):
    # one <span> per sentence: each optional clause is its own translation segment
    # instead of every combination of clauses being a different paragraph
    return " ".join(f"<span>{s}</span>" for s in sentences)

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
    sentences = []
    s = (f"This SuppDB record normalizes {n} active {ing} from {_data(brand)}'s {_data(pname)} label "
         f"as a {_data(form_type)} supplement at {esc(str(serving_count))} {_data(serving_unit)} per serving")
    if spc and spc not in ('', '0', '0.0'):
        s += f", {esc(spc)} servings per container"
    s += "."
    sentences.append(s)
    if doses:
        s = f"{len(doses)} of {n} {ing} carry an exact per-serving dose"
        s += f", together totalling {_mg(total)} mg." if total else "."
        sentences.append(s)
    if prop:
        sentences.append(f"{prop} {'sits' if prop == 1 else 'sit'} inside a proprietary blend where the label withholds the exact split.")
    if with_cid:
        iw = "ingredient" if with_cid == 1 else "ingredients"
        sentences.append(f"{with_cid} {iw} {'is' if with_cid == 1 else 'are'} cross-referenced to NIH PubChem chemistry.")
    return f'<p style="color:var(--text-muted); font-size:1.02rem; margin-top:20px; max-width:72ch;">{_sentences(sentences)}</p>'

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
    sentences = []
    p = f"{_data(ing_name)} appears in {np_} commercial supplement {'product' if np_ == 1 else 'products'}"
    if nb:
        p += f" across {nb} {'brand' if nb == 1 else 'brands'}"
    p += " in this SuppDB sample"
    if doses:
        lo, hi = min(doses), max(doses)
        p += (f", at a per-serving dose of {_mg(lo)} mg" if lo == hi
              else f", at per-serving doses ranging {_mg(lo)}–{_mg(hi)} mg")
    p += "."
    sentences.append(p)
    if category:
        p = f"It is catalogued as a {_data(category)} ingredient"
        if forms:
            top_forms = sorted(forms, key=lambda f: (-forms[f], f))[:3]
            p += ", supplied in forms such as " + _oxford([_data(f) for f in top_forms])
        p += "."
        sentences.append(p)
    chem = []
    if formula and formula != 'N/A':
        chem.append(f"molecular formula {_data(formula)}")
    if weight and weight != 'N/A':
        chem.append(f"a molecular weight of {esc(str(weight))} g/mol")
    if inchikey and inchikey != 'N/A':
        chem.append(f"InChIKey {_data(inchikey)}")
    if chem:
        sentences.append("Its NIH PubChem record lists " + _oxford(chem) + ".")
    refs = []
    if rec:
        refs.append(f"a recommended intake of {_mg(min(rec))} mg" if min(rec) == max(rec)
                    else f"recommended intakes of {_mg(min(rec))}–{_mg(max(rec))} mg")
    if ul:
        refs.append(f"an upper safety limit up to {_mg(max(ul))} mg")
    if refs:
        sentences.append("Label reference values in the sample record " + _oxford(refs) + ".")
    # Built from `rows` (a stable list), never from the `prods` set: set iteration order
    # is hash-randomized per process, which would make a most_common() tie-break --
    # and this generated sentence -- non-deterministic between runs.
    brand_counts = Counter()
    _seen_bp = set()
    for r in rows:
        b = (r.get('brand') or '').strip()
        pn = (r.get('product_name') or '').strip()
        if not pn or (b, pn) in _seen_bp:
            continue
        _seen_bp.add((b, pn))
        if b:
            brand_counts[b] += 1
    if brand_counts:
        top_brands = sorted(brand_counts, key=lambda b: (-brand_counts[b], b))[:3]
        brand_list = _oxford([_data(b) for b in top_brands])
        noun = "label" if len(top_brands) == 1 else "labels"
        sentences.append(f"Sold under the {brand_list} {noun} in this sample.")
    prop_n = sum(1 for r in rows if _is_prop(r.get('is_proprietary_blend')))
    if prop_n:
        total_n = len(rows)
        sentences.append(f"In {prop_n} of {total_n} label listings it is folded into an undisclosed proprietary blend rather than dosed on its own.")
    return f'<p style="color:var(--text-muted); font-size:1.02rem; margin-top:20px; max-width:72ch;">{_sentences(sentences)}</p>'

def product_meta_description(rows, brand, pname, form_type, serving_count, serving_unit):
    """First sentence = the product's most distinctive fact: form, serving, top-dosed ingredient."""
    n = len(rows)
    doses = [(r.get('ingredient', '').strip(), _num(r.get('amount_per_serving_mg'))) for r in rows]
    doses = [(nm, d) for nm, d in doses if nm and d and d > 0]
    if doses:
        top_name, top_mg = max(doses, key=lambda t: t[1])
        lead = (f"{pname} is a {form_type} supplement from {brand} at {serving_count} {serving_unit} "
                f"per serving, led by {top_name} at {_mg(top_mg)} mg.")
    else:
        lead = (f"{pname} is a {form_type} supplement from {brand} at {serving_count} {serving_unit} "
                f"per serving across {n} ingredients.")
    lead += f" Normalized supplement facts for all {n} ingredients with NIH PubChem cross-references."
    return fit_desc(lead)

def ingredient_meta_description(ing_name, rows):
    """First sentence = the ingredient's most distinctive fact: product count, forms, dosage range."""
    prods, forms, doses = set(), Counter(), []
    for r in rows:
        b = (r.get('brand') or '').strip()
        pn = (r.get('product_name') or '').strip()
        if pn:
            prods.add((b, pn))
        fm = (r.get('ingredient_form') or '').strip()
        if fm:
            forms[fm] += 1
        d = _num(r.get('amount_per_serving_mg'))
        if d and d > 0:
            doses.append(d)
    n = len(prods) or len(rows)
    lead = f"{ing_name} appears in {n} SuppDB {'product' if n == 1 else 'products'}"
    if forms:
        top_forms = sorted(forms, key=lambda f: (-forms[f], f))[:2]
        lead += f", most often as {_oxford(top_forms)}"
    lead += "."
    if doses:
        lo, hi = min(doses), max(doses)
        lead += (f" Per-serving dose is {_mg(lo)} mg." if lo == hi
                 else f" Per-serving doses range {_mg(lo)}–{_mg(hi)} mg.")
    return fit_desc(lead)

def _meta_shows_only_page_data(ing_name, rows, category, ing_form):
    """(og:title ok, description ok): True when every data value those <meta> strings
    carry (ingredient form names) is also shown on the page inside a translate="no"
    element, so i18n_common.py can placeholder it. Otherwise the tag gets translate="no"
    and stays English rather than becoming a one-page, data-bearing translation segment."""
    all_forms, shown_forms = Counter(), Counter()
    for r in rows:
        fm = (r.get('ingredient_form') or '').strip()
        if fm:
            all_forms[fm] += 1
            if fm.lower() != (ing_name or '').lower():
                shown_forms[fm] += 1
    shown = {ing_name}
    if category:  # ingredient_profile lists forms only in its category sentence
        shown |= set(sorted(shown_forms, key=lambda f: (-shown_forms[f], f))[:3])
    desc_forms = set(sorted(all_forms, key=lambda f: (-all_forms[f], f))[:2])
    return ing_form in shown, desc_forms <= shown

def _neighbour_fill(idx, ordered, exclude, need):
    """Pick up to `need` items from ordered[] around idx, skipping anything in exclude."""
    picked = []
    n = len(ordered)
    offset = 1
    while len(picked) < need and offset <= n:
        for cand_idx in (idx - offset, idx + offset):
            if 0 <= cand_idx < n:
                cand = ordered[cand_idx]
                if cand not in exclude:
                    picked.append(cand)
                    exclude.add(cand)
                    if len(picked) >= need:
                        break
        offset += 1
    return picked

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

    # --- Precompute cross-record metadata used for related-links (siblings, co-occurrence) ---
    product_meta = {}
    for pid, rows in products.items():
        if not rows:
            continue
        first = rows[0]
        brand = first.get('brand', 'Unknown Brand').strip()
        pname = first.get('product_name', 'Unnamed Supplement').strip()
        form_type = first.get('form_type', 'Capsule').strip()
        slug = slugify(f"{brand}-{pname}")
        if not slug or len(slug) < 3:
            continue
        product_meta[pid] = {"slug": slug, "pname": pname, "brand": brand, "form_type": form_type}

    by_brand, by_form = defaultdict(list), defaultdict(list)
    for pid, m in product_meta.items():
        by_brand[m["brand"]].append(pid)
        by_form[m["form_type"]].append(pid)
    name_sorted_pids = sorted(product_meta.keys(), key=lambda pid: product_meta[pid]["pname"].lower())
    pid_index = {pid: i for i, pid in enumerate(name_sorted_pids)}

    def _ing_valid(name):
        s = slugify(name)
        return bool(name) and len(name) > 1 and bool(s) and len(s) >= 2 and s not in ('unspecified', 'other')

    ingredient_slugs = {}
    for ing_name in ingredients:
        s = slugify(ing_name)
        if not s or len(s) < 2 or s in ('unspecified', 'other'):
            continue
        ingredient_slugs[ing_name] = s
    name_sorted_ings = sorted(ingredient_slugs.keys(), key=lambda n: n.lower())
    ing_index = {n: i for i, n in enumerate(name_sorted_ings)}

    co_occ = defaultdict(Counter)
    for pid, rows in products.items():
        names = sorted({r.get('ingredient', '').strip() for r in rows
                         if _ing_valid(r.get('ingredient', '').strip())})
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if names[i] in ingredient_slugs and names[j] in ingredient_slugs:
                    co_occ[names[i]][names[j]] += 1
                    co_occ[names[j]][names[i]] += 1

    # --- Title dedup: <title> must be unique across the whole site. Truncation to fit
    # 60 chars can collapse two distinct entities onto the same string (e.g. two products
    # with the same name from similarly-named brands), so titles are built in increasingly
    # specific rounds until every one is unique -- the last round is guaranteed unique
    # (product id / ingredient slug), so this always terminates.
    def _dedupe_titles(ids, round_fn):
        titles = {i: round_fn(i, 0) for i in ids}
        dupes = {t for t, c in Counter(titles.values()).items() if c > 1}
        if dupes:
            for i in ids:
                if titles[i] in dupes:
                    titles[i] = round_fn(i, 1)
        dupes = {t for t, c in Counter(titles.values()).items() if c > 1}
        if dupes:
            for i in ids:
                if titles[i] in dupes:
                    titles[i] = round_fn(i, 2)
        return titles

    _DANGLING_WORDS = {"by", "with", "without", "and", "of", "for", "the"}

    def _strip_dangling(text):
        """A word-boundary cut can leave a trailing preposition/conjunction dangling
        (e.g. "... without" or "... by") that reads as a broken mid-thought; strip it
        (repeatedly, in case more than one stacks up)."""
        words = text.split(" ")
        while words and words[-1].strip(" ,;:-–—()/").lower() in _DANGLING_WORDS:
            words.pop()
        return " ".join(words).rstrip(" ,;:-–—(/")

    def _title_has_full_brand(t, brand):
        """True only if the *entire* brand string appears intact right after " by ".

        A naive `" by " in t` check is satisfied even when a word-boundary cut lands
        right after the word "by" and drops the brand entirely -- the separator " — "
        that follows starts with a space, so "...Iron by — supplement | SuppDB" still
        contains the substring " by " despite the brand being completely missing. This
        instead requires the full brand string, followed by a non-alphanumeric character
        (the " (" of a form_type parenthetical, the " —" separator, or the " |" tail) so
        a partially-cut brand can never pass as a match."""
        marker = f" by {brand}"
        idx = t.find(marker)
        if idx == -1:
            return False
        end = idx + len(marker)
        return end >= len(t) or not t[end].isalnum()

    def _product_forced_title(pname, brand, extra=None, tag=None):
        """Force the brand (optionally with `extra`, e.g. a form_type disambiguator) into
        the title by pre-cutting the product name to whatever room is left over, rather
        than handing fit_title the combined "<name> by <brand>" entity -- fit_title tries
        the bare, untruncated entity before it tries truncating, so a long name would
        otherwise win over the brand and the brand would vanish silently. Cutting the name
        ourselves first makes the brand non-negotiable.

        `tag`, for the guaranteed-unique round, replaces the cut name's last word instead
        of being appended after it -- there's no spare room to add both, and this keeps
        the brand-bearing descriptor untouched and the result still <= 60 chars.

        If the brand itself is so long that "by {brand} | SuppDB" alone already exceeds
        60 chars -- i.e. there is no room for a product name at all, let alone the whole
        one -- naming the brand is mathematically impossible in this title format. Rather
        than let that degrade to a blank "| SuppDB" title (fit_title's own last-resort
        empty-descriptor branch would otherwise fire), fall back to the product name with
        no brand mention -- a real name beats an empty title.

        Likewise, when the brand leaves only a handful of characters for the name, a plain
        word-boundary cut can still land mid-word (_cut's own short-room hard-cut fallback
        chops wherever `room` lands, not at the nearest earlier space) -- e.g. "CBD Oil..."
        cut to room=5 becomes "CBD O", not "CBD". The name must always be a whole-word
        prefix of the real one, so that's verified explicitly below; anything narrower than
        one whole word (or under a 4-char floor) gives up on the brand entirely rather than
        publish a mangled fragment."""
        descriptor = f"by {brand}" + (f" ({extra})" if extra else "")
        tail = f" — {descriptor} | SuppDB"
        if len(tail) > 60:
            fallback_entity = f"{pname.rsplit(' ', 1)[0]} {tag}".strip() if tag and " " in pname \
                else (tag or pname)
            return fit_title(fallback_entity, "", "SuppDB")
        room = 60 - len(tail)
        entity = _strip_dangling(_cut(pname, room))
        first_word_len = len(pname.split(" ", 1)[0]) if pname else 0
        whole_word_prefix = (
            bool(entity) and pname.startswith(entity)
            and (len(entity) == len(pname) or pname[len(entity)] == " ")
        )
        if not whole_word_prefix or room < first_word_len or room < 4:
            # Not enough room for even one whole word of the product name alongside the
            # brand -- an honest brand-less title beats a mid-word fragment. `tag`, when
            # given, still goes in as the descriptor so the guaranteed-unique round stays
            # guaranteed unique even in this fallback.
            return fit_title(pname, [tag] if tag else ["supplement"], "SuppDB")
        if tag:
            base = entity.rsplit(" ", 1)[0] if " " in entity else ""
            joiner = " " if base else ""
            budget = room - len(tag) - len(joiner)
            if budget < 0:
                base, joiner = "", ""
            elif len(base) > budget:
                base = _strip_dangling(_cut(base, budget))
            entity = f"{base}{joiner}{tag}"
        return fit_title(entity, descriptor, "SuppDB")

    def _product_title_round(pid, round_n):
        m = product_meta[pid]
        pname, brand, form_type = m["pname"], m["brand"], m["form_type"]
        if round_n == 0:
            t = fit_title(f"{pname} by {brand}", ["Supplement Facts", "supplement"], "SuppDB")
            return t if _title_has_full_brand(t, brand) else _product_forced_title(pname, brand)
        if round_n == 1:
            t = fit_title(f"{pname} by {brand} ({form_type})",
                           ["Supplement Facts", "supplement"], "SuppDB")
            return t if _title_has_full_brand(t, brand) else \
                _product_forced_title(pname, brand, extra=form_type)
        # Guaranteed-unique fallback: pid is unique, so this always terminates the loop.
        return _product_forced_title(pname, brand, extra=form_type, tag=f"#{pid}")

    product_titles = _dedupe_titles(list(product_meta.keys()), _product_title_round)

    ingredient_n_products = {}
    ingredient_form_display = {}
    for ing_name in ingredient_slugs:
        rows_i = ingredients[ing_name]
        seen_pi = {slugify(f"{r.get('brand', '').strip()}-{r.get('product_name', '').strip()}")
                   for r in rows_i if r.get('product_name', '').strip()}
        ingredient_n_products[ing_name] = len(seen_pi) or len(rows_i)
        ingredient_form_display[ing_name] = (rows_i[0].get('ingredient_form') or '').strip() or ing_name

    def _ingredient_title_round(ing_name, round_n):
        descriptors = [f"in {ingredient_n_products[ing_name]} products", "supplement ingredient"]
        if round_n == 0:
            return fit_title(ing_name, descriptors, "SuppDB")
        if round_n == 1:
            return fit_title(f"{ing_name} ({ingredient_form_display[ing_name]})", descriptors, "SuppDB")
        return fit_title(f"{ing_name} ({ingredient_form_display[ing_name]})",
                          [f"#{ingredient_slugs[ing_name]}"], "SuppDB")

    ingredient_titles = _dedupe_titles(list(ingredient_slugs.keys()), _ingredient_title_round)

    # Generate Product Monograph Pages (top products or all products in sample)
    generated_products = 0
    for pid, rows in products.items():
        if pid not in product_meta:
            continue
        m = product_meta[pid]
        first = rows[0]
        brand = m["brand"]
        pname = m["pname"]
        form_type = m["form_type"]
        serving_count = first.get('serving_size_count', '1').strip()
        serving_unit = first.get('serving_size_unit', 'Capsule(s)').strip()
        dsld_id = first.get('dsld_label_id', '').strip()
        source_url = first.get('source_url', 'https://dsld.od.nih.gov/').strip()

        slug = m["slug"]
        page_url = f"https://suppdb.dataengineered.io/products/{slug}"
        generated_products += 1

        # Related products: 2 same-brand + 2 same-form (name-order neighbours fill any gap), + hub.
        _used = {pid}
        _sibs = []
        for p in by_brand.get(brand, []):
            if p != pid and p not in _used and len(_sibs) < 2:
                _used.add(p)
                _sibs.append(("brand", p))
        for p in by_form.get(form_type, []):
            if p != pid and p not in _used and len([s for s in _sibs if s[0] == "form"]) < 2:
                _used.add(p)
                _sibs.append(("form", p))
        if len(_sibs) < 2:
            for p in _neighbour_fill(pid_index[pid], name_sorted_pids, _used, 2 - len(_sibs)):
                _sibs.append(("neighbour", p))
        related_items = []
        for kind, p in _sibs:
            pm = product_meta[p]
            reason = {"brand": f"same brand — {brand}", "form": f"same form — {form_type}"}.get(kind)
            related_items.append((f"../products/{pm['slug']}", pm['pname'], reason, False))
        related_items.append(("../products/", "All product labels", None))
        related_html = related_block(related_items, heading="Related products", limit=None)
        # the brand / form inside a "same brand — X" reason is data: mark it for i18n_common.py
        for _why, _val in (("same brand", brand), ("same form", form_type)):
            related_html = related_html.replace(
                f'— {_why} — {html.escape(_val)}</span>',
                f'— {_why} — <span translate="no">{html.escape(_val)}</span></span>')

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

            ing_link = f'<a href="../ingredients/{ing_slug}" translate="no" style="color:var(--text-ink); font-weight:600; text-decoration:none;">{ing_name}</a>'
            amount_display = f"{amount} mg" if amount else "Blend / Variable"

            ing_rows_html += f"""
          <tr style="border-bottom: 1px solid var(--rule-color);">
            <td style="padding: 12px 14px;">{ing_link}<br><span translate="no" style="font-size:0.8rem; color:var(--text-muted);">{ing_form}</span></td>
            <td style="padding: 12px 14px; font-family:'JetBrains Mono', monospace; font-weight:600; color:var(--accent);">{amount_display}</td>
            <td style="padding: 12px 14px; text-align:center;">{is_prop}</td>
            <td style="padding: 12px 14px;">{cid_link}</td>
          </tr>"""

        page_title = html.escape(product_titles[pid])
        # A title that had to cut the product name (or drop the brand) carries a name
        # fragment no translate="no" element on the page repeats: keep it English rather
        # than turn it into a one-page, data-bearing translation segment.
        title_tn = "" if (pname in product_titles[pid] and brand in product_titles[pid]) else ' translate="no"'
        _desc = product_meta_description(rows, brand, pname, form_type, serving_count, serving_unit)
        page_desc = html.escape(_desc)
        # fit_desc cut through the lead ingredient's name ("led by Vitamin…"): that fragment
        # is data no translate="no" element repeats, so the tag stays English.
        _led = re.search(r" led by (.*)$", _desc)
        _top = [(r.get('ingredient', '').strip(), _num(r.get('amount_per_serving_mg'))) for r in rows]
        _top = [t for t in _top if t[0] and t[1] and t[1] > 0]
        _top_name = max(_top, key=lambda t: t[1])[0] if _top else ""
        desc_tn = ' translate="no"' if (_led and not re.match(re.escape(_top_name) + r"(?: at |…$)", _led.group(1))) else ""

        html_content = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title{title_tn}>{page_title}</title>
  <meta name="description" content="{page_desc}"{desc_tn} />
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
      {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://suppdb.dataengineered.io/"}},
      {{"@type": "ListItem", "position": 2, "name": "Products Index", "item": "https://suppdb.dataengineered.io/#explorer"}},
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
    .related {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid var(--rule-color); }}
    .related h2 {{ font-size: 1.1rem; color: var(--accent); margin-bottom: 10px; }}
    .related ul {{ list-style: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 4px; }}
    .related li {{ font-size: 0.92rem; }}
    .related a {{ color: var(--text-ink); text-decoration: none; }}
    .related a:hover {{ color: var(--accent); }}
    .related-why {{ color: var(--text-muted); font-size: 0.8rem; }}
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
      <span class="badge mono">NIH DSLD LABEL #{dsld_id or '1001'} · <span translate="no">{form_type.upper()}</span></span>
      <h1 translate="no" style="font-size: 2.4rem; font-weight: 700; margin-top: 6px;">{pname}</h1>
      <p style="color: var(--text-muted); font-size: 1.15rem; margin-top: 6px;">Manufactured by <strong translate="no" style="color: var(--text-ink);">{brand}</strong> · Serving Size: {serving_count} <span translate="no">{serving_unit}</span></p>
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
    {related_html}
  </main>

  <footer>
    <div class="container">
      <p>SuppDB — Supplements &amp; Nootropics Normalized Dataset · <a href="/#pricing" style="color:var(--accent); text-decoration:none;">Download Complete 17,000+ Product Snapshot ($49)</a></p>
      <div class="catalog-line" style="text-align:center; margin-top:14px; font-size:0.85rem; opacity:0.85;"><a href="https://dataengineered.io/">Part of the DataEngineered catalog →</a> · <a href="https://dataengineered.io/about">About</a> · <a href="https://dataengineered.io/terms">Terms</a> · <a href="https://dataengineered.io/privacy">Privacy</a> · <a href="https://dataengineered.io/refund-policy">Refund policy</a></div>
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

        page_url = f"https://suppdb.dataengineered.io/ingredients/{slug}"
        generated_ingredients += 1

        # Matching products (every one -- this is the full reciprocal list back to each product)
        prod_links_html = ""
        seen_p = set()
        prod_candidates = []
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
              <a href="../products/{p_slug}" translate="no" style="color:var(--text-ink); font-weight:600; text-decoration:none; font-size:1rem;">{p_name}</a>
              <div translate="no" style="font-size:0.82rem; color:var(--text-muted);">{p_brand}</div>
            </div>
            <span class="mono" style="color:var(--accent); font-weight:600;">{amt} mg</span>
          </div>"""
            prod_candidates.append((_num(amt) or 0, p_name, p_slug))

        cid_display = f'<a href="https://pubchem.ncbi.nlm.nih.gov/compound/{cid.split(".")[0]}" target="_blank" rel="noopener noreferrer" style="color:var(--accent); text-decoration:none;">CID {cid.split(".")[0]} ↗</a>' if (cid and cid.replace('.','',1).isdigit()) else 'Not assigned / Complex botanical extract'

        # Related: top 6 products by dose (full list already lives in the panel above),
        # 2 most-co-occurring ingredients, name-order neighbours to fill any gap, + hub.
        top6 = sorted(prod_candidates, key=lambda t: (-t[0], t[1].lower()))[:6]
        related_items = [(f"../products/{p_slug_}", p_name_, None, False) for _, p_name_, p_slug_ in top6]
        _used_ing = {ing_name}
        picked = 0
        _partners = co_occ.get(ing_name, Counter())
        for partner_name in sorted(_partners, key=lambda n: (-_partners[n], n.lower())):
            cnt = _partners[partner_name]
            if partner_name in _used_ing or partner_name not in ingredient_slugs:
                continue
            _used_ing.add(partner_name)
            related_items.append((f"../ingredients/{ingredient_slugs[partner_name]}", partner_name,
                                   f"co-occurs in {cnt} product{'s' if cnt != 1 else ''}", False))
            picked += 1
            if picked >= 2:
                break
        if len(related_items) < 2:
            for partner_name in _neighbour_fill(ing_index[ing_name], name_sorted_ings, _used_ing,
                                                 2 - len(related_items)):
                related_items.append((f"../ingredients/{ingredient_slugs[partner_name]}", partner_name, None, False))
        related_items.append(("../ingredients/", "All ingredient monographs", None))
        related_html = related_block(related_items, heading="Related ingredients", limit=None)

        page_title = html.escape(ingredient_titles[ing_name])
        page_desc = html.escape(ingredient_meta_description(ing_name, rows))
        _og_ok, _desc_ok = _meta_shows_only_page_data(ing_name, rows, category, ing_form)
        og_title_tn = "" if _og_ok else ' translate="no"'
        desc_tn = "" if _desc_ok else ' translate="no"'
        # i18n_common.py only placeholders translate="no" texts of 3+ characters, so an
        # element-symbol formula ("Ca", "B") would leak into a one-page segment
        og_desc_tn = ' translate="no"' if (formula != 'N/A' and len(formula) < 3 and not any(ch.isdigit() for ch in formula)) else ""

        html_content = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{page_title}</title>
  <meta name="description" content="{page_desc}"{desc_tn} />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{page_url}" />
  <link rel="alternate" hreflang="en" href="{page_url}" />
  <link rel="alternate" hreflang="x-default" href="{page_url}" />

  <meta property="og:title" content="{ing_name} ({ing_form}) Chemical &amp; Dosage Monograph — SuppDB"{og_title_tn} />
  <meta property="og:description" content="Formula: {formula} · Weight: {weight} · InChIKey: {inchikey}"{og_desc_tn} />
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
      {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://suppdb.dataengineered.io/"}},
      {{"@type": "ListItem", "position": 2, "name": "Ingredients Index", "item": "https://suppdb.dataengineered.io/#explorer"}},
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
    .related {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid var(--rule-color); }}
    .related h2 {{ font-size: 1.1rem; color: var(--accent); margin-bottom: 10px; }}
    .related ul {{ list-style: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 4px; }}
    .related li {{ font-size: 0.92rem; }}
    .related a {{ color: var(--text-ink); text-decoration: none; }}
    .related a:hover {{ color: var(--accent); }}
    .related-why {{ color: var(--text-muted); font-size: 0.8rem; }}
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
      <span class="badge mono">CHEMICAL MONOGRAPH · <span translate="no">{category.upper()}</span></span>
      <h1 translate="no" style="font-size: 2.4rem; font-weight: 700; margin-top: 6px;">{ing_name}</h1>
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
          <span class="mono" translate="no" style="font-weight:600;">{formula}</span>
        </div>
        <div class="metric-row">
          <span style="color:var(--text-muted);">Molecular Weight</span>
          <span class="mono">{weight} g/mol</span>
        </div>
        <div class="metric-row" style="flex-direction:column; gap:4px;">
          <span style="color:var(--text-muted);">InChIKey</span>
          <span class="mono" translate="no" style="font-size:0.78rem; word-break:break-all; color:var(--accent);">{inchikey}</span>
        </div>
        <div class="metric-row" style="flex-direction:column; gap:4px;">
          <span style="color:var(--text-muted);">Canonical SMILES</span>
          <span class="mono" translate="no" style="font-size:0.75rem; word-break:break-all; color:var(--text-muted);">{smiles}</span>
        </div>
      </div>

      <div class="card">
        <h3 style="font-size: 1.3rem; color: var(--accent); margin-bottom: 16px; border-bottom: 1px solid var(--rule-color); padding-bottom: 10px;">Commercial Product Dosages</h3>
        <div style="max-height: 340px; overflow-y: auto; padding-right: 8px;">
          {prod_links_html}
        </div>
      </div>
    </div>
    {related_html}
  </main>

  <footer>
    <div class="container">
      <p>SuppDB — Supplements &amp; Nootropics Normalized Dataset · <a href="/#pricing" style="color:var(--accent); text-decoration:none;">Download Complete 17,000+ Product Snapshot ($49)</a></p>
      <div class="catalog-line" style="text-align:center; margin-top:14px; font-size:0.85rem; opacity:0.85;"><a href="https://dataengineered.io/">Part of the DataEngineered catalog →</a> · <a href="https://dataengineered.io/about">About</a> · <a href="https://dataengineered.io/terms">Terms</a> · <a href="https://dataengineered.io/privacy">Privacy</a> · <a href="https://dataengineered.io/refund-policy">Refund policy</a></div>
    </div>
  </footer>
</body>
</html>"""
        with open(os.path.join(ingredients_dir, f"{slug}.html"), mode='w', encoding='utf-8') as f_out:
            f_out.write(html_content)

    # sitemap.xml is owned by scripts/generate_hubs.py (it runs after this script and also
    # knows about the /ingredients/, /products/ and letter-hub pages) -- run that next.
    print(f"Successfully generated {generated_products} product monographs (`products/*.html`) and "
          f"{generated_ingredients} chemical monographs (`ingredients/*.html`). "
          f"Run scripts/generate_hubs.py next to rebuild the hubs and sitemap.xml.")

if __name__ == '__main__':
    main()
