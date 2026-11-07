"""Render HFLIC Instagram carousel slides from a posts.json file.

Usage: python3 render.py <posts.json> <out_dir>
Writes <out_dir>/<post id>/slide-<n>.jpg at 1080x1350 (4:5), JPEG.
Needs the fonts: npm install @fontsource/dm-serif-display @fontsource/inter
(run in the folder that holds this script, or set HFLIC_FONTS to the @fontsource folder).

Slide types:
  cover: kicker, title, sub, optional badge (e.g. "Ranked by Claude")
  text:  heading, optional big, body (list of short paragraphs), optional source
  list:  heading, optional intro, items [[label, value], ...], optional stacked, note, source
  chart: heading, optional intro, items [[label, number, shown_value], ...] (horizontal bars), optional note, source
  end:   takeaway
"""
import html
import json
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.environ.get("HFLIC_FONTS", os.path.join(HERE, "node_modules", "@fontsource"))

NAVY = "#07090F"
NAVY_2 = "#101B30"
CREAM = "#F4F6F9"
INK = "#07090F"
MINT = "#74AA80"
GREEN_DARK = "#2F6A85"
MUTED_DARK = "#8FA3B8"
MUTED_LIGHT = "#5B6575"
RULE_LIGHT = "#D8DEE6"
FILL_DARK = "linear-gradient(90deg, #74AA80, #558CA7)"  # CSS background (e.g. a gradient) for accents on dark slides
FILL_LIGHT = "linear-gradient(90deg, #74AA80, #558CA7)"  # same for bars on light slides
THEME_KEYS = ("FILL_DARK", "FILL_LIGHT", "NAVY", "NAVY_2", "CREAM", "INK", "MINT", "GREEN_DARK", "MUTED_DARK", "MUTED_LIGHT", "RULE_LIGHT")

