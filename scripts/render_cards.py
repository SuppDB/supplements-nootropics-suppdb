#!/usr/bin/env python3
"""
SuppDB card images (`SuppDB-public`), drawn as SVG and rendered with headless Microsoft Edge:

    og-image-v2.png           1200x630  social card (og:image, twitter:image, JSON-LD, webmanifest)
                              and the product image on both SuppDB Stripe products
    assets/kaggle-cover.png   1200x400  Kaggle cover + README banner

The cards carry no counts on purpose: counts move with every refresh, and an image sits outside
the claim checks. They name the canonical host only.

`_headers` serves /*.png as immutable for a year, so a changed social card needs a NEW file name
(update every reference, and list the old path in functions/_middleware.js RETIRED_FILES). The
Kaggle cover is not linked from any page, so it is redrawn in place.

Needs Windows with Edge and numpy (no Pillow): the screenshot is median-cut to 256 colours and
written as an indexed PNG.

Usage:
    python scripts/render_cards.py            # writes both files
    python scripts/render_cards.py --keep     # also keeps the intermediate HTML/PNG in .cards-build/
"""
import argparse
import shutil
import struct
import subprocess
import tempfile
import time
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

BG, BAR, GREEN, WHITE, GRID = "#0b0e0f", "#0d9c74", "#2fd4a3", "#eef1f2", "#151a1c"
SANS = "'Segoe UI', system-ui, sans-serif"
MONO = "'Cascadia Mono', Consolas, monospace"

HOST = "suppdb.dataengineered.io"
TITLE = "Supplements &amp; Nootropics Dataset"
SUBLINE = "NIH DSLD labels  ·  PubChem chemistry  ·  doses normalized to mg"
CHIPS = ["proprietary blends flagged", "InChIKey canonicalization", "source URL on every record"]


def logo():
    """Pill + wordmark, laid out for the 1200x630 card (pill box starts at 77,89)."""
    return f"""
  <g transform="translate(158.5 152) rotate(30)">
    <clipPath id="cap"><rect x="-88.5" y="-35" width="177" height="70" rx="35"/></clipPath>
    <g clip-path="url(#cap)">
      <rect x="-90" y="-40" width="90" height="80" fill="{GREEN}"/>
      <rect x="0" y="-40" width="90" height="80" fill="{WHITE}"/>
      <rect x="-7" y="-40" width="7" height="80" fill="{BG}"/>
    </g>
  </g>
  <text x="268" y="190" font-family="{SANS}" font-size="100" font-weight="600" fill="{WHITE}">SuppDB</text>
  <text x="650" y="172" font-family="{MONO}" font-size="28" fill="{GREEN}">// dataset</text>"""


