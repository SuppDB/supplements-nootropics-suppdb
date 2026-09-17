#!/usr/bin/env python3
"""Generate the /ingredients/ and /products/ directory hubs, plus a second level of
range hubs for each (spec rule 4: any hub with >100 child links gets one, and each
child hub should land in the 20-80 link range -- a literal per-letter split undershoots
that badly for sparse letters like "q" or "z").

Both content directories shipped with no index page, and the homepage
linked just four ingredient pages -- through absolute .html URLs, which
the site 308s to their extensionless form. So 810 of 814 pages were
orphaned: listed in the sitemap, unreachable by following links. The
interactive explorer on the homepage is a static sample table with a JS
filter, not a crawl path.

That matters here more than elsewhere in the portfolio: these are the
only orphaned pages in the portfolio that have actually drawn
impressions (/ingredients/creatine 25, /ingredients/vitamin-d 17), so
the corpus can rank -- it just cannot be crawled.

/ingredients/ alone has ~519 child pages, well past the 100-link rule of
thumb, so it no longer lists every ingredient itself: it links one
directory page per first-letter range (/ingredients/a/, /ingredients/b/,
/ingredients/d-f/, ...), each holding at least MIN_BUCKET (20) entries --
`make_buckets()` walks the sorted first-letter groups and greedily merges
consecutive ones until a bucket clears that floor, so a sparse run of
letters (d, e, h, i, j, ... ) collapses into one range hub instead of
several near-empty ones. "0-9" is never its own hub: it always folds into
whichever range comes first. The same split applies to /products/.

This builds the top-level hub, the range hubs, writes the homepage
link block between its BEGIN/END markers, and rebuilds sitemap.xml from
scratch (homepage + both top hubs + every range hub + every leaf) via
seo_common.write_sitemap -- this is the single place sitemap.xml gets
written; scripts/generate_seo_pages.py only touches products/*.html and
ingredients/*.html, so run this script after it.

Every leaf's label is taken from the page's own <h1> and <title>, so the
hubs restate what those pages already say.

Run from the repo root:  python scripts/generate_hubs.py
"""

import html as htmllib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seo_common import fit_title, fit_desc, write_sitemap

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
BASE = "https://suppdb.dataengineered.io"

BEGIN = "<!-- BEGIN:hub-browse -->"
END = "<!-- END:hub-browse -->"

SECTIONS = [
    {
        "slug": "ingredients",
        "h1": "Ingredient directory",
        "desc": ("Every supplement ingredient in SuppDB, each with its own monograph: "
                 "molecular formula, weight, PubChem id, InChIKey and the commercial "
                 "products it appears in."),
        "lede": ("One page per ingredient. Each carries the chemical determination -- "
                 "molecular formula, molecular weight, PubChem record and exact InChIKey -- "
                 "alongside the commercial products that contain it and their per-serving doses."),
        "label": "ingredient monographs",
        "kind": "ingredient",
    },
    {
        "slug": "products",
        "h1": "Product directory",
        "desc": ("Every commercial supplement product in SuppDB, each with its normalised "
                 "per-serving ingredient doses in mg."),
        "lede": ("One page per commercial product, with its label panel normalised to "
                 "per-serving milligrams. Proprietary blends whose per-ingredient dose is "
                 "undisclosed are flagged rather than dropped."),
        "label": "product labels",
        "kind": "product",
    },
]