def build_css():
    fd = FILL_DARK or MINT
    fl = FILL_LIGHT or GREEN_DARK
    return f"""
@font-face {{ font-family: 'Serif'; src: url('file://{FONTS}/dm-serif-display/files/dm-serif-display-latin-400-normal.woff2'); }}
@font-face {{ font-family: 'Sans'; font-weight: 400; src: url('file://{FONTS}/inter/files/inter-latin-400-normal.woff2'); }}
@font-face {{ font-family: 'Sans'; font-weight: 600; src: url('file://{FONTS}/inter/files/inter-latin-600-normal.woff2'); }}
@font-face {{ font-family: 'Sans'; font-weight: 700; src: url('file://{FONTS}/inter/files/inter-latin-700-normal.woff2'); }}
@font-face {{ font-family: 'Sans'; font-weight: 800; src: url('file://{FONTS}/inter/files/inter-latin-800-normal.woff2'); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 1080px; height: 1350px; }}
body {{ font-family: 'Sans', sans-serif; -webkit-font-smoothing: antialiased; }}
.slide {{ width: 1080px; height: 1350px; padding: 88px 92px; display: flex; flex-direction: column; position: relative; overflow: hidden; }}
.dark {{ background: {NAVY}; color: {CREAM}; }}
.light {{ background: {CREAM}; color: {INK}; }}
.top {{ display: flex; justify-content: space-between; align-items: center; font-weight: 800; font-size: 30px; letter-spacing: 0.18em; }}
.top .num {{ font-weight: 600; letter-spacing: 0.04em; font-size: 28px; }}
.dark .top .num {{ color: {MUTED_DARK}; }}
.light .top .num {{ color: {MUTED_LIGHT}; }}
.mark span {{ color: {MINT}; }}
.light .mark span {{ color: {GREEN_DARK}; }}
.top, .body, .foot {{ position: relative; z-index: 1; }}
.body {{ flex: 1; display: flex; flex-direction: column; justify-content: center; }}
.foot {{ display: flex; justify-content: space-between; align-items: center; font-size: 28px; font-weight: 600; }}
.dark .foot {{ color: {MUTED_DARK}; }}
.light .foot {{ color: {MUTED_LIGHT}; }}
.kicker {{ font-size: 30px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: {MINT}; margin-bottom: 40px; }}
.title {{ font-family: 'Serif', serif; font-size: 112px; line-height: 1.04; letter-spacing: -0.01em; }}
.sub {{ font-size: 40px; line-height: 1.35; margin-top: 44px; color: {MUTED_DARK}; max-width: 820px; }}
.bar {{ width: 120px; height: 10px; background: {fd}; border-radius: 6px; margin-bottom: 52px; }}
.swipe {{ color: {MINT}; }}
.heading {{ font-family: 'Serif', serif; font-size: 86px; line-height: 1.08; margin-bottom: 48px; }}
.big {{ font-family: 'Serif', serif; font-size: 72px; line-height: 1.12; color: {GREEN_DARK}; margin-bottom: 44px; }}
.p {{ font-size: 44px; line-height: 1.45; margin-bottom: 24px; max-width: 880px; }}
.intro {{ font-size: 40px; line-height: 1.4; margin-bottom: 28px; color: {MUTED_LIGHT}; }}
.rows {{ border-top: 3px solid {INK}; }}
.row {{ display: flex; justify-content: space-between; align-items: baseline; gap: 40px; padding: 30px 0; border-bottom: 2px solid {RULE_LIGHT}; }}
.row .l {{ font-size: 44px; font-weight: 600; }}
.row .v {{ font-size: 44px; font-weight: 700; color: {GREEN_DARK}; text-align: right; }}
.row.stack {{ display: block; padding: 32px 0; }}
.row.stack .l {{ font-family: 'Serif', serif; font-weight: 400; font-size: 60px; display: block; margin-bottom: 8px; }}
.row.stack .v {{ font-size: 40px; font-weight: 400; color: {MUTED_LIGHT}; text-align: left; display: block; line-height: 1.4; }}
.note {{ font-size: 35px; line-height: 1.45; margin-top: 36px; color: {MUTED_LIGHT}; max-width: 880px; }}
.take {{ font-family: 'Serif', serif; font-size: 92px; line-height: 1.1; }}
.follow {{ margin-top: 64px; display: inline-flex; align-self: flex-start; background: {fd}; color: {NAVY}; font-weight: 800; font-size: 36px; padding: 24px 40px; border-radius: 60px; }}
.follow-sub {{ font-size: 32px; margin-top: 22px; color: {MUTED_DARK}; }}
.disc {{ font-size: 26px; color: {MUTED_DARK}; }}
.badge {{ display: inline-flex; align-self: flex-start; border: 2px solid {MINT}; color: {MINT}; font-size: 28px; font-weight: 700; letter-spacing: 0.06em; padding: 10px 22px; border-radius: 40px; margin-bottom: 36px; }}
.chart {{ display: flex; flex-direction: column; gap: 26px; border-top: 3px solid {INK}; padding-top: 34px; }}
.bar-row .bl {{ display: flex; justify-content: space-between; align-items: baseline; gap: 24px; font-size: 38px; font-weight: 600; margin-bottom: 10px; }}
.bar-row .bl .bv {{ color: {GREEN_DARK}; font-weight: 700; white-space: nowrap; }}
.bar-track {{ height: 26px; background: {RULE_LIGHT}; border-radius: 14px; overflow: hidden; }}
.bar-fill {{ height: 100%; background: {fl}; border-radius: 14px; }}
.source {{ font-size: 28px; line-height: 1.4; color: {MUTED_LIGHT}; margin-top: 30px; }}
.glow {{ position: absolute; width: 760px; height: 760px; border-radius: 50%; right: -260px; top: -240px; background: radial-gradient(circle, {NAVY_2} 0%, transparent 70%); }}
"""


def esc(t):
    return html.escape(t)


def top(n, total):
    return f'<div class="top"><div class="mark">HFLIC<span>.</span></div><div class="num">{n}/{total}</div></div>'


