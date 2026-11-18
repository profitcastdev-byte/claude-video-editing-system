# Effects Library

A catalogue of video effects to pull from when editing. Built from 6 reference reels (in `references/`), studied frame by frame on 2026-11-17.

**How to use this file:** effects are the vocabulary, not the edit. Pick 3–6 that serve the script; never stack them for their own sake. Every effect should land on a spoken word, a number, or a beat.

**"Build with" column:** the installed skill or tool that makes it.
- `effects` = the claude-video-effects skill (51 talking-head effects, face-tracked)
- `mm` = motionmaxxing
- `HF` = HyperFrames
- `RM` = Remotion
- `hgm` = Hadi Got Motion
- `ff` = ffmpeg
- `3js` = three.js skills
- `Mag` = Magnific (cutout, relight, background)

---


> **Reference reels.** The six source reels are other creators' videos, so they are not stored in this repo. Watch them at the
> links below, or run `yt-dlp <link>` into a local `references/` folder to study frame by frame. File names in the table
> (`…_<id>.mp4`) match the Instagram ids.
>
> | Creator | Reel | Id |
> |---|---|---|
> | Taki Wong (AI For Business) | https://www.instagram.com/reel/Det_44sBsPY/ | `Det_44sBsPY` |
> | Nick Saraev (SFX tips) | https://www.instagram.com/reel/De4XVvXPTWY/ | `De4XVvXPTWY` |
> | Justyn Berkovits | https://www.instagram.com/reel/DemQeuKsrOD/ | `DemQeuKsrOD` |
> | Justyn Berkovits | https://www.instagram.com/reel/Dfcr8TJMKCV/ | `Dfcr8TJMKCV` |
> | Marc Cleroux | https://www.instagram.com/reel/Def9pj5TWtA/ | `Def9pj5TWtA` |
> | Marc Cleroux | https://www.instagram.com/reel/Dff6wULz-i4/ | `Dff6wULz-i4` |
>
> **Adding a reel:** download it with yt-dlp, transcribe it with whisper word timings, build per-effect frame strips, then append the
> new effects here (deduplicated) with the reel id in "Seen in". Commit the text; never the video.

## Reference reels

| # | File | Creator | Length | What it is |
|---|---|---|---|---|
| R1 | `3877913714_Det_44sBsPY.mp4` | Taki Wong (@taki.gpt) | 60 s | 20 effects, one every 2 s, light room, orange accent |
| R2 | `80462658566_Def9pj5TWtA.mp4` | Marc Cleroux (@tenfoldmarc) | 27 s | 17 effects shown inside a phone he holds |
| R3 | `…_Dfcr8TJMKCV.mp4` | Justyn Berkovits (@justyn.ai) | 26 s | 20 effects, dark moody room, green panel. **Highest craft of the set.** |
| R4 | `…_De4XVvXPTWY.mp4` | Nick Saraev | 35 s | Tips: 3 free tools for sound effects |
| R5 | `…_DemQeuKsrOD.mp4` | Justyn Berkovits | 20 s | 18 more effects, mostly editor-UI and type |
| R6 | `…_Dff6wULz-i4.mp4` | Marc Cleroux | 35 s | 16 more effects, phone-in-hand again |

---

## 1. Camera moves and zooms

