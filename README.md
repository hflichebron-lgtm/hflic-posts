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

## Daily schedule (Central time)

- 5:47 PM: the "HFLIC daily content" task makes tomorrow's 3 posts (plans/<date>.json for the carousels, posts/<date>-<slug>/reel.json for the reel), queues them in the "HFLIC Post Queue" sheet with a Slot, and sends the reel and the 2:30 PM post to Tommy to approve.
- 7:00 AM: the Lesson carousel posts automatically.
- 9:00 AM: the reel posts if its Status is "Approved".
- 2:30 PM: the Top 5 carousel posts if its Status is "Approved".

## TikTok

Posting to TikTok is manual for now. `tools/tiktok.py posts/<folder>` makes 9:16 versions of a carousel's slides in `posts/<folder>/tiktok/`. At each posting time, the posting task sends Tommy the TikTok version (slides or reel), the caption and a trending sound to add, and marks the sheet's "TikTok" column "Sent".
