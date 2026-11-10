# HFLIC nightly content run

Set up 2026-11-09. This file is the instruction set for the nightly run that makes tomorrow's two Instagram posts. The run happens in Tommy's HFLIC chat (the Claude session that has push access to this repo), triggered by a scheduled reminder each evening. Scheduled cloud tasks can't push to GitHub on their own, which is why content is made here and the cloud tasks only post.

## The schedule (Instagram only, America/Chicago)
- 7:00 AM: one slideshow (carousel). Cloud task "HFLIC 7 AM slideshow" posts it automatically at about 6:51 AM.
- 9:00 AM: one reel (two AI voices). Cloud task "HFLIC 9 AM reel" posts it automatically at about 8:51 AM unless Tommy asked for changes ("Changes requested") or said skip ("Skipped").
- Every evening at about 6:37 PM: this run makes tomorrow's two posts, uploads them, queues them, and sends Tommy the reel to look at.
- The slideshow and the reel are on different topics, from different topic ranges.

## Step 0: keep the chain going (do this first, every run)
1. With list_triggers (include_completed false), check for a pending one-shot reminder named "HFLIC nightly content run" set for tomorrow. If there isn't one, create it with send_later: at = tomorrow 18:37 [America/Chicago], name "HFLIC nightly content run", initiation "human_schedule", message exactly: "HFLIC nightly content run: follow playbook/daily-run.md in /home/claude/hflic-posts (clone https://github.com/hflichebron-lgtm/hflic-posts there first if it's missing). Make tomorrow's 7 AM slideshow and 9 AM reel."
2. Never create two reminders for the same evening.