| Effect | What you see | Use it for | Build with | Seen in |
|---|---|---|---|---|
| **Snap zoom** | Hard 1.3–1.5× punch-in on a word, with a 2–3 frame motion blur on the way in | Emphasis on a key word | `ff` / RM, `effects:lean-in` | R1 8.4s |
| **Digital zoom** | Camcorder HUD (REC dot, corner brackets, timecode, "2.6×" readout) while it zooms deep into the face, then back to 1.0× | Funny "zoom in on this" moments | RM/HF overlay + `ff` | R1 36s, R2 |
| **Dolly zoom / Vertigo** | Face stays the same size while the room stretches away behind | A realisation or "wait, what?" beat | `effects:rabbit-hole`, `3js` | R1 25s, R2, R3 21s |
| **Zoom-through cut** | Push into the face until it blurs out, then cut to a new angle that's already zoomed | Hiding a jump cut, changing topic | `ff` | R1 31s, R2 |
| **Zoom portal** | Small circular inset of the face with an orange ring, pinned top-left while the main shot carries on | Reacting to yourself, picture-in-picture | RM/HF | R1 14.6s |
| **Pullback reveal** | Starts tight, pulls back to reveal a UI or scene around you | Revealing context or a result | RM/HF | R2 |
| **Rack focus** | Focus shifts between foreground and background layers (fake depth from a cutout) | Moving attention from you to text | `Mag` cutout + blur | R3 17s, R6 |
| **Slow push** | A slow cinematic push-in while the room melts out of focus | Emotional or serious lines | `effects:slow-push` | — |
| **Over-the-shoulder zoom** | Push into one corner, then a glass graph pops beside you | Showing data | `effects:over-the-shoulder-zoom` | — |

## 2. Frame and composition breaks

| Effect | What you see | Use it for | Build with | Seen in |
|---|---|---|---|---|
| **Frame escape** | The video shrinks into a tilted white-bordered photo on a dark background, and you (cut out) step out past its edge | Breaking the fourth wall | `Mag` cutout + HF | R1 6.4s |
| **Frame break** | Cracks spider across the screen, then the frame shatters into flying blue shards | Smashing a myth, "breaking" a rule | `3js` / HF | R1 34.5s, R2 |
| **Shatter 3D** | The frame breaks into 3D pieces that rotate | Big transitions | `3js` | R6 |
| **Phone mock-up** | The video sits inside an iPhone frame on a dark gradient | "This is what it looks like on your feed" | HF/RM, `effects:reel-frame` | R1 37.7s, R2 |
| **Chat takeover** | The video shrinks into a Claude/chat app window, a prompt types itself, and steps tick (✓ Cut the pauses ✓ Caption every word) | Showing AI or tool work | HF | R1 4.7s |
| **B-roll overlay** | The video sits inside a video-editor UI with an orange/blue timeline and a moving playhead | "Behind the scenes" of the edit | HF, `effects:timeline` | R1 20.7s |
| **Layer explode** | The frame splits into stacked 3D glass layers (video / captions / sound waveform / type) fanned in depth | Explaining how something is built | `3js` / HF | R3 12.9s |
| **Head stack / Clone row** | 3–5 copies of you side by side, or stacked above the head | "Do the work of 5 people" | `Mag` cutout + RM | R3 1.3s, R6 |
| **Blow away** | You dissolve into particles that drift off and leave an empty chair | Endings, "gone", disappearing problems | `3js` particles + `Mag` clean plate | R3 25s |
| **Depth scatter** | Elements scatter in 3D depth around you | Lists, many options | `3js` | R6 |
| **Blackout** | Everything goes black except you or a single word | Dramatic pause | `effects:spotlight`, `ff` | R6 |
| **Spotlight** | Room lights drop, you stay lit | Focus on one statement | `effects:spotlight` | R6 |

## 3. Background swaps (needs a person cutout)