STYLE = """* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg-paper: #0b0e0f; --bg-paper-2: #121618; --text-ink: #eef1f2;
  --text-muted: #97a1a3; --rule-color: rgba(238, 241, 242, 0.18);
  --accent: #2fd4a3; --card-bg: #161a1d;
}
body { font-family: 'Outfit', system-ui, -apple-system, sans-serif; background: var(--bg-paper);
  color: var(--text-ink); line-height: 1.6; padding-bottom: 60px; }
.mono { font-family: 'JetBrains Mono', ui-monospace, monospace; }
header { border-bottom: 1px solid var(--rule-color); padding: 20px 0;
  background: rgba(18, 22, 24, 0.85); backdrop-filter: blur(10px); }
.container { max-width: 1000px; margin: 0 auto; padding: 0 24px; }
.nav-bar { display: flex; justify-content: space-between; align-items: center; }
.brand { font-size: 1.5rem; font-weight: 700; color: var(--text-ink); text-decoration: none; }
.brand span { color: var(--accent); }
.btn-link { color: var(--text-ink); text-decoration: none; font-size: 0.88rem;
  border: 1px solid var(--rule-color); padding: 8px 16px; border-radius: 6px; transition: all 0.2s; }
.btn-link:hover { background: var(--accent); color: #0b0e0f; border-color: var(--accent); }
.hero { padding: 44px 0; border-bottom: 1px solid var(--rule-color); }
.badge { display: inline-block; background: rgba(47, 212, 163, 0.15); color: var(--accent);
  padding: 4px 12px; border-radius: 4px; font-size: 0.8rem; font-weight: 600;
  margin-bottom: 12px; border: 1px solid rgba(47, 212, 163, 0.3); }
h1 { font-size: 2.4rem; font-weight: 700; margin-top: 6px; letter-spacing: -0.02em; }
.sub { color: var(--text-muted); font-size: 1.08rem; margin-top: 8px; max-width: 72ch; }
.count { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 0.78rem;
  color: var(--text-muted); margin-top: 20px; letter-spacing: 0.06em; }
.back { margin-bottom: 18px; }
.alpha { margin-top: 34px; }
.alpha-h { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 0.82rem;
  font-weight: 700; color: var(--accent); letter-spacing: 0.12em; padding-bottom: 8px;
  border-bottom: 1px solid var(--rule-color); }
.dirlist { list-style: none; margin: 14px 0 0; padding: 0; display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 2px; }
.dirlist a { display: block; padding: 9px 12px; text-decoration: none; border-radius: 6px; }
.dirlist a:hover { background: var(--card-bg); }
.dirlist a:hover .n { color: var(--accent); }
.n { display: block; font-weight: 600; font-size: 0.95rem; color: var(--text-ink); }
.d { display: block; font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 0.7rem; color: var(--text-muted); margin-top: 2px; }
footer { margin-top: 60px; border-top: 1px solid var(--rule-color); padding: 32px 0;
  text-align: center; font-size: 0.85rem; color: var(--text-muted); }
footer a { color: var(--accent); }"""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{desc}" />
  <meta name="robots" content="index, follow, max-image-preview:large" />
  <link rel="canonical" href="{url}" />
  <link rel="alternate" hreflang="en" href="{url}" />
  <link rel="alternate" hreflang="x-default" href="{url}" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:type" content="website" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
  <script type="application/ld+json">
  {{"@context": "https://schema.org", "@type": "CollectionPage", "name": "{h1}", "description": "{jdesc}", "url": "{url}", "isPartOf": {{"@type": "WebSite", "name": "SuppDB", "url": "{base}"}}, "publisher": {{"@type": "Organization", "name": "DataEngineered", "url": "{base}"}}}}
  </script>
  <style>
{style}
  </style>
</head>
<body>
  <header>
    <div class="container nav-bar">
      <a href="/" class="brand">Supp<span>DB</span></a>
      <div>
        <a href="/#explorer" class="btn-link">&larr; Explorer</a>
        <a href="/#pricing" class="btn-link" style="margin-left: 10px; background: rgba(47, 212, 163, 0.1);">Full Dataset ($49)</a>
      </div>
    </div>
  </header>

  <main class="container">
    {back}
    <section class="hero">
      <span class="badge mono">DIRECTORY</span>
      <h1>{h1_html}</h1>
      <p class="sub">{lede}</p>
      <p class="count">{n} {label}</p>
    </section>

{groups}
  </main>

  <footer>
    <div class="container">
      SuppDB &middot; <a href="/#pricing">Full snapshot ($49)</a> &middot; <a href="/">suppdb.dataengineered.io</a>
      <div class="catalog-line" style="text-align:center; margin-top:14px; font-size:0.85rem; opacity:0.85;"><a href="https://dataengineered.io/">Part of the DataEngineered catalog &rarr;</a> &middot; <a href="https://dataengineered.io/about">About</a> &middot; <a href="https://dataengineered.io/terms">Terms</a> &middot; <a href="https://dataengineered.io/privacy">Privacy</a> &middot; <a href="https://dataengineered.io/refund-policy">Refund policy</a></div>
    </div>
  </footer>
