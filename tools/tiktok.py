#!/usr/bin/env python3
"""Make TikTok versions (9:16, 1080x1920) of a carousel's slides.

Usage: python3 tools/tiktok.py posts/<date>-<slug> [more folders...]
Reads <folder>/slide-1.jpg ... and writes <folder>/tiktok/slide-1.jpg ... at 1080x1920.
Each 1080x1350 slide is centered and its own top and bottom rows are stretched to fill the
extra space, so the background continues seamlessly and TikTok's on-screen buttons and
caption don't cover the content.
"""
import glob
import os
import sys

from PIL import Image

W, H = 1080, 1920


def tall(src, dst):
    im = Image.open(src).convert("RGB")
    if im.width != W:
        im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    pad = H - im.height
    top, bottom = pad // 2, pad - pad // 2
    out = Image.new("RGB", (W, H))
    if top:
        out.paste(im.crop((0, 0, W, 1)).resize((W, top)), (0, 0))
    out.paste(im, (0, top))
    if bottom:
        out.paste(im.crop((0, im.height - 1, W, im.height)).resize((W, bottom)), (0, top + im.height))
    out.save(dst, "JPEG", quality=92)


def main():
    for folder in sys.argv[1:]:
        slides = sorted(glob.glob(os.path.join(folder, "slide-*.jpg")))
        if not slides:
            print("no slides in", folder)
            continue
        os.makedirs(os.path.join(folder, "tiktok"), exist_ok=True)
        for s in slides:
            tall(s, os.path.join(folder, "tiktok", os.path.basename(s)))
        print("tiktok slides:", folder, len(slides))


if __name__ == "__main__":
    main()