| Effect | What you see | Use it for | Build with | Seen in |
|---|---|---|---|---|
| **Studio reveal** | The room goes dark, two softboxes and an orange "ON AIR" sign light up behind you | "Pro" upgrade moment | `Mag` cutout + HF | R1 18.6s |
| **Green screen** | Background flashes green, then becomes a city skyline at sunset | "Put yourself anywhere" | `Mag` remove-bg | R1 33s, R2 |
| **Paper cutout** | You get a thick white sticker border on a flat orange background with a black star, blue circle and dots | Playful, collage energy | `Mag` cutout + HF | R1 22.8s, R2 |
| **Magazine cover** | A masthead ("TAKIGPT") sits *behind* your head, with cover lines, a barcode and a "20 EFFECTS" roundel | Authority, "featured" | `effects:cover-star` | R1 27s, R2 |
| **Newspaper** | "The Daily Reel" broadsheet front page with you as the black-and-white lead photo | Announcements, big news | HF | R3 22.6s |
| **Bank note** | You engraved as the portrait on a green banknote while the number ticks 17 → 174,953 | Money, revenue, results | HF + engraving shader | R3 18.2s |
| **Impact frame** | Black-and-white manga ink portrait with radial speed lines and huge "IMPACT" text | The punchline hit | HF/shader | R3 20.2s |
| **Code body** | You re-rendered as ASCII/code characters (green-red), then resolve back | Tech, AI, "built with code" | HF canvas | R3 5.6s |
| **Doodle boil** | A hand-drawn marker outline "boils" (jitters) around you | Casual, creative | `effects:scribble` | R2 |
| **Film look** | A full colour grade switch (warm film stock, grain) | Mood shift | `ff` LUTs, `effects:moody` | R5 12.3s |

## 4. Typography

| Effect | What you see | Use it for | Build with | Seen in |
|---|---|---|---|---|
| **Kinetic hook** | A huge condensed sans title stacks word by word ("KINETIC / HOOK") over the opening | The first 2 seconds | HF/RM | R5 0s |
| **Gravity drop** | A small italic serif word, then giant letters drop in with weight and bounce | Title words | HF/mm | R5 1.2s |
| **Giant captions** | A white bold word on a dark green slab, with an italic serif word underneath | Key phrase | HF | R5 2.2s |
| **Letter dive** | A giant serif word fills a cream frame and the camera flies *through* the letters into the next shot | Section transitions | HF/3js | R3 7.7s |
| **Sketch words** | A pencil-sketch serif word draws itself on cream paper, with sketchy underlines | Ideas, plans | HF, `effects:crayon-write` | R3 13.8s |
| **Orbit / Orbit ring** | A serif text ring rotates in 3D around your head, passing behind and in front | Your name, a promise | HF + cutout, `effects:orbit` | R1 3.2s, R3 4.7s |
| **Headline storm / wall** | Many tilted headline banners pile up around and behind your head | Social proof, "everyone's talking" | `effects:headline-wall` | R1 12.6s, R2 |
| **Scene text** (depth text) | A big word sits *behind* you, so you occlude it ("STAND OUT") | The core message | `effects:backdrop-word` | R6 |
| **Type wall** | A wall of repeating giant words fills the background | The opening hook | HF | R6 0s |
| **Sticky text** | A tape or sticker label slaps on with a slight rotation | Callouts | `effects:tape-label` | R6 |
| **Serif flow** | Elegant italic serif lines fade and flow in on dark green | Calm statements | HF | R6 |
| **Glass type** | Words rendered as frosted or refractive glass | Premium feel | `effects:glass-widgets` | R2 |
| **Press font** | Letterpress or stamped type hits | Firm claims | HF, `effects:reject-stamp` | R3 22.6s |
| **Title card** | Timecode "00:00:11:21", then big serif "TITLE CARD" on dark green | Chapter breaks | HF | R5 13.6s |
| **Huge strike** | One huge serif word behind you gets a red line crossed through it | "Not this" | `effects:huge-strike` | — |

## 5. UI and social elements