</body>
</html>
"""


def text_of(pattern, source):
    m = re.search(pattern, source, re.S)
    if not m:
        return ""
    return htmllib.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


def read_entry(path, kind):
    src = path.read_text(encoding="utf-8", errors="replace")
    name = text_of(r"<h1[^>]*>(.*?)</h1>", src) or path.stem
    title = text_of(r"<title[^>]*>(.*?)</title>", src)
    desc = ""
    if kind == "ingredient":
        # "<Name> — in <n> products | SuppDB" -> the descriptor
        m = re.match(r"^\s*.*?\s[—-]\s(.+?)\s\|\s", title)
        if m:
            desc = m.group(1).strip()
    else:
        # "<Product> by <Brand> — ... | SuppDB" -> the brand
        m = re.match(r"^\s*.*?\sby\s+(.+?)\s+[—-]\s", title)
        if m:
            desc = m.group(1).strip()
    if desc.lower() == name.lower():
        desc = ""
    return {"slug": path.stem, "name": name, "desc": desc}


def group_key(name):
    c = name[:1].upper()
    return c if c.isalpha() else "0-9"


MIN_BUCKET = 20
MAX_BUCKET = 80


def make_buckets(order, groups):
    """Walk the ordered first-character groups (as built from `order`/`groups` in
    build_section -- "0-9" first if present, then A..Z present ones only, ascending)
    and greedily merge consecutive ones until each bucket holds >= MIN_BUCKET entries,
    starting a new bucket instead whenever the current one already clears MIN_BUCKET and
    the next group would push it past MAX_BUCKET. A trailing short remainder merges into
    the previous bucket instead of standing alone under the 20-link target. "0-9" is
    never its own bucket: it's always the first key considered, so it silently folds into
    whatever the first bucket becomes.

    A bucket still under MIN_BUCKET always takes the next group regardless of the
    resulting size -- there's no way to split a single first-letter group further in
    this scheme, so a bucket can only end up over MAX_BUCKET if one letter's own count
    already exceeds it (not the case for this dataset; the largest single letter is 60).

    The trailing remainder (whatever's left in cur_entries once `order` is exhausted)
    normally merges into the previous bucket -- but only if that merge doesn't push
    the previous bucket past MAX_BUCKET. When it would, the remainder stands alone as
    its own final bucket instead of overflowing the one before it. That standalone
    remainder is necessarily under MIN_BUCKET (that's exactly why it never finalized
    into a bucket of its own during the loop above), so it's the one bucket exempted
    from the floor in the hard assertion below -- every bucket, remainder included,
    still respects the MAX_BUCKET ceiling."""
    buckets = []
    cur_keys, cur_entries = [], []
    for k in order:
        group = groups[k]
        if cur_keys and len(cur_entries) >= MIN_BUCKET and len(cur_entries) + len(group) > MAX_BUCKET:
            buckets.append((cur_keys, cur_entries))
            cur_keys, cur_entries = [], []
        cur_keys.append(k)
        cur_entries = cur_entries + group
        if len(cur_entries) >= MIN_BUCKET:
            buckets.append((cur_keys, cur_entries))
            cur_keys, cur_entries = [], []

    is_remainder_bucket = False
    if cur_keys:
        if buckets and len(buckets[-1][1]) + len(cur_entries) <= MAX_BUCKET:
            prev_keys, prev_entries = buckets[-1]
            buckets[-1] = (prev_keys + cur_keys, prev_entries + cur_entries)
        else:
            buckets.append((cur_keys, cur_entries))
            is_remainder_bucket = True

    for i, (keys, entries) in enumerate(buckets):
        n = len(entries)
        is_exempt_remainder = is_remainder_bucket and i == len(buckets) - 1
        assert n <= MAX_BUCKET, f"bucket {keys!r} has {n} entries, over MAX_BUCKET={MAX_BUCKET}"
        assert n >= MIN_BUCKET or is_exempt_remainder, (
            f"bucket {keys!r} has {n} entries, under MIN_BUCKET={MIN_BUCKET}")
    return buckets


def bucket_label(keys):
    """Human-facing range label, e.g. "a", "d-f". "0-9" folded in is never shown --
    it rides along with whichever alphabetic key(s) it was merged with."""
    alpha = [k for k in keys if k != "0-9"]
    if not alpha:
        return "0-9"
    return alpha[0] if len(alpha) == 1 else "%s-%s" % (alpha[0], alpha[-1])


def bucket_slug(keys):
    alpha = [k for k in keys if k != "0-9"]
    if not alpha:
        return "0-9"
    lo, hi = alpha[0].lower(), alpha[-1].lower()
    return lo if lo == hi else "%s-%s" % (lo, hi)


def render_dirlist(entries, prefix="", data_desc=False):
    """`prefix` is prepended to each href. Leaf entries live one directory above the range
    hub that lists them (ingredients/5-htp, not ingredients/a/5-htp), so callers rendering
    a range hub's own leaf list must pass prefix="../"; the top-level hub's links to the
    range hubs are already siblings of it, so they pass no prefix.

    Entry names (ingredient/product names, range labels) carry translate="no" for
    scripts/i18n_common.py; so does the descriptor when it is data (a product's brand,
    `data_desc=True`) rather than copy ("in 12 products"). Rendering is unchanged."""
    items = []
    for e in entries:
        tn = ' translate="no"' if data_desc else ""
        dh = ('<span class="d"%s>%s</span>' % (tn, htmllib.escape(e["desc"]))) if e["desc"] else ""
        items.append(
            '        <li><a href="%s%s"><span class="n" translate="no">%s</span>%s</a></li>'
            % (prefix, htmllib.escape(e["slug"]), htmllib.escape(e["name"]), dh)
        )
    return '      <ul class="dirlist">\n%s\n      </ul>' % "\n".join(items)


def build_section(sec):
    d = ROOT / sec["slug"]
    pages = sorted(p for p in d.glob("*.html") if p.stem != "index")
    if not pages:
        sys.exit("no pages found in %s/" % sec["slug"])

    entries = [read_entry(p, sec["kind"]) for p in pages]
    entries.sort(key=lambda e: (group_key(e["name"]) != "0-9", e["name"].lower()))

    groups, order = {}, []
    for e in entries:
        k = group_key(e["name"])
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(e)

    buckets = make_buckets(order, groups)
    ranges = {}
    for keys, bucket_entries in buckets:
        label = bucket_label(keys)
        bslug = bucket_slug(keys)
        n_b = len(bucket_entries)
        examples = ", ".join(e["name"] for e in bucket_entries[:3])
        bucket_url = "%s/%s/%s/" % (BASE, sec["slug"], bslug)
        title = fit_title("%s — %s" % (sec["h1"], label), "%d %s" % (n_b, sec["label"]), "SuppDB")
        desc = fit_desc("%d %s from %s in SuppDB's %s, including %s." %
                         (n_b, sec["label"], label, sec["h1"].lower(), examples))
        back = ('<p class="back"><a href="../" class="btn-link" style="font-size:0.8rem;">'
                '&larr; All %s</a></p>' % sec["label"])
        page = PAGE.format(
            base=BASE, url=bucket_url, title=htmllib.escape(title), desc=htmllib.escape(desc),
            jdesc=desc.replace('"', "'"), h1="%s: %s" % (sec["h1"], label),
            h1_html='%s: <span translate="no">%s</span>' % (sec["h1"], label), lede=sec["lede"],
            label=sec["label"], n=n_b, style=STYLE, back=back,
            groups='    <section class="alpha">\n' + render_dirlist(bucket_entries, prefix="../", data_desc=sec["kind"] == "product") + '\n    </section>',
        )
        bucket_dir = d / bslug
        bucket_dir.mkdir(exist_ok=True)
        (bucket_dir / "index.html").write_text(page, encoding="utf-8", newline="")
        ranges[bslug] = {"slug": bslug, "count": n_b, "label": label}

    # Top-level hub: links the range hubs (not every leaf -- that's the >100-link problem).
    range_items = []
    for info in ranges.values():
        range_items.append({
            "slug": "%s/" % info["slug"],
            "name": info["label"],
            "desc": "%d %s" % (info["count"], sec["label"]),
        })
    top_url = "%s/%s/" % (BASE, sec["slug"])
    title = fit_title(sec["h1"], "%d %s" % (len(entries), sec["label"]), "SuppDB")
    desc = fit_desc(sec["desc"])
    page = PAGE.format(
        base=BASE, url=top_url, title=htmllib.escape(title), desc=htmllib.escape(desc),
        jdesc=sec["desc"].replace('"', "'"), h1=sec["h1"], h1_html=sec["h1"], lede=sec["lede"],
        label=sec["label"],
        n=len(entries), style=STYLE, back="",
        groups='    <section class="alpha">\n      <h2 class="alpha-h">BROWSE BY RANGE</h2>\n'
               + render_dirlist(range_items) + '\n    </section>',
    )
    (d / "index.html").write_text(page, encoding="utf-8", newline="")
    return len(entries), ranges


def update_homepage(counts):
    """Link both top-level directories from the end of the explorer section.

    The explorer is where the page already invites browsing, but it is a
    static sample table behind a JS filter -- these are the links that
    actually lead anywhere. (The letter hubs are one hop further, linked
    from each top-level directory page itself.)
    """
    src = INDEX.read_text(encoding="utf-8")
    block = (
        '{begin}\n'
        '      <p style="text-align: center; margin-top: 18px; font-size: 0.95rem;">\n'
        '        Browse every page: <a href="/ingredients/" style="color: var(--accent); '
        'text-decoration: underline; font-weight: 600;">{i} ingredient monographs</a> '
        '&middot; <a href="/products/" style="color: var(--accent); text-decoration: underline; '
        'font-weight: 600;">{p} product labels</a>\n'
        '      </p>\n'
        '      {end}'
    ).format(begin=BEGIN, end=END, i=counts["ingredients"], p=counts["products"])

    if BEGIN in src and END in src:
        src = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END),
                     lambda _: block, src, flags=re.DOTALL)
    else:
        anchor = '    </div>\n  </section>\n\n  <section class="section section-alt" id="pricing">'
        if anchor not in src:
            sys.exit("could not find the end of the #explorer section")
        src = src.replace(anchor, block + "\n" + anchor, 1)

    # The four hand-written ingredient links point at .html, which the site
    # 308s to the extensionless form. Internal links must not go via a redirect.
    src = re.sub(r'(https://suppdb\.dataengineered\.io/(?:ingredients|products)/[a-z0-9-]+)\.html',
                 r"\1", src)

    INDEX.write_text(src, encoding="utf-8", newline="")


def rebuild_sitemap(ranges_by_section):
    """The single place sitemap.xml gets written: homepage, both top hubs, every
    range hub, and every leaf, all through seo_common.write_sitemap (dedupes,
    drops non-HTML, stamps lastmod from git)."""
    entries = [(BASE + "/", INDEX, "weekly", "1.0")]
    for sec in SECTIONS:
        d = ROOT / sec["slug"]
        priority = "0.9" if sec["kind"] == "ingredient" else "0.8"
        entries.append(("%s/%s/" % (BASE, sec["slug"]), d / "index.html", "weekly", "0.9"))
        for info in ranges_by_section[sec["slug"]].values():
            range_url = "%s/%s/%s/" % (BASE, sec["slug"], info["slug"])
            entries.append((range_url, d / info["slug"] / "index.html", "weekly", "0.7"))
        for p in sorted(d.glob("*.html")):
            if p.stem == "index":
                continue
            entries.append(("%s/%s/%s" % (BASE, sec["slug"], p.stem), p, "monthly", priority))
    return write_sitemap(ROOT, entries)


def main():
    counts = {}
    ranges_by_section = {}
    for sec in SECTIONS:
        n, ranges = build_section(sec)
        counts[sec["slug"]] = n
        ranges_by_section[sec["slug"]] = ranges
        print("wrote %s/index.html -- %d entries across %d range hubs" %
              (sec["slug"], n, len(ranges)))
    update_homepage(counts)
    print("homepage block updated; .html internal links rewritten extensionless")
    n_urls = rebuild_sitemap(ranges_by_section)
    print("sitemap.xml rebuilt -- %d URLs" % n_urls)


if __name__ == "__main__":
    main()