## Step 1: set up
- cd /home/claude/hflic-posts (if missing: git clone https://github.com/hflichebron-lgtm/hflic-posts /home/claude/hflic-posts), then git pull --rebase origin main.
- If python3 -c "import kokoro_onnx, playwright" fails or fonts/model files are missing, run bash tools/setup.sh. Check ffmpeg -version.

## Step 2: what's queued and what's working
1. Read 'Posts'!A:N of the Google Sheet "HFLIC Post Queue" (id 10liXCmnyPIbGicgA8i76kcRpEIpV3AcPzm9GaLJZAw8). Columns: A Date | B Day | C Type | D Topic (topic range) | E Post title | F Folder | G Status | H Posted at | I Instagram post ID | J Caption | K Slot ("7:00 AM" or "9:00 AM") | L (unused) | M Sources | N Recheck.
2. Tomorrow's rows: make only the slots that have no row yet (or whose row is "Failed" because files weren't uploaded; redo those in place).
3. Also check today's rows: if one is "Failed" or missing and its time hasn't passed by much, tell Tommy in the final message.
4. Read playbook/research-guide.md (Tommy's standing brief: 13 topic ranges, sources, per-post checks, formats) and playbook/social-playbook.md (monthly playbook and topic calendar; ignore TikTok).
5. Instagram results: get_data, connector "instagram", fields ["media_id", "media_permalink", "media_type", "media_reach", "media_like_count", "media_saved", "media_shares", "media_comments_count", "timestamp"], date_preset "last_30d" (no force_refresh). Lean toward what gets reach, saves and shares.

## Step 3: pick and research
- Each post answers one focused question for 17 to 18-year-old U.S. students, from one of the guide's 13 topic ranges (put the range name in Topic). The two posts use different ranges. Use no range more than twice in 7 days, and don't repeat a title or core idea from the last 8 weeks of the sheet.
- Finance, business or tech only, with 2026 or late-2025 data. Use the playbook's calendar when it fits. Never build a post on data that hasn't been released yet when the run happens.
- Follow the guide's research checks: official and original sources first (BLS, IRS, SSA, CFPB, FTC, FDIC, Federal Student Aid, Fed, BEA, CBO, SEC EDGAR, company IR pages), check dates and definitions, state ranking criteria, separate facts from forecasts, stay nonpartisan on policy (proposed vs enacted, effective dates), verify every calculation in Python, label hypothetical examples, returns are never guaranteed.
- Every number on a slide, in a reel line or in a caption must come from a source you recorded. If you can't source it, cut it.
- Write anything that could change before posting time into Recheck.

## Step 4: make the posts
Slideshow (7 AM): alternate between a Lesson (exactly 5 slides: cover, 3 text slides, end) and a Top list (Top 3 or 4: cover with criteria, one text slide per item with heading "#1 <name>", big numbers and 2 short paragraphs, then a chart slide when there are numbers, then end; 6 to 8 slides). Write plans/<tomorrow>.json as {"date", "handle": "@hflic.hebron", "posts": [{"id", "date", "day", "slot": "7:00 AM", "type", "topic", "format", "folder": "posts/<date>-<slug>", "slides": [...], "caption", "sources": [{"title", "publisher", "url", "date"}], "recheck"}]}, no "theme". Render with python3 tools/render.py plans/<tomorrow>.json <scratch>/slides, fix any overflow warning, then look at a contact sheet of all slides and fix anything cramped or badly wrapped.

Reel (9 AM): write posts/<date>-<slug>/reel.json (copy "theme" from posts/2026-11-08-costco-membership/reel.json; "speed": 1.15; "sources"; "recheck"; 6 to 9 scenes using hook, rank, stat, bars, text, cta; lines under about 15 words; alternate voices "heart" and "michael"; in "say" write numbers as words and "H Flick", in "show" use digits and "HFLIC"; data source on screen; end with a cta scene with a takeaway, "Follow H Flick for more..." and a share prompt). Good models: posts/2026-11-10-first-paycheck/reel.json, posts/2026-11-08-teen-spending/reel.json, posts/2026-11-08-costco-membership/reel.json. Run python3 tools/reel.py <reel.json> <scratch>/reel --stills, look at stills-sheet.jpg and fix overflow or a word alone on a title line, then render without --stills. ffprobe: 1080x1920, audio, 30 to 60 seconds.

Captions: 2 or 3 short paragraphs, then "Follow @hflic.hebron for a new money lesson every day." (reel: "Follow @hflic.hebron for more money facts like this."), then "Education only, not financial advice." (plus "Returns are not guaranteed." on investing posts and a "Data: <source>." line when there are figures), then 5 hashtags including #financialliteracy. Save as caption.txt in each folder.

Style: concrete numbers and worked examples, plain short sentences, catchy but true hooks, no "not X, but Y", "here's the thing", "game-changer", "unlock". NEVER an em dash (U+2014) or en dash (U+2013) anywhere. Never tell viewers to buy a specific stock, fund, app or company. Current brand colors only (the renderer defaults).

Python checks before upload: no U+2014 or U+2013 in plan, reel.json or captions; slide counts right; 6 to 9 reel scenes; every post has a source URL; captions under 2,200 characters.

## Step 5: upload, verify, queue
1. Copy slide-1.jpg... into the slideshow folder, reel.mp4 and cover.jpg into the reel folder. git add, commit (end the message with the attribution lines), git pull --rebase origin main, git push origin HEAD:main.
2. git ls-remote origin refs/heads/main must equal git rev-parse HEAD. If not, fix and push again.
3. curl every new file at https://raw.githubusercontent.com/hflichebron-lgtm/hflic-posts/<commit>/<folder>/<file>: all 200, .jpg as image/jpeg.
4. Only then write the rows to the sheet (next empty rows, A to N): Date, Day, Type ("Lesson", "Top list" or "Reel"), Topic, Post title, Folder, "Planned", "", "", Caption (exact caption.txt text), Slot, "", Sources (one "Title, publisher, date: URL" per line), Recheck. Read the rows back.
5. If the upload can't be fixed, don't queue anything as Planned; tell Tommy plainly.

## Step 6: tell Tommy
SendUserFile the reel.mp4 (display "render", status "proactive", caption "Tomorrow 9 AM reel: <title>"), and the slideshow contact sheet (caption "Tomorrow 7 AM slideshow: <title>"). Then SendUserMessage: the two titles and times, the reel caption, and "Both post automatically. Reply 'change' with what to fix, or 'skip', before 8:45 AM." On Sundays add one line on last week's best post (reach, saves, shares).

## When Tommy replies
- Change request: set that row "Changes requested", fix the plan or reel.json and caption, re-render, re-check, upload and verify as in Step 5, update the row's Caption and Sources, send him the new version, then set it back to "Planned" (it posts at its normal time; if that time already passed, post it right away with the posting steps in the cloud task prompts: exact caption.txt, commit-pinned raw URLs, duplicate check first, then Status "Posted", time and post ID).
- Skip: set the row "Skipped".
- "Make today's posts" (or a cloud task said nothing was queued): make the missing posts for today, upload and queue them, and post any whose time has passed right away (same posting steps).

## On the 1st of each month
Before Step 2, refresh playbook/social-playbook.md (under about 1,000 words, Instagram only): what's working for HFLIC from the last 30 days of data, Instagram changes this month (official sources first), hooks and formats, student questions, a dated topic calendar across the 13 ranges marked Slideshow or Reel, newest verified data with release dates, things to avoid, and sources. Commit and push it.