| Effect | What you see | Use it for | Build with | Seen in |
|---|---|---|---|---|
| **UI orbit** | App icons (CC, Aa, scissors, play, mic) orbit your head | "All these tools" | `effects:orbit` | R1 3.2s |
| **Checklist pop** | White pill chips with orange checks pop in one by one beside your head | Listing features | `effects:todo`, `effects:check-pills` | R1 10.5s |
| **Checklist recap** | A full list ticks from "7/20" to "20/20 effects" on a dark screen | Summaries | `effects:checklist` | R1 39.6s |
| **Live cursor** | A Figma-style cursor labelled "Claude" drags a bounding box with pixel readouts around your head | "AI is doing this" | HF, `effects:select-resize` | R3 0s |
| **Predict keys** | An iOS keyboard types while the prediction bar suggests words | Typing a search or prompt | HF | R3 3.3s |
| **Prompt bar / box** | An AI prompt field types itself and the send button turns into a check | "Just type a prompt" | HF | R5 3.3s, R6 |
| **Comment drop / CTA** | An Instagram comment box types "EDIT", posts, and a reply appears: "Sent. Check your DMs" | The call to action at the end | `effects:comment-box` | R3 8.6s, R5 18s |
| **Voice note** | A WhatsApp-style voice-note bubble with a waveform, then a "Delivered" tick | Client messages, testimonials | HF | R3 19.2s |
| **Post wall** | A grid of posts fills the top while a counter climbs 244 → 1,711 | Volume or output proof | `effects:profile-wall` | R3 6.6s |
| **Icon strike** | App icons (CapCut, Edits) appear, then get struck out with red lines | "You don't need these anymore" | HF | R5 5.5s |
| **Jiggle delete** | iOS home-screen icons jiggle, then get deleted | Replacing old tools | HF | R5 9s |
| **File drop** | A "Drop raw footage" zone; a clip drags in and a "0:31 of raw footage" chip appears | Showing the input | HF | R5 6.6s |
| **NLE timeline** | A video-editor timeline with gold clips appears at the bottom | Editing context | HF, `effects:timeline` | R5 7.8s |
| **Storyboard deck** | Cards (thumbnails) deal and fan out from your hand | Plans, options, a portfolio | `effects:fan-build`, `effects:phone-fan` | R5 4.2s |
| **Grade slider** | A before/after vertical wipe with a centre handle | Before/after results | `effects:swipe` | R5 10s |
| **Eyedropper grade** | An eyedropper picks colours, swatches appear, and the grade changes | Colour or brand matching | HF | R5 11.3s |
| **Playing grid / Reel feed** | Your reel cards pile up, then a real Instagram feed scrolls | Social proof | `effects:noise`, `effects:place-in-grid` | R5 14.7s |
| **Video card** | A video thumbnail card with a title slides in top-left | Referencing another video | HF | R5 17s |
| **Chip row** | A row of tag chips slides across | Categories or features | HF | R6 |
| **Day dial** | A rotary calendar dial spins behind you with a beam of light | Timeframes, "in 30 days" | HF/3js | R3 2.3s |
| **Freeze sticker / Freeze + label** | The frame freezes and a label or sticker annotates you | Pointing something out | `effects:pause-point` | R6 |
| **iMessage pop-ups** | Notifications stack in with a soft glow | Leads coming in | `effects:messages` | — |
| **Follow tap** | A Follow button flips to Following | Ending | `effects:tap` | — |

## 6. Data and numbers

| Effect | What you see | Use it for | Build with | Seen in |
|---|---|---|---|---|
| **Growth curve** | The background goes dark navy and an orange line climbs behind you, with a "1× → 4× → 10×" tag riding the tip | Growth claims | `effects:liquid-glass-graph`, HF | R1 16.7s |
| **Chart grow** | Bars grow inside a white UI card | Comparisons | HF | R2, R6 |
| **Counter tick** | A big number rolls up (used inside Bank note and Post wall) | Any stat | HF/RM | R3 |

## 7. Transitions

| Effect | What you see | Build with | Seen in |
|---|---|---|---|
| **Paper tear** | The frame rips like paper to reveal the next shot | HF texture mask | R3 23.8s |
| **Blade slice** | A diagonal slice cuts across the frame and the halves slide apart | HF | R3 15.1s |
| **Liquid glass** | A refractive glass blob wipes across your face | HF shader, `effects:glass-widgets` | R1 29.4s |
| **Letter dive** | See Typography | HF | R3 |
| **Zoom-through cut** | See Camera | `ff` | R1 |
| **Match cut** | Pages cut on one word, locked behind your head | `effects:match-cut` | — |

---

## Format techniques (how these reels are *structured*, not single effects)