def grid(x0, x1, y0, y1, step):
    xs = np.arange(x0, x1 + 1, step)
    ys = np.arange(y0, y1 + 1, step)
    lines = [f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}"/>' for x in xs]
    lines += [f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/>' for y in ys]
    return f'<g stroke="{GRID}" stroke-width="1.5">{"".join(lines)}</g>'


def og_card():
    chips, x = [], 72
    for label in CHIPS:
        w = round(len(label) * 0.6 * 20 + 36)  # Cascadia Mono advance is 0.6 em
        chips.append(
            f'<rect x="{x}" y="453.5" width="{w}" height="47" rx="14" fill="#0e1715" stroke="{GREEN}" '
            f'stroke-opacity="0.55" stroke-width="1.5"/>'
            f'<text x="{x + w / 2}" y="484" text-anchor="middle" font-family="{MONO}" font-size="20" '
            f'fill="{GREEN}">{label}</text>')
        x += w + 24
    return 1200, 630, f"""
  <rect width="1200" height="630" fill="{BG}"/>
  {grid(695, 1130, 100, 540, 88)}
  <rect width="1200" height="6" fill="{BAR}"/>
  {logo()}
  <text x="74" y="341" font-family="{SANS}" font-size="46" font-weight="600" fill="#f4f7f8">{TITLE}</text>
  <text x="74" y="388" font-family="{MONO}" font-size="28" fill="#9aa5a8" xml:space="preserve">{SUBLINE}</text>
  {"".join(chips)}
  <text x="1127" y="556" text-anchor="end" font-family="{MONO}" font-size="26" fill="#8b9699">{HOST}</text>"""


def kaggle_cover():
    return 1200, 400, f"""
  <rect width="1200" height="400" fill="{BG}"/>
  {grid(695, 1130, 65, 345, 70)}
  <rect width="1200" height="4" fill="{BAR}"/>
  <g transform="translate(12.6 -1.1) scale(0.81)">{logo()}</g>
  <text x="74" y="252" font-family="{SANS}" font-size="37" font-weight="600" fill="#f4f7f8">{TITLE}</text>
  <text x="74" y="286" font-family="{MONO}" font-size="22" fill="#9aa5a8" xml:space="preserve">{SUBLINE}</text>
  <text x="1127" y="327" text-anchor="end" font-family="{MONO}" font-size="22" fill="#8b9699">{HOST}</text>"""


def render(width, height, body, html_path, png_path, profile):
    html_path.write_text(
        "<!doctype html><meta charset='utf-8'><style>html,body{margin:0;background:" + BG + "}</style>"
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">{body}</svg>', encoding="utf-8")
    subprocess.run([str(EDGE), "--headless=new", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--disable-gpu", f"--user-data-dir={profile}", f"--window-size={width},{height}",
                    f"--screenshot={png_path}", html_path.as_uri()], check=True, capture_output=True)
    # msedge.exe hands off to a browser process and returns before the screenshot is written
    deadline, last = time.time() + 60, -1
    while time.time() < deadline:
        size = png_path.stat().st_size if png_path.exists() else -1
        if size > 0 and size == last:
            return
        last = size
        time.sleep(1)
    raise SystemExit(f"Edge wrote no screenshot to {png_path}")


def read_rgb(path):
    """RGB(A) 8-bit PNG -> HxWx3 array (Edge writes filter types 0-4)."""
    data = path.read_bytes()
    pos, idat = 8, b""
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", body[:10])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    assert depth == 8 and ctype in (2, 6), (depth, ctype)
    ch = 3 if ctype == 2 else 4
    raw, stride = zlib.decompress(idat), w * ch
    out = np.zeros((h, stride), np.uint8)
    prev = np.zeros(stride, np.int32)
    for y in range(h):
        f, line = raw[y * (stride + 1)], np.frombuffer(raw, np.uint8, stride, y * (stride + 1) + 1).astype(np.int32)
        if f in (0, 2):
            cur = line if f == 0 else (line + prev) & 255
        else:
            cur = np.zeros(stride, np.int32)
            for x in range(stride):
                a = cur[x - ch] if x >= ch else 0
                b, c = prev[x], (prev[x - ch] if x >= ch else 0)
                if f == 1:
                    p = a
                elif f == 3:
                    p = (a + b) // 2
                else:
                    pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                    p = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                cur[x] = (line[x] + p) & 255
        out[y], prev = cur, cur
    return out.reshape(h, w, ch)[:, :, :3]


def write_indexed(path, rgb, colors=256):
    """Median-cut to <=256 colours, nearest-colour mapping, indexed PNG at zlib level 9."""
    h, w, _ = rgb.shape
    px = rgb.reshape(-1, 3).astype(np.int32)
    uniq, inv = np.unique(px, axis=0, return_inverse=True)
    weights = np.bincount(inv.reshape(-1), minlength=len(uniq))
    boxes = [np.arange(len(uniq))]
    while len(boxes) < colors:
        spans = [(np.ptp(uniq[b], 0).max() if len(b) > 1 else -1) for b in boxes]
        i = int(np.argmax(spans))
        if spans[i] <= 0:
            break
        box = boxes.pop(i)
        c = int(np.ptp(uniq[box], 0).argmax())
        box = box[np.argsort(uniq[box, c], kind="stable")]
        cum = np.cumsum(weights[box])
        cut = int(np.clip(np.searchsorted(cum, cum[-1] / 2), 1, len(box) - 1))
        boxes += [box[:cut], box[cut:]]
    palette = np.array([np.average(uniq[b], 0, weights[b]) for b in boxes]).round().astype(np.int32)
    nearest = np.empty(len(uniq), np.int64)
    for s in range(0, len(uniq), 2048):
        nearest[s:s + 2048] = ((uniq[s:s + 2048, None] - palette[None]) ** 2).sum(-1).argmin(1)
    index = nearest[inv.reshape(-1)].reshape(h, w).astype(np.uint8)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    raw = b"".join(b"\x00" + row.tobytes() for row in index)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0))
                     + chunk(b"PLTE", palette.astype(np.uint8).tobytes())
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--keep", action="store_true", help="keep the intermediate files in .cards-build/")
    args = ap.parse_args()
    build = Path(tempfile.mkdtemp(prefix="suppdb-cards-"))
    try:
        for name, (w, h, body), target in [("og", og_card(), ROOT / "og-image-v2.png"),
                                           ("kaggle", kaggle_cover(), ROOT / "assets" / "kaggle-cover.png")]:
            shot = build / f"{name}.png"
            render(w, h, body, build / f"{name}.html", shot, build / "profile")
            rgb = read_rgb(shot)
            assert rgb.shape[:2] == (h, w), (name, rgb.shape)
            write_indexed(target, rgb)
            print(f"{target.relative_to(ROOT).as_posix()}: {w}x{h}, {target.stat().st_size:,} bytes")
        if args.keep:
            keep = ROOT / ".cards-build"
            shutil.rmtree(keep, ignore_errors=True)
            shutil.copytree(build, keep, ignore=shutil.ignore_patterns("profile"))
    finally:
        shutil.rmtree(build, ignore_errors=True)


if __name__ == "__main__":
    main()