def slide_html(s, n, total, handle):
    t = s["type"]
    if t == "cover":
        badge = f'<div class="badge">{esc(s["badge"])}</div>' if s.get("badge") else ""
        inner = (
            f'<div class="glow"></div>{top(n, total)}'
            f'<div class="body">{badge}<div class="kicker">{esc(s["kicker"])}</div>'
            f'<div class="title">{esc(s["title"])}</div>'
            f'<div class="sub">{esc(s["sub"])}</div></div>'
            f'<div class="foot"><div>{esc(handle)}</div><div class="swipe">Swipe</div></div>'
        )
        return f'<div class="slide dark">{inner}</div>'
    if t == "end":
        inner = (
            f'<div class="glow"></div>{top(n, total)}'
            f'<div class="body"><div class="bar"></div><div class="take">{esc(s["takeaway"])}</div>'
            f'<div class="follow">Follow {esc(handle)}</div>'
            f'<div class="follow-sub">A new money lesson every day</div></div>'
            f'<div class="foot"><div class="disc">Education only. Not financial advice.</div></div>'
        )
        return f'<div class="slide dark">{inner}</div>'
    parts = [top(n, total), '<div class="body">', f'<div class="heading">{esc(s["heading"])}</div>']
    if t == "text":
        if s.get("big"):
            parts.append(f'<div class="big">{esc(s["big"])}</div>')
        for p in s.get("body", []):
            parts.append(f'<div class="p">{esc(p)}</div>')
    elif t == "list":
        if s.get("intro"):
            parts.append(f'<div class="intro">{esc(s["intro"])}</div>')
        cls = "row stack" if s.get("stacked") else "row"
        parts.append('<div class="rows">')
        for label, value in s["items"]:
            parts.append(f'<div class="{cls}"><span class="l">{esc(label)}</span><span class="v">{esc(value)}</span></div>')
        parts.append("</div>")
        if s.get("note"):
            parts.append(f'<div class="note">{esc(s["note"])}</div>')
    elif t == "chart":
        if s.get("intro"):
            parts.append(f'<div class="intro">{esc(s["intro"])}</div>')
        top_val = max(float(it[1]) for it in s["items"]) or 1
        parts.append('<div class="chart">')
        for label, val, shown in s["items"]:
            pct = max(4, round(100 * float(val) / top_val))
            parts.append(f'<div class="bar-row"><div class="bl"><span>{esc(label)}</span><span class="bv">{esc(shown)}</span></div><div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div></div>')
        parts.append("</div>")
        if s.get("note"):
            parts.append(f'<div class="note">{esc(s["note"])}</div>')
    if s.get("source"):
        parts.append(f'<div class="source">{esc(s["source"])}</div>')
    parts.append("</div>")
    parts.append(f'<div class="foot"><div>{esc(handle)}</div><div></div></div>')
    return f'<div class="slide light">{"".join(parts)}</div>'


def main():
    src, out = sys.argv[1], os.path.abspath(sys.argv[2])
    data = json.load(open(src))
    handle = data.get("handle", "@hflic.hebron")
    # Optional "theme": {"NAVY": "#..", "MINT": "#..", ...} overrides the default palette.
    for k, v in (data.get("theme") or {}).items():
        if k in THEME_KEYS:
            globals()[k] = v
    css = build_css()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--allow-file-access-from-files"])
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for post in data["posts"]:
            if not post.get("slides"):
                print("skipped (no slides, e.g. a reel):", post.get("id"))
                continue
            d = os.path.join(out, post["id"])
            os.makedirs(d, exist_ok=True)
            total = len(post["slides"])
            for i, s in enumerate(post["slides"], 1):
                doc = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{slide_html(s, i, total, handle)}</body></html>"
                tmp = os.path.join(d, f"slide-{i}.html")
                open(tmp, "w").write(doc)
                page.goto(f"file://{tmp}")
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(150)
                overflow = page.evaluate("(() => { const s = document.querySelector('.slide'); const b = s.querySelector('.body'); return b.scrollHeight > b.clientHeight + 2; })()")
                if overflow:
                    print(f"WARNING overflow: {post['id']} slide {i}")
                page.screenshot(path=os.path.join(d, f"slide-{i}.jpg"), type="jpeg", quality=92)
                os.remove(tmp)
            print("rendered", post["id"], total, "slides")
        browser.close()


if __name__ == "__main__":
    main()