1. **Running index.** A list of every effect sits on screen and highlights the current one.
   - R3/R5: a dark green panel on the right, with the current row as a white pill.
   - R2/R6: a two-column list top-left, with the current item in yellow.
   - R1: a top "20 Video Effects Created by Claude" title, a numbered orange pill ("04 Snap Zoom") and a thin progress bar.

   This keeps viewers watching to the end. Good for any "X tips" or "X services" ad.
2. **Name it as it happens.** The voiceover says the effect name at the exact moment it appears, every 1–2 s. Rapid-fire listing is the hook.
3. **Phone-in-hand showcase** (R2/R6). The creator holds a phone, and each demo plays *inside* it. Cheap to shoot, and it shows the result "on a feed".
4. **One-word captions** (R1). White bold sans with a soft shadow, one word at a time, low-centre.
5. **Two-line caption slab** (R3/R5). White text on a dark rounded box, 4–6 words.
6. **Keyword CTA ending.** "Comment EDIT / STUDIO" plus an animated Instagram comment. Every reel ends this way.
7. **Consistent world per creator.** R3/R5 use deep green, cream and serif (premium, editorial); R1 uses white, orange and sans (bright, techy); R2/R6 use yellow highlights. Pick one world per video and keep it.

---

## Sound effects (from R4: Nick Saraev's tips, plus research)

**The tip:** Claude's motion graphics look good, but the sound effects it picks sound cheap. Fix it with real recordings, placed on the exact frame, at the right level.

| Tool | What it does | Link | Status |
|---|---|---|---|
| **Openverse API** | Free search over ~5M Creative Commons sounds; the agent searches and downloads by itself | openverse.org | Already used inside `hgm sfx` |
| **Real SFX** (skill) | Reads your timeline, finds every moment that needs a sound, and places a real recording on the exact frame | github.com/Clipwing/skills | Not installed |
| **earshot** | Gives the agent "ears": it analyses sound, checks sync, scores real vs fake, and can *generate* a sound or a full kit in code. Includes a `real-sound` soundtrack skill | github.com/Leonxlnx/earshot | Not installed |
| sound-effects (Barty-Bart) | CC0 kit of 110 sounds; one real sound per cue; cuts on the beat; mixes to −16 LUFS | github.com/Barty-Bart/motion-graphics | Not installed |
| video-sound (varg) | Cue sheet, voiceover auditions, sound effects on the frame, and a mix graded for LUFS, true peak and dead air | github.com/vargHQ/skills | Not installed |
| ElevenLabs / Magnific | Generate a custom sound effect when no library sound fits | connected | ✅ |

**Sound rules for every edit:**
- One sound per visual event, never a bed of random whooshes.
- Each sound starts on the frame where the motion *starts*, not when it peaks.
- Use real recordings (foley, UI clicks, paper, glass) over synthetic beeps.
- Duck the music under the voice; mix the final export to about −14 to −16 LUFS for Reels and Meta.
- Silence is also a sound: drop everything for 0.5 s before the punchline.

**Cue map (effect → sound):**

| Effect type | Sound |
|---|---|
| Snap zoom, punch-in | Short whoosh or air swish (80–150 ms) |
| Chips, checklist pop, notifications | Soft UI pop or tick, pitched up slightly for each item |
| Frame break, shatter | Glass crack, then a debris tail |
| Paper cutout, paper tear | Paper rip or rustle |
| Typing, prompt bar, comment | Real keyboard clicks (Mixkit typing), with a send "swoosh" |
| Counter tick, bank note | Fast mechanical ticker, then a cash-register "cha-ching" on the final number |
| Impact frame | Bass hit or boom with a short sub drop |
| Studio reveal | Two light "clunk" switches, then a low hum |
| Blow away | Wind gust plus a granular sand hiss |
| Letter dive, zoom-through | Riser into a whoosh |
| Growth curve | Rising tone (pitch follows the line) |
| Voice note | Soft "bloop" on send |
