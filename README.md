# hflic-posts

Instagram posts for [@hflic.hebron](https://www.instagram.com/hflic.hebron/), the Hebron Financial Literacy and Investment Club.

- `posts/<date>-<slug>/` holds each post's slides (`slide-1.jpg` to `slide-5.jpg`) and `caption.txt`.
- `plans/<week>.json` is the week's plan that the slides are rendered from.
- `tools/render.py` turns a plan into slides.

Posts go live only after they're approved.

## Reels

- `posts/<date>-<slug>/reel.json` is a reel's script and scene list; `reel.mp4`, `cover.jpg` and `caption.txt` sit next to it.
- `tools/reel.py SPEC.json OUT_DIR` makes the reel (animated scenes, two free Kokoro AI voices, word-timed captions). Add `--stills` to check key frames first. The docstring explains every scene layout.
- Run `tools/setup.sh` once on a new machine to install the fonts and download the voice model.
