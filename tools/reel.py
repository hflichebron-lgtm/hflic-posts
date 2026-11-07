#!/usr/bin/env python3
"""Make an HFLIC reel: a 1080x1920 MP4 with animated scenes, two AI voices and word-timed captions.

Usage:
  python3 tools/reel.py SPEC.json OUT_DIR             full render: OUT_DIR/reel.mp4 and OUT_DIR/cover.jpg
  python3 tools/reel.py SPEC.json OUT_DIR --stills    key frames + contact sheet only (fast check before a full render)

Run tools/setup.sh once first (fonts, kokoro-onnx, voice model files in tools/models).

Spec (JSON):
{
  "handle": "@hflic.hebron",
  "theme": {...optional, same keys as plans' "theme"; defaults to the current HFLIC brand...},
  "speed": 1.15,                                  # voice speed (default 1.15)
  "scenes": [ {"layout": "...", ...layout fields..., "lines": [{"voice": "heart"|"michael", "say": "spoken text", "show": "caption text"}]} ]
}
Every scene has "lines": what is spoken during it ("say") and the matching on-screen caption ("show", defaults to "say").
Write numbers in "say" as words (e.g. "one hundred five thousand") and in "show" as digits ("$105,000").
Layouts and their fields:
  hook  : kicker, title, highlight (part of title in gradient), sub (or sub_html with <b> for emphasis), badge
  rank  : rank, title, value (number), label, max (bar scale), ref, ref_label, chip, progress (how many progress pips are lit)
  stat  : kicker, value, prefix, suffix, decimals, label, note, source
  bars  : heading, items [[label, value, shown]], max, ref, ref_label, source
  text  : heading, items [lines], numbered (bool), source
  cta   : takeaway, follow, sub, source
Optional "cues": {"title": "word", "value": "word", "sub": "word", "chip": "word", "note": "word", "follow": "word"}
  times an element to when that caption word is spoken. Defaults: rank value = first word with "$", hook sub = start of line 2.
  text scenes take "items": ["word", "word", ...], one caption word per item, to reveal each line as it is spoken.
Top-level "progress_total": number of progress pips shown on scenes that set "progress".
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.environ.get("HFLIC_FONTS", os.path.join(HERE, "node_modules", "@fontsource"))
MODELS = os.environ.get("HFLIC_MODELS", os.path.join(HERE, "models"))
W, H, FPS = 1080, 1920, 30
SR = 24000
VOICES = {"heart": "af_heart", "michael": "am_michael"}
DEFAULT_THEME = {"NAVY": "#07090F", "NAVY_2": "#101B30", "CREAM": "#F4F6F9", "MINT": "#74AA80",
                 "MUTED_DARK": "#8FA3B8", "FILL_DARK": "linear-gradient(90deg, #74AA80, #558CA7)"}
LINE_GAP, LEAD_FIRST, LEAD, TAIL, TAIL_LAST = 0.15, 0.1, 0.2, 0.35, 1.2


def theme_vars(theme):
    t = dict(DEFAULT_THEME)
    t.update({k: v for k, v in (theme or {}).items() if v})
    fill = t.get("FILL_DARK") or f"linear-gradient(90deg, {t['MINT']}, {t['MINT']})"
    m = re.findall(r"#[0-9A-Fa-f]{6}", fill)
    glow2 = (m[-1] if m else t["MINT"]) + "22"
    return (f"--bg:{t['NAVY']};--glow:{t['NAVY_2']};--glow2:{glow2};--text:{t['CREAM']};"
            f"--accent:{t['MINT']};--muted:{t['MUTED_DARK']};--fill:{fill};")


def tts(spec):
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.int8.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    speed = spec.get("speed", 1.15)
    for sc in spec["scenes"]:
        for ln in sc["lines"]:
            v = VOICES.get(ln.get("voice", "heart"), ln.get("voice", "af_heart"))
            a, sr = k.create(ln["say"], voice=v, speed=speed, lang="en-us")
            assert sr == SR, sr
            a = np.asarray(a, dtype=np.float32)
            thr = 0.02 * float(np.max(np.abs(a)) or 1)
            idx = np.where(np.abs(a) > thr)[0]
            s0, s1 = (max(0, idx[0] - int(0.03 * SR)), min(len(a), idx[-1] + int(0.06 * SR))) if len(idx) else (0, len(a))
            ln["_audio"] = a[s0:s1]
            print(f"  voice {ln.get('voice')}: {len(ln['_audio']) / SR:.2f}s  {ln['say'][:60]}")


def weight(tok):
    core = tok.strip()
    w = 0.0
    if re.search(r"\d", core):
        groups = re.findall(r"\d+", core)
        if core.startswith("#"):
            w = 11
        elif re.fullmatch(r"\d+x", core):
            w = 11
        else:
            w = sum(4 + 9 * max(1, (len(g) + 2) // 3) for g in groups) + (3 if "%" in core else 0)
            w += len(re.sub(r"[\d$,.%#\-]", "", core))
    elif core.startswith("@"):
        w = 8
    else:
        w = len(re.sub(r"[^A-Za-z']", "", core)) + 1.5
    if re.search(r"[.?!]$", core):
        w += 6
    elif re.search(r"[,:;]$", core):
        w += 3.5
    return max(w, 2)


def build_timeline(spec):
    t = 0.0
    words_all = []
    audio = []
    for si, sc in enumerate(spec["scenes"]):
        sc["start"] = round(t, 4)
        lt = LEAD_FIRST if si == 0 else LEAD
        sc["_words"], sc["_line_starts"] = [], []
        for ln in sc["lines"]:
            a = ln["_audio"]
            dur = len(a) / SR
            start = sc["start"] + lt
            audio.append((start, a))
            sc["_line_starts"].append(lt)
            toks = (ln.get("show") or ln["say"]).split()
            ws = [weight(x) for x in toks]
            total = sum(ws)
            cur = start + 0.02
            span = dur - 0.08
            for tok, wv in zip(toks, ws):
                d = span * wv / total
                wd = {"w": tok, "t0": round(cur, 3), "t1": round(cur + d * 0.92, 3), "scene": si}
                words_all.append(wd)
                sc["_words"].append(wd)
                cur += d
            lt += dur + LINE_GAP
        last = si == len(spec["scenes"]) - 1
        sc["dur"] = round(lt - LINE_GAP + (TAIL_LAST if last else TAIL), 4)
        sc["last"] = last
        t = sc["start"] + sc["dur"]
    total = t
    # cues: local times for elements
    for sc in spec["scenes"]:
        cues = {}
        def find(txt):
            for w in sc["_words"]:
                if txt.lower() in w["w"].lower():
                    return round(w["t0"] - sc["start"], 3)
            return None
        for key, txt in (sc.get("cues") or {}).items():
            if isinstance(txt, list):  # e.g. "items": ["word for item 1", "word for item 2", ...]
                vals = [find(x) for x in txt]
                if all(v is not None for v in vals):
                    cues[key] = vals
                continue
            v = find(txt)
            if v is not None:
                cues[key] = v
        if sc["layout"] == "rank":
            cues.setdefault("value", find("$"))
            if len(sc["_words"]) > 1:
                cues.setdefault("title", round(sc["_words"][1]["t0"] - sc["start"], 3))
        if sc["layout"] in ("stat",):
            v = find("$") or find("%")
            if v is not None:
                cues.setdefault("value", v)
        if sc["layout"] == "hook" and len(sc["_line_starts"]) > 1:
            cues.setdefault("sub", round(sc["_line_starts"][1], 3))
        if sc["layout"] == "cta":
            v = find("follow") or find("@")
            if v is not None:
                cues.setdefault("follow", v)
        sc["cues"] = {k: v for k, v in cues.items() if v is not None}
    # caption chunks
    chunks, cur = [], []
    for w in words_all:
        if cur:
            size = sum(len(x["w"]) + 1 for x in cur) + len(w["w"])
            hard = cur[-1]["scene"] != w["scene"] or re.search(r"[.?!]$", cur[-1]["w"]) or (re.search(r"[,:;]$", cur[-1]["w"]) and len(cur) >= 3)
            full = len(cur) >= 5 or size > 28
            # don't strand the last word of a sentence on its own
            if full and not hard and re.search(r"[.?!]$", w["w"]) and len(cur) < 6 and size <= 40:
                full = False
            if hard or full:
                chunks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        sc = spec["scenes"][c[0]["scene"]]
        nxt = chunks[i + 1][0]["t0"] if i + 1 < len(chunks) else total
        until = min(nxt - 0.06, c[-1]["t1"] + 0.5, sc["start"] + sc["dur"] - 0.05)
        out.append({"t0": c[0]["t0"], "until": round(max(until, c[-1]["t1"]), 3),
                    "words": [{"w": x["w"], "t0": x["t0"], "t1": x["t1"]} for x in c]})
    # narration track
    n = int(round(total * FPS)) / FPS
    track = np.zeros(int(n * SR) + SR, dtype=np.float32)
    for start, a in audio:
        i = int(start * SR)
        track[i:i + len(a)] += a[: max(0, len(track) - i)]
    track = track[: int(n * SR)]
    peak = float(np.max(np.abs(track)) or 1)
    track = track * (0.89 / peak)
    return n, out, track


def page_data(spec, chunks):
    keep = ("layout", "start", "dur", "last", "cues", "kicker", "title", "highlight", "sub", "sub_html", "badge", "rank",
            "value", "label", "max", "ref", "ref_label", "chip", "progress", "prefix", "suffix", "decimals", "note",
            "source", "heading", "items", "numbered", "takeaway", "follow")
    scenes = [{k: sc[k] for k in keep if k in sc} for sc in spec["scenes"]]
    return {"handle": spec.get("handle", "@hflic.hebron"), "progress_total": spec.get("progress_total", 0),
            "scenes": scenes, "chunks": chunks}


def open_page(p, html_path):
    browser = p.chromium.launch(executable_path=shutil.which("google-chrome") or None, args=["--allow-file-access-from-files"])
    page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    page.goto("file://" + html_path)
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(300)
    return browser, page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    spec = json.load(open(a.spec))
    text = json.dumps(spec, ensure_ascii=False)
    if "—" in text or "–" in text:
        sys.exit("Spec contains an em dash or en dash. Replace it before rendering.")
    print("Generating voices...")
    tts(spec)
    total, chunks, track = build_timeline(spec)
    print(f"Total length: {total:.2f}s, {len(spec['scenes'])} scenes, {len(chunks)} caption chunks")
    html = open(os.path.join(HERE, "reel_template.html")).read()
    html = html.replace("__FONTS__", FONTS).replace("__THEME_VARS__", theme_vars(spec.get("theme")))
    html = html.replace("<script>", "<script>window.REEL = " + json.dumps(page_data(spec, chunks)) + ";\n", 1)
    html_path = os.path.join(out, "_reel.html")
    open(html_path, "w").write(html)
    sf.write(os.path.join(out, "narration.wav"), track, SR)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser, page = open_page(p, html_path)
        # cover: end of the first scene, no captions
        sc0 = spec["scenes"][0]
        page.evaluate(f"render({sc0['start'] + sc0['dur'] - 0.25}, {{noCaptions: true}})")
        page.screenshot(path=os.path.join(out, "cover.jpg"), type="jpeg", quality=92)
        if a.stills:
            from PIL import Image
            shots = []
            for i, sc in enumerate(spec["scenes"]):
                c = [x for v in sc.get("cues", {}).values() for x in (v if isinstance(v, list) else [v])]
                lt = min(sc["dur"] - 0.2, max(c) + 1.0 if c else 2.2)
                tt = sc["start"] + lt
                fp = os.path.join(out, f"still-{i + 1:02d}.jpg")
                page.evaluate(f"render({tt})")
                page.screenshot(path=fp, type="jpeg", quality=92)
                shots.append(fp)
            ims = [Image.open(f).resize((360, 640)) for f in shots]
            sheet = Image.new("RGB", (370 * len(ims) - 10, 640), "white")
            for i, im in enumerate(ims):
                sheet.paste(im, (i * 370, 0))
            sheet.save(os.path.join(out, "stills-sheet.jpg"), quality=90)
            print("Stills written:", len(shots))
            browser.close()
            return
        # one encoded file per scene
        files = []
        frame0 = 0
        for i, sc in enumerate(spec["scenes"]):
            frame1 = int(round((sc["start"] + sc["dur"]) * FPS))
            if i == len(spec["scenes"]) - 1:
                frame1 = int(round(total * FPS))
            final = os.path.join(out, f"scene-{i + 1:02d}.mp4")
            tmp = os.path.join(out, f"scene-{i + 1:02d}.part.mp4")
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
                   "-g", "60", "-profile:v", "high", tmp]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            for f in range(frame0, frame1):
                page.evaluate(f"render({f / FPS})")
                proc.stdin.write(page.screenshot(type="jpeg", quality=92))
            proc.stdin.close()
            if proc.wait() != 0:
                sys.exit(f"ffmpeg failed on scene {i + 1}")
            os.replace(tmp, final)
            files.append(final)
            print(f"  scene {i + 1}: {(frame1 - frame0) / FPS:.2f}s")
            frame0 = frame1
        browser.close()
    lst = os.path.join(out, "scenes.txt")
    open(lst, "w").write("".join(f"file '{f}'\n" for f in files))
    video = os.path.join(out, "video.part.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video], check=True)
    final = os.path.join(out, "reel.part.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", os.path.join(out, "narration.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                    "-shortest", "-movflags", "+faststart", final], check=True)
    os.replace(final, os.path.join(out, "reel.mp4"))
    os.remove(video)
    print("Done:", os.path.join(out, "reel.mp4"))


if __name__ == "__main__":
    main()
