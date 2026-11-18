# Module 8: Color Theory & Visual Continuity

> **Note (style profiles).** This module was written while CVES was tested on its first ad. Its research rules are universal; where it speaks of the "house" look or a house number for a per-client choice (palette, accent colour, grade, transition kinds, cutaway share, caption position, bed level), read it as the value from the client's style profile (`docs/STYLE.md`). The black stage / green accent / warm moody A-roll measured here is now the optional preset `profitcast-dark`, not the default.

Dissected from the 8 transcripts in `transcripts/8 Color Theory & Visual Continuity/` (14,363 spoken words in total, all read in full; 8.3 was re-sourced and re-dissected later).
The target is the CVES selfie-ad editor, as first tested. It grades one fixed, front-facing iPhone take (SDR BT.709, 10-bit HEVC, 23.976 fps,
1080×1920 output) in Python (`Edit/look.py`) and cuts it against full-screen motion-graphic cutaways in a black and green-accent palette (now preset `profitcast-dark`)
(`Edit/gfx.py`: accent `(25,230,160)`, accent-dark `(14,120,86)`, `CARD (12,22,18)`, `CARD_B (44,78,63)`, `WELL (18,56,42)`, `WHITE`, `GOLD (214,178,108)`).
There is no colourist, no Resolve, and no reshoot. The levers are the grade maths, the matte, the vignette, the cutaway palette, the encode
tags and, for future shoots, the wardrobe and set.

Timestamps `[mm:ss]` mark the start of the transcript chunk (about 30 s long) that holds the idea. Rule ids take the form `video.rule`, for example `8.5.13`.
Where Resolve-specific steps appear, the rule keeps the colour-science idea and the Python equivalent is given in section B.2.

**Calibration run.** To ground the gates, I measured the test render (`v3c`) with a
numpy/OpenCV probe (YuNet face box, YCbCr code values, OpenCV Lab). The numbers quoted as "v3c baseline" below come from that run:
10 A-roll frames (mid-shot, outside cutaways) and 10 cutaway frames.

---

## A. Per-video dissection

### 8.1 Color Theory in Film: Color Psychology for Directors, Ep. 5
- **Source:** id 8.1 · StudioBinder · https://www.youtube.com/watch?v=lINVnA3rVIE · 284 s (4:44) · 655 words · search match 0.73.
  The curriculum title was "Color Grading vs. Color Correction Process"; the resolved video is StudioBinder's colour-psychology episode instead.
  It is partly on topic: it covers HSB and palette design, not the correction/grading workflow. The correction-before-grading idea is covered better by 8.5 and 8.4.
- **Thesis:** Hue, saturation and brightness (HSB) are the three dials that let a director choose a precise colour for a precise mood.
  Colour meaning is assigned by the film, not fixed, and the grade cannot rescue a production that had no colour plan.

1. `[00:00]` Treat colour as an emotional lever: colours elicit emotions and have a psychological effect on people.
2. `[00:00]` Go beyond "placing a blue tint over an entire sequence"; specify exactly which blue you want.
3. `[00:30]` Specify every colour by three factors: **hue** (the colour itself), **saturation** (its intensity) and **brightness** (how light or dark it is), abbreviated HSB.
4. `[00:30]` Build a complex colour scheme simply from HSB alone.
5. `[01:01]` A monochromatic scheme ("affinity of hue") means the film is mostly one colour. An analogous scheme uses neighbouring colours on the wheel.
6. `[01:01]` Tie the dominant hue to the story world. The Matrix is green because we associate green with code, and the green has a sickly quality that matches the world's state.
7. `[01:32]` Desaturate to make a world feel cold, rude and gritty. Bleach bypass drains colour and evokes faded photographs and black-and-white period newsreels, taking the viewer "back in time".
8. `[02:01]` Use brightness on individual colours as well as on the overall tone of the film.
9. `[02:01]` A palette of entirely bright, vivid colours can be an attraction in itself (Technicolor era).
10. `[02:01]` A dark scene can be so dark that the viewer almost forgets it was shot in colour.
11. `[02:31]` Contrast scenes against each other by value. In one film, one scene uses only dark colours and another only bright ones, and every element is chosen for its darker or lighter colour.
12. `[02:31]` Use hue, saturation and brightness together to "precisely identify the right colours" for the feeling you want.
13. `[03:02]` Rule of thumb: bright images read as lively and exciting, darker images as dramatic.
14. `[03:02]` Rules can be broken: "You get to decide what the colours mean."
15. `[03:02]` Re-assign a colour's meaning by associating it with a character. In *Her*, red connotes love through Theodore, not violence.
16. `[03:31]` Colour codes are not fixed: black is for villains (Vader) until it is for the hero (Batman).
17. `[03:31]` Saturated colours make mundane scenes pop "almost like a comic book" (Wes Anderson). Conversely, comic-book films ground high concepts in gritty, realistic tones.
18. `[04:00]` Post-production now makes the palette easier than ever to control.
19. `[04:00]` Grading is expensive and slow, and it "rarely can make up for" a project that had no colour-design strategy in pre-production. Plan the palette before the shoot.

**Rule count: 19**

---

### 8.2 Using Colour To Tell A Story In Film
- **Source:** id 8.2 · In Depth Cine · https://www.youtube.com/watch?v=UbYjgJuvsDg · 667 s (11:07) · 1,753 words · search match 0.33, **WEAK MATCH**.
  The curriculum entry was StudioBinder's "How Color Theory Works in Film". This is a different channel but squarely on the same topic
  (colour theory, complementary contrast, palettes built through design, light and grade), so it is relevant and was used in full.
  The sponsor read for MUBI (`[00:00]`, `[09:31]`–`[11:02]`) has no content.
- **Thesis:** A film's palette is built in three stages: production design and costume first, then lighting, then the grade.
  A limited palette of complementary colours gives the strongest separation and potency, while a wide palette scatters the image.

1. `[00:00]` Light has shape, quality, strength and colour, and colour is one of cinematography's main tools.
2. `[00:30]` Colour theory is a set of guidelines for mixing colours and for the visual effect colours have on an audience.
3. `[01:02]` Use primary colours sparingly in a frame. A splash of red in an otherwise green landscape stands out and draws the eye.
4. `[01:02]` Know the complementary pairs. They sit opposite each other on the colour wheel, and combined they make white, grey or black.
5. `[01:33]` Placed next to each other, complementary colours create the strongest contrast for those two colours and are generally viewed as pleasing.
6. `[01:33]` Use complementary colours to increase contrast and separation between two planes of the image.
7. `[02:02]` Light the character with warm orange tungsten against a blue-teal background. This gives more separation and depth than a background in a similar orange.
8. `[02:02]` There are two camps of colour psychology: innate meaning (Storaro) and instinct, with many people in between.
9. `[02:32]` Changing the colour temperature of a single light changes the emotion completely (Storaro). For him, blue means freedom.
10. `[02:32]` Colour psychology depends on context and on the audience's background.
11. `[03:02]` A deliberate, repeated colour works as a motif for a theme or idea.
12. `[03:02]` On the Kelvin scale, lower values are warmer and higher values are cooler.
13. `[03:02]` Use warm colours to emphasise physical heat, and cool colours to make a setting feel cold or damp.
14. `[03:31]` A palette is made with three tools: production design and costume, lighting, and the colour grade.
15. `[04:03]` The set and wardrobe are always the starting point. Limit the art department to certain colours and decide specific tones for key props.
16. `[04:03]` Dress the set to the palette: paint the walls, and bring in furniture, curtains and household items that conform.
17. `[04:35]` Choose costume colour carefully because characters are seen close up. A bold primary makes them stand out; a neutral makes them blend into the set.
18. `[05:03]` Lighting starts from colour temperature: warm 3,200 K tungsten and cool 5,600 K HMI.
19. `[05:03]` Add tint on top with coloured gels or by changing an LED's hue or tint.
20. `[05:03]` You can flood the image with monochromatic coloured light, but it is more common to light different pockets of the frame with different temperatures or hues.
21. `[05:32]` Create colour contrast the way you create light/shadow contrast: with different areas of coloured light.
22. `[05:32]` The grade fine-tunes the colour already baked in by the set and the lighting.
23. `[06:00]` Grading manipulates the red, green and blue levels in specific tonal ranges, for example blue into the shadows or magenta into the highlights.
24. `[06:00]` Use power windows to change RGB in one area of the frame, and keys to isolate a colour for adjustment.
25. `[06:32]` Control saturation, the overall intensity of colour.
26. `[06:32]` Use colour to elevate scenes above reality and to show how the characters perceive the world (Euphoria).
27. `[07:02]` Let exaggerated coloured light escalate along with the story's tension.
28. `[07:34]` Use a **limited palette of complementary colours**. A wide palette becomes "visually scattered" and decreases the potency of the colours you do use.
29. `[07:34]` Euphoria's gels were light amber on tungsten units and cyan 30 or 60 on daylight HMIs, plus LED SkyPanels for quickly dialled tints.
30. `[08:31]` Storaro flashed the negative on Apocalypse Now to get the contrast and saturation he wanted. Very strong saturation pushes the image toward the surreal.
31. `[08:31]` Use filters to add an aggressive monochromatic palette that increases tension.
32. `[09:00]` Put artificial colour in conflict with natural colour (coloured smoke against the jungle, using primaries and complementaries).
33. `[09:00]` Black can be the most important colour. Use silhouettes with slivers of light emerging from darkness.

**Rule count: 33**

---

### 8.3 The Power of Colour in Cinema (replacement for "Color in Storytelling")
- **Source:** id 8.3 · It's Just Cinema · https://www.youtube.com/watch?v=9Rb9QcTBmFo · 351 s (5:51) · 1,032 words · manual replacement (match 1.0).
  The curriculum entry was "Color in Storytelling" by Channel Criswell. The House of Tabula transcript dissected before held only title cards and has been replaced.
  The body was checked against the header and matches: it is a narrated video essay on colour in cinema. A Patreon plug at `[05:00]` carries no content.
  The history passage (`[00:30]`–`[01:30]`: tinted silent film, three-strip Technicolor from 1929, the Depression cutback, then the golden age) is context, and only its one transferable idea is kept as a rule.
- **Thesis:** Directors, cinematographers and art departments deliberately include or avoid colours to grab attention, foreshadow and steer emotion.
  A film can build its own colour vocabulary: a colour tied to a character or an idea, a motif that recurs as the story nears its truth, or one scene that breaks the dominant palette. Leaving colour out (black and white) is a choice too.

1. `[00:01]` Use colour for three jobs: grab attention, foreshadow information, and control or influence emotion, both consciously and subliminally.
2. `[00:01]` Decide which colours to include and which to avoid. The choice deepens the narrative and raises the picture's overall quality and beauty.
3. `[00:30]` Plan colour meticulously, shot by shot, together with the cinematographer and the art department.
4. `[00:30]` Even when the medium can't capture colour, an overall tint carries psychological effect (silent-era film was dyed to tint the whole frame).
5. `[01:30]` Use colour as a device for meaning (semiotics), expression and entertainment.
6. `[01:30]` Tie a colour to a character, here the antagonist: Kubrick's red for HAL in *2001*.
7. `[02:01]` Wash an otherwise plain space in one saturated colour to give the scene a feeling it would not have without it: the boring processor room in red carries "impending dread".
8. `[02:01]` The same colour can carry the opposite meaning in another film: red as love and passion in *Her*.
9. `[02:01]` Use costume colour across the film to show a character's changing emotional state without words (Theodore's red, blue, yellow and white shirts).
10. `[02:32]` Beyond cultural connotations, build the film's own colour vocabulary by giving a colour a new meaning: yellow means truth in *Blade Runner 2049*.
11. `[03:00]` Make the motif colour recur each time the protagonist gets closer to the goal (Sapper's house, the flower, the office light, the headquarters walls, Joi's jacket) and peak at the climax (the Las Vegas scenes).
12. `[03:30]` Colour detail that seems unnecessary at first is what separates average from masterful work.
13. `[03:30]` Hold one dominant palette for almost the whole film (dirty beige in *There Will Be Blood*) and break it in a single scene (saturated blue) so that scene stands out.
14. `[04:00]` Let the meaning of the break colour turn inside the scene: the blue first reads as freshness, then as cold once the character realises how alone he is. Context re-colours a colour's meaning.
15. `[04:00]` Treat the absence of colour as a deliberate option: shoot black and white when that is right for the story.
16. `[04:30]` Black and white gives seriousness, realism and authenticity, especially when it references period photojournalism or neo-realism, and can make a narrative feel like a documentary (*Raging Bull*).
17. `[05:00]` Don't take colour for granted now that it is the norm; use its power on purpose.

**Rule count: 17**

---

### 8.4 Learn to PRO Color MATCH Shots in 15 mins!
- **Source:** id 8.4 · Darren Mostyn · https://www.youtube.com/watch?v=l3rOObH74TE · 851 s (14:11) · 2,847 words · search match 0.73 (correct topic).
- **Thesis:** Making one shot look good is easy; the craft is coherence across a scene. Match shots on the subject's skin, not the walls.
  Copy the grade, then correct the residual difference on a dedicated balance node. Compare shots on scopes after resizing the reference so the subject fills a similar share of frame, and verify with a split screen and a play-through.

1. `[00:00]` Making one shot look good is easy. The art is making it look coherent across an entire scene (scene balancing).
2. `[01:00]` Turn the brief into concrete grade attributes. "Gothic" became desaturated skin tones, coolness in the blacks, and "nice and contrasty".
3. `[01:31]` Keep the skin tone consistent across a location change (gig in the church, then her house) to give continuity.
4. `[02:01]` Use a fixed node tree: the same node numbers do the same job on every shot, which keeps you efficient.
5. `[02:01]` Check colour management before anything else.
6. `[02:31]` Grade in a large working space (DaVinci Wide Gamut Intermediate) and output Rec.709 gamma 2.4, because that is what the monitor is calibrated to and what the deliverable is.
7. `[02:31]` Use colour-space transforms: camera log (Blackmagic Pocket Film Gen 4) to DWG first, then DWG to Rec.709 at the end.
8. `[03:01]` Switch on the output transform early so you are grading what the display shows; otherwise "I wouldn't have a clue what's going on".
9. `[04:01]` Before grading, play the shot and make sure you are on the representative part of it.
10. `[04:30]` Node 1 is the transform; node 2 is general exposure and first balance.
11. `[04:30]` Read the scopes first: make sure nothing clips in the blacks, and lift the image if it is set too low.
12. `[05:01]` Set exposure with offset (or the HDR tools).
13. `[05:01]` Make sure the blacks "sit nicely" at the bottom of the scope.
14. `[05:31]` Use a film print emulation (Kodak 2383) for cool blacks and creamy highlights without adding much saturation.
15. `[06:00]` Compare candidate looks with a grabbed still and a wipe. He found Resolve's built-in 2383 harsh and chose Dehancer's warmer 2383 for this promo.
16. `[06:31]` Knock exposure down very slightly inside the print-emulation node.
17. `[07:01]` Never stack two print emulations. Place the emulation before the output transform and grade underneath it, not at the end, because "it's going to do quite a lot to your image".
18. `[07:32]` Use node 3 for colour temperature and saturation. Don't add saturation when the look is desaturated; correct the shot that is "a little bit warm".
19. `[08:00]` Make small balancing pushes, such as gain slightly toward blue, "not too much".
20. `[08:00]` Grab a still of the finished hero shot as the reference for matching the others.
21. `[08:31]` Copy the grade to the other shots, but expect a mismatch even in the same room with the same lights. Her face was "much higher exposure".
22. `[08:31]` Do the shot-to-shot correction on a separate balance node, not in the hero grade.
23. `[09:00]` Match the skin tones and the face, not the walls. Walls differ when the camera faces another direction.
24. `[09:00]` Balance with global controls rather than keying the skin.
25. `[09:00]` Use display-qualifier focus to find where the skin sits on the scope, and ignore the wall traces.
26. `[09:31]` Resize the reference still so the subject takes a similar share of frame in both images. Otherwise the scope is dominated by the wall and the comparison is unfair.
27. `[10:31]` Copy the match to the next shot, then correct its overshoot (that one ended up too dark, so lift it).
28. `[11:00]` Fine-tune the remaining skin difference with gain.
29. `[11:00]` Check by wiping against the timeline clip.
30. `[11:30]` Check all the matched shots together in a split-screen of selected clips on the output monitor.
31. `[11:30]` The technique in one line: grab a still, reposition it so the scopes compare like for like, then balance with the scopes.
32. `[12:02]` Group the matched shots and apply the shared look at group level.
33. `[12:31]` For a wardrobe colour, use hue-vs-hue on the shirt. Widen the selection ("you don't want them too tight") and dial it back if it is too much.
34. `[13:01]` Ripple a node change across the group so every shot gets the same fix.
35. `[13:30]` Confirm the matched shots keep the reference's skin property (low saturation in the skin here).
36. `[13:30]` Play the scene through from the previous scene to check continuity across the boundary.
37. `[13:30]` Add vignettes, windows and shapes only after the shots are balanced.

**Rule count: 37**

---

### 8.5 Your Skin Tones Look Fake Because You're Making These Mistakes
- **Source:** id 8.5 · Waqas Qazi · https://www.youtube.com/watch?v=0GZSn6nDlnM · 1,090 s (18:10) · 3,400 words · search match 0.67 (correct topic: skin tone and vectorscope).
  It has a Memorial Day sale plug at `[05:30]` and `[17:31]`.
- **Thesis:** Camera colour science is built around skin. Green or magenta skin is a balance error, not a camera fault.
  Fix the colour balance first, with broad in-camera-like moves (gain, temp and tint in linear light, hue-vs-hue) anchored on neutrals.
  Never desaturate or saturate globally, or key skin, as the first step.

1. `[00:00]` Every camera manufacturer (ARRI, Canon, Fujifilm, Sony, Panasonic, RED) builds its colour science around skin tones. Trust that starting point.
2. `[00:31]` Green or magenta skin is usually user error, not the camera.
3. `[01:01]` Start from a proper log-to-Rec.709 conversion.
4. `[01:30]` Anti-pattern: seeing reds as too saturated and pulling global saturation down. It "stripped the life out" of the manufacturer's "look DNA".
5. `[02:02]` Global desaturation leaves the image under-saturated and lifeless.
6. `[02:30]` Anti-pattern: adding global saturation back. The skin gains "life" but looks unnatural because you inject something artificial.
7. `[03:01]` Diagnose by hovering over the skin and seeing where it lands on the vectorscope. Here it showed a strong green bias.
8. `[03:30]` Anti-pattern: keying the skin, denoising the key and pulling green out with offset. The result is "not bad", but it manipulates instead of corrects.
9. `[04:00]` Never make skin-tone manipulation the first step; correct the image first.
10. `[04:30]` Define "natural" against references: Queen's Gambit (muted but natural), Mad Max (unnatural but right in context), Severance (the sweet spot: clean, skin "just right").
11. `[05:00]` Pick your middle point on that scale before grading. Severance's skin is roughly "cleaned up white balance" plus contrast.
12. `[06:01]` The pro techniques are hue-vs-hue, temp and tint in linear light, gain balance in linear light, and then a qualifier into gamma only if needed.
13. `[06:01]` Set the node's gamma to linear (and ripple that to all shots), because linear-light changes behave like in-camera changes and respect the colour science.
14. `[06:31]` Fix colour balance instead of desaturating; correct balance "puts everything in place".
15. `[06:31]` In linear light, gain acts as offset. Balance by watching the white (neutral) area.
16. `[07:00]` Don't neutralise to sterile white. Keep the slight tint that an indoor scene would have. Lighting matters most for skin.
17. `[07:30]` Judge balance against known-colour practicals in the background (lamps that should be orange, not "gunky green").
18. `[07:30]` Use hue-vs-hue to compress discolouration: pull red down and lift yellow so red patches and yellow areas converge on one skin hue.
19. `[08:00]` After hue-vs-hue, return to gain and re-tweak the balance.
20. `[08:30]` Desaturating without fixing balance dulls lips and face and blends the subject into the background. A correct balance separates the subject strongly ("like green screen").
21. `[09:02]` Broad-stroke changes fix patchy skin. Hue-vs-hue is "your huge huge friend".
22. `[09:30]` Use temp and tint only in linear light. In the primaries they are "super artificial".
23. `[10:00]` Target a steely grey on neutral objects, and keep each known neutral neutral.
24. `[11:00]` Don't neutralise motivated colour: blue light from a screen on the subject stays blue.
25. `[11:30]` Aim for a neutral space that keeps each camera's character. Secondary manipulations strip the "look DNA" the DP and director chose.
26. `[12:03]` If the whole image carries green, fix it with tint alone; the skin then returns to the skin-tone indicator line.
27. `[12:32]` A correct balance gives colour separation everywhere: whites read white, grass, bricks and sky separate.
28. `[13:02]` When skin lacks "juice", start with balance. Here the parade showed a green bias, then red, then blue.
29. `[14:03]` Balance until the RGB parade is even and the vectorscope is centred. The skin then "pops" without added saturation.
30. `[14:32]` Qualifiers are fine "if it's used right": after balance, denoised heavily.
31. `[14:32]` For skin adjustments, use gamma (midtones), because that is where skin lives for dark and light complexions alike.
32. `[15:01]` Push skin only until just before the subject stops looking real; compare before and after.
33. `[15:32]` Always look for anchors: blacks, whites and all the neutral colours in the image.
34. `[15:32]` On a white shirt, the three RGB parade dots should be even.
35. `[16:00]` Correct with gain (drop red, raise blue) but keep a slight bias toward the scene's motivated light (red over green over blue indoors).
36. `[16:31]` Clean neutrals remove the warmth "seeping" into the forehead and give separation.
37. `[17:31]` For a natural look or natural skin, use broad strokes as if done in camera, so the image is as close as possible to what the manufacturer intended.

**Rule count: 37**

---

### 8.6 The 60-30-10 Color Rule Explained (And How To Use It)
- **Source:** id 8.6 · Kittl · https://www.youtube.com/watch?v=rAfjUOkbyr0 · 214 s (3:34) · 509 words · manual replacement (the first hit had no captions); transcribed with local Whisper.
  This is a graphic-design source, not a film one, which is appropriate here because the rule is applied to cutaway graphics. It has a Kittl plug at `[02:00]`.
- **Thesis:** A balanced scheme uses three colours by area: 60% dominant (background), 30% secondary (supports it and adds interest) and 10% accent (sparing pops on calls to action and key details).

1. `[00:00]` Use the 60-30-10 rule to build a balanced, cohesive palette.
2. `[00:33]` Colour's jobs in design are to evoke emotion, create harmony and guide attention.
3. `[00:33]` Build the scheme from three main colours; the percentages are their distribution across the design.
4. `[01:02]` **60% dominant:** the colour covering most of the design, such as the background or main element.
5. `[01:02]` **30% secondary:** it complements the dominant colour and adds visual interest.
6. `[01:02]` **10% accent:** a pop of vibrancy, applied sparingly to specific details, call-to-action buttons or anything that must draw attention.
7. `[01:32]` Worked example: a black dominant sets the brand mood, an off-white secondary contrasts with it ("black and white create the highest contrast possible"), and a magenta accent appears only in details.
8. `[02:34]` Keep it simple: a limited palette avoids overwhelming the audience and stays clean.
9. `[02:34]` Choose colours from the brand identity and the audience's preferences.
10. `[02:34]` Experiment, using colour pickers or palette tools to find shades that work together.
11. `[03:01]` Test the colour choices for accessibility.

**Rule count: 11**

---

### 8.7 Why Your Videos Look Flat: Contrast Explained
- **Source:** id 8.7 · Graded by Oscar · https://www.youtube.com/watch?v=4HfUIWwjdmQ · 817 s (13:37) · 2,247 words · manual replacement (match 1.0).
  The curriculum entry was by Avery Peck; this replacement is on topic.
- **Thesis:** "Flat" means the waveform sits in a narrow band. Build contrast with a monotonic S-curve (shadows down, highlights up, midtones placed),
  then add colour (split toning, hue curves) and a subtle vignette. Contrast comes first and colour after.

1. `[00:30]` Pipeline: S-Log3 to DaVinci Wide Gamut with a CST, grade, then a CST to Rec.709 at the end.
2. `[01:00]` Read the waveform: its x-axis is horizontal position in the image and its height is brightness.
3. `[01:00]` Use display-qualifier focus to see which part of the image a trace belongs to.
4. `[01:30]` Raising luminance moves the whole waveform up.
5. `[02:01]` Contrast is the difference between the darkest and brightest parts of the image. A flat image has them in "a very thin band".
6. `[02:30]` A log-to-709 conversion is not enough; build contrast in the grade "without breaking our image".
7. `[03:02]` If there are no real shadows, put a point low on the curve and pull it down so only the shadows move.
8. `[03:02]` Curve points isolate tonal regions: pulling a low point barely moves the highlights (the mountain peaks).
9. `[03:32]` A typical S-curve pulls the shadows down and the highlights up.
10. `[04:00]` If the image still looks flat or faded after the S-curve, pull the midtones down.
11. `[04:00]` Click the image to place a curve point at that pixel's tone.
12. `[04:30]` Moving one point drags its neighbours; add or adjust another point to compensate.
13. `[05:30]` Don't over-manipulate the curve. A bend that makes brighter parts of the image darker than darker parts (tone inversion) "completely" breaks the image.
14. `[06:31]` Keep the S shape (monotonic). Rebalance if the highlights were pulled down too far.
15. `[07:02]` Adding contrast also adds saturation, visible on the vectorscope.
16. `[07:30]` Split toning: lower the red curve in the shadows to put teal into them without touching the highlights.
17. `[08:32]` Push gamma (midtones) toward orange-pink for the warm half of the split tone.
18. `[08:32]` "The main juice" happens in the custom and hue curves.
19. `[09:00]` Hue vs hue: rotate blue toward cyan or teal, watching the vectorscope.
20. `[09:31]` Hue vs saturation: raise cyan to make that area pop.
21. `[10:00]` A teal look is stylised (there was no teal light source). For a natural look leave it out, or go near black and white.
22. `[10:31]` Add saturation in the red and yellow ranges to accentuate the warm sunset light.
23. `[11:02]` Hue vs luminance: a small brightness lift on the reds.
24. `[11:02]` Vignette: an oval power window with a tiny gamma boost and a little contrast inside, and an outside node that pulls gamma down.
25. `[11:32]` Shape the window's curves with editable splines for a smooth result.
26. `[12:31]` Make the vignette as subtle or as strong as you like.
27. `[13:00]` Order of work: build contrast first, then add the colour.

**Rule count: 27**

---

### 8.8 Why Teal & Orange is Scientifically More Cinematic
- **Source:** id 8.8 · Matti Haapoja · https://www.youtube.com/watch?v=410kMINGZ0o · 666 s (11:06) · 1,920 words · manual replacement (match 1.0).
  The curriculum entry was a Vox video; this replacement covers the same teal/orange idea plus "when to break it". It has an Artlist sponsor read at `[04:30]`–`[05:31]`.
- **Thesis:** Skin sits on one hue line (orange), and its complement is blue/teal. Putting blue in the wardrobe, props and background, especially right against the skin,
  makes faces pop more than any grade. Break the pairing on purpose to signal that something has changed.

1. `[00:30]` The same grade looks better or worse depending only on wardrobe. Wardrobe changes how good the grade is perceived to be.
2. `[01:00]` Productions dress leads, extras and small details in blue or teal.
3. `[01:00]` Colour contrast comes from opposite colours on the wheel. Red and green pop far more than red and orange.
4. `[01:30]` The thing you want to pop is the skin, the people.
5. `[02:02]` Everyone's skin hue is the same: it sits on the vectorscope's flesh-tone line and differs only in luminance (brighter or darker).
6. `[02:02]` The complement of skin is blue, so add blue to get maximum colour contrast with skin.
7. `[02:31]` Don't add blue everywhere with the grade sliders; add blue objects and wardrobe to the frame.
8. `[02:31]` Put the blue right up against the skin (shirt, hat) for the strongest contrast.
9. `[03:00]` This is why a favourite grade sometimes looks great and sometimes doesn't: the frame's colours differ.
10. `[03:00]` Evidence in Interstellar (shirts, screens, logo, cups), The Fall Guy, Drive and Severance.
11. `[04:02]` Blue clothing pulls the eye exactly where the director wants (the faces).
12. `[06:01]` Demo: a white t-shirt and black shorts, then a blue hat ("instantly my face pops"), then a blue shirt (better again), all with no grade change.
13. `[06:30]` A blue backdrop works the same way.
14. `[07:00]` Break the scheme deliberately to signal change. Interstellar's maroon t-shirt clashes with the blue/orange world and must be deliberate.
15. `[07:30]` A single off-palette colour flags a character subconsciously (Black Bag: one character in red in a teal/orange world).
16. `[08:02]` There is wiggle room on the axis: red/green (Amélie) or yellow/blue (Moonlight) also work. The presenter prefers teal/orange and rates yellow/blue above red/green.
17. `[09:01]` Apply it to backgrounds and props too. A green screensaver hurts; blue helps; slightly too teal is weaker than blue.
18. `[09:31]` It works best when the scene is otherwise boring or white (Interstellar's white hospital, saved by a blue shirt).
19. `[10:01]` Sunsets look good for the same reason: an orange sun against blue sky.
20. `[10:01]` The starting point (wardrobe, set) matters as much as the grade, "if not way more".
21. `[10:30]` Make it a habit: he wears a blue hat when filming because it makes his skin and eyes pop.

**Rule count: 21**

---

## B. Module synthesis

### B.1 Best practices (de-duplicated, ordered by impact)

| # | Rule | Sources | Scope |
|---|---|---|---|
| 1 | **Correct before you grade.** Fix exposure and white balance against neutral anchors (whites, blacks, greys) with broad, global, in-camera-like moves before any creative look or skin manipulation. Never "fix" skin by global desaturation or saturation, or by keying, as the first step. | 8.5.4–9, 14, 26, 28–29, 33–37; 8.4.10–13; 8.1.19 | UNIVERSAL |
| 2 | **Skin is the reference for everything.** All skin hues sit on one flesh-tone line on the vectorscope and differ mainly in luminance. Judge every grade by whether skin lands on that line, keeps its "juice" and looks real. | 8.5.1, 7, 10, 26, 29, 32; 8.8.4–5 | UNIVERSAL |
| 3 | **Match shots on skin, not walls.** Copy the grade, then put the residual correction on a separate balance node. Compare the face region on scopes with the subject at the same frame share, and check all the shots together and in a play-through. | 8.4.1, 3, 20–31, 35–36 | UNIVERSAL whenever there is more than one shot |
| 4 | **Build contrast with a monotonic S-curve.** Flat means a narrow waveform band: pull the shadows down, lift the highlights, place the midtones, and never invert tones. Do contrast first and colour after. | 8.7.5–14, 27 | UNIVERSAL |
| 5 | **Use a limited palette with one complementary pair.** Separate subject and background with complementary colour (warm skin against teal/blue). A wide palette scatters attention and weakens every colour. | 8.2.4–7, 28; 8.8.3, 6; 8.6.8; 8.1.5 | UNIVERSAL |
| 6 | **The starting point beats the grade.** Wardrobe, set and light colour do more than any grade. Blue/teal wardrobe or props against the skin make the face pop; a neutral or off-palette shirt cannot be graded into that. Plan colour shot by shot before the shoot; costume colour can also carry the subject's emotional state. | 8.8.1, 7–8, 12–13, 17–18, 20; 8.2.14–17, 22; 8.1.19; 8.3.3, 9 | CONTEXT (shoot planning) |
| 7 | **Keep motivated colour and a hint of ambient tint.** Don't neutralise to sterile white: indoor warmth and screen-blue stay. Keep the look's intent (warm and moody here). | 8.5.16, 24, 35; 8.4.2 | UNIVERSAL |
| 8 | **Do colour maths in the right space.** Balance (temp, tint, gain) in linear light, and grade inside a defined transform: source to working space to display space. Turn on the display transform early so you judge the real output. | 8.5.13, 15, 22; 8.4.5–8, 17; 8.7.1 | UNIVERSAL |
| 9 | **60-30-10 for designed frames.** Dominant (background) about 60%, secondary about 30%, accent about 10% by area, with the accent reserved for calls to action and key details, and accessible contrast. | 8.6.3–7, 11 | CONTEXT (graphics and cutaways) |
| 10 | **Plan colour meaning and keep it consistent.** A colour repeated on purpose becomes a motif. Assign meanings (red = love, brand accent = "the fix") and break them only on purpose, to signal change. Build the piece's own vocabulary: tie a colour to a character or an idea, let the motif recur each time the story moves toward its answer and peak at the climax, and break the dominant palette in only one place so that place stands out. Context can turn a colour's meaning. | 8.1.6, 14–16; 8.2.11; 8.8.14–15; 8.3.6, 8, 10–11, 13–14 | CONTEXT |
| 11 | **Use HSB as the vocabulary.** Specify a colour by hue, saturation and brightness. Bright reads lively, dark reads dramatic, and desaturated reads cold or gritty. A saturated wash over a plain space sets the mood; no colour at all (black and white) reads as serious, real and documentary. | 8.1.3–4, 7, 12–13; 8.3.7, 15–16 | UNIVERSAL |
| 12 | **Hue-vs-hue for discolouration.** Compress red patches and yellow areas toward one skin hue with wide, soft selections, dialled back if overdone. Use gamma for skin density, and qualifiers only after balance, heavily denoised. | 8.5.18, 21, 30–31; 8.4.33; 8.7.19–20 | UNIVERSAL (as a secondary step) |
| 13 | **Saturation follows contrast.** Adding contrast raises saturation, so re-check saturation after every contrast change. Use split toning (teal shadows, warm mids) only as a stylised choice. | 8.7.15–17, 21 | UNIVERSAL / CONTEXT |
| 14 | **Do vignettes and windows last, and subtly.** Balance first, then a soft vignette (inside gamma up a hair, outside gamma down). | 8.4.37; 8.7.24–26 | UNIVERSAL |
| 15 | **Mind the blacks.** Check for clipped blacks and make them sit "nicely" at the bottom. A print-emulation look can add cool blacks and creamy highlights; never stack two looks. | 8.4.11, 13–17 | UNIVERSAL |
| 16 | **Kelvin language.** Lower K is warmer (3,200 K tungsten) and higher K is cooler (5,600 K daylight). Warm reads heat; cool reads cold or damp. | 8.2.12–13, 18 | UNIVERSAL |
| 17 | **Colour does three jobs: attention, foreshadowing and emotion.** Decide what to include and what to avoid for each; no colour is accidental. | 8.3.1–2, 5, 17; 8.2.3; 8.6.2 | UNIVERSAL |

### B.2 Short-form ad translation (9:16, 30–60 s, one fixed selfie take plus dark-stage accent cutaways)

**What transfers directly**
- **B.1-1 (correct before grade).** `look.py` grades straight from the BT.709 plate with fixed multipliers. There is no per-shot balance step and no anchor check.
  Translation: measure a neutral anchor before grading. Options are the wall (a near-neutral grey-beige in the raw), the white of the eyes, or a grey card if one is ever shot.
  If the anchor's Cb/Cr bias differs from the approved reference by more than the gate in B.5, apply a per-segment linear-light gain correction **before** `grade()`.
  One take in one room under one light needs only a small correction, but iPhone auto white balance and auto exposure drift across a 4-minute raw (segments run from 0.2 s to 218 s).
- **B.1-2 (skin line).** This is the most valuable automatable check. In the v3c baseline, the median skin hue across 9 A-roll shots is **117.5°–121.3°** (atan2(Cr, Cb) on BT.709 YCbCr),
  within 2–6° of the classic 123° I-line, with chroma 27–30 (8-bit Cb/Cr units). The plate measured 117.8° and `grade()` moved it to 120.2° (+2.4°, toward the line) with +4% chroma.
  The grade is doing the right thing: warm without swinging magenta or yellow.
- **B.1-3 (match on skin, not wall).** In a single-take selfie, "shots" are segments of one take, so the wall is constant and skin is the right anchor.
  Measure the Lab mean of a fixed face-core patch (from the YuNet box) and of a wall patch, and compare consecutive A-roll segments.
  Punch-ins (1.12–1.14×) change the subject's frame share, which is exactly the Mostyn "resize the reference" problem: compare **face-patch** statistics, never whole-frame statistics.
  The EDIT-STANDARD rule "No sudden dims, no desaturation jumps" is this gate.
- **B.1-4 (contrast).** The baseline A-roll luma runs p1 = 19–24 and p99 = 169–180 (8-bit limited range), and the face/wall luma ratio is 2.1–3.05.
  That is intentionally low-key, with the contrast coming mostly from the subject/background separation of the matte darkening.
  `look.py`'s subject curve (`gamma 1.12`, `gain .97`) plus a filmic shoulder (`x/(1+.25x)`, ×1.2) is a monotonic S-like curve, consistent with 8.7.13–14.
- **B.1-5 / B.1-6 (complementary pair, wardrobe).** The current take has an **olive-green t-shirt** against a warm grey-beige wall, darkened and pushed warm-brown by `look.py` (`[1.0, .93, .86]`).
  Skin, wall and shirt therefore sit in the warm/yellow-green half of the wheel, and there is no blue anywhere in the A-roll.
  Per 8.8, the cheapest upgrade for future shoots is a **blue, teal or denim shirt**, or a blue practical or object in the background.
  It cannot be fixed in post without a garment key, which would violate 8.5.9 and risk edge artefacts like the "aura".
  Note also that the test look's cutaways are teal-green (hue about 158°), which already provides the cool half of the pair *across the cut*.
  The ad alternates warm A-roll with cool graphics, a temporal version of complementary contrast. Keep it.
- **B.1-7 (motivated tint).** The test look (preset `profitcast-dark`) is "warm, dark and moody"; a client's own grade comes from style `grade:`. Do **not** neutralise skin to a clinical white balance. The gate allows a warm bias but caps it (B.5 G3).
- **B.1-8 (linear light).** `look.py` applies its warm multipliers (`[1.02, .985, .95]` subject, `[1.0, .93, .86]` wall) to **gamma-encoded** BT.709 values.
  That is the "temp/tint in the primaries" approach Qazi calls artificial (8.5.22). At these small magnitudes the measured effect is benign (+2.4° hue).
  If the warmth is ever increased, move the white-balance multiply into linear light: decode the BT.709 OETF, multiply, re-encode, then apply the tone curve.
- **B.1-9 (60-30-10).** It applies to the cutaways. The baseline cutaway frames measure about **89% dark (black/card) / 10% accent (glow, icons, highlights) / <1% white (type) / <0.6% off-palette**.
  That is a dominant/accent scheme rather than a literal 60-30-10, which is correct for this series: the brand look *is* "black stage, green accents", and the inspirations work that way. Other clients' ratios come from their inspirations.
  Translate 60-30-10 into **roles, not literal areas**: dominant = black and near-black card surfaces; secondary = dark green (card borders, wells, dot grid, glow); accent = the saturated accent colour plus white type.
  The gate (B.5 G8) bounds the dominant share, the accent share and off-palette pixels rather than forcing 60/30/10.
- **B.1-10 (colour meaning).** The accent is "the fix / the brand"; white ✕ states on dark cards are "the problem". `GOLD` is reserved for client wordmarks.
  Keep these meanings constant across the ad and the series. A red, for example for a warning or a competitor, would read as the deliberate break of 8.8.14–15, so use it only once and only on purpose.
  8.3 adds the motif trail (8.3.11): the accent should appear each time the fix is named, and the problem states should never use it. It peaks at the end card or CTA, the ad's "climax", where the brand is said. A single palette break (8.3.13) belongs at most once, and only where the story turns.
  Foreshadowing (8.3.1) transfers as letting a small accent appear on the solution before the full solution cutaway arrives, within the words-first rule of EDIT-STANDARD §1.
- **B.1-14 (vignette).** `look.py`'s vignette is centred on the face with strength 0.55 and a soft falloff. This is consistent, and the order (after balance) is right.
- **B.1-15 (blacks).** The baseline A-roll black (p0.1) is 18 against the legal 16, with zero frames crushed. `look.py`'s `+[.010,.007,.004]` lift gives warm, never-crushed blacks, as intended.

**What does NOT transfer, and why**
- Log and CST management (8.4.6–7, 8.5.3, 8.7.1). The source is iPhone SDR BT.709 (verified with ffprobe: `bt709/bt709/bt709/tv`), not log, so there is no log conversion.
  The transferable part is "know your working space and output space and keep them consistent", and the output encode is where that currently fails (B.6 F1).
- Film print emulation LUTs (8.4.14–17). They are optional and not part of the test look. If one is ever added, it goes before the final output step and only one is allowed.
- Gels, HMIs, set dressing and Kelvin choices (8.2.18–21). These are shoot-side only, and useful as shoot notes for future takes.
- Scene-to-scene palette shifts for story (8.1.11, 8.2.26–33, 8.3.13–14). A 30–60 s ad has one "scene". The only valid story shift is the A-roll/cutaway alternation and, optionally, one deliberate accent break at the CTA.
- Black and white for realism (8.3.15–16), and whole-frame saturated washes for dread (8.3.7). Both conflict with the warm, natural-skin test look. A selfie ad is already as "documentary" as it gets.
- Bleach bypass and heavy desaturation (8.1.7). These conflict with "natural skin", which every look keeps.
- Teal split-toning of the A-roll shadows (8.7.16). It conflicts with "warm shadows" in `look.py` and with EDIT-STANDARD's warm look. Teal belongs to the cutaways.

### B.3 Checklist (binary)

**Pre-edit / pre-shoot**
- [ ] Is the shirt or a background object blue, teal or denim (complementary to skin), and not olive, green or skin-coloured? (8.8)
- [ ] Is there a known neutral in frame (white of a garment, grey wall patch) to anchor balance? (8.5.33)
- [ ] Is the camera white balance locked, not auto, for the whole take? (8.5.2 in principle; prevents drift)
- [ ] Is exposure locked so the face does not breathe between sentences? (8.4.21)
- [ ] Has the source colour space been confirmed with ffprobe (`bt709` transfer, primaries, matrix; `tv` range)? (8.4.5)

**During edit**
- [ ] Is balance corrected on neutrals before `grade()` runs, with no global saturation change used as a fix? (8.5.4–9, 14)
- [ ] Is any white-balance multiply done in linear light? (8.5.13, 22)
- [ ] Is the tone curve monotonic, with no point where a brighter input maps darker? (8.7.13)
- [ ] Was saturation re-checked after the contrast change? (8.7.15)
- [ ] Is the vignette applied after balance and centred on the face? (8.4.37, 8.7.24)
- [ ] Do the cutaways use only palette colours (stage, card colours, accent, white, plus gold for client wordmarks)? (8.6.8, 8.2.28)
- [ ] Is the accent reserved for the spoken key item or CTA in each cutaway? (8.6.6)
- [ ] Does any off-palette colour (e.g. red) appear only as a deliberate, single "break"? (8.8.14, 8.3.13)
- [ ] Does the accent appear on every solution/fix element and on no problem element, peaking at the end card or CTA? (8.3.10–11)

**Pre-delivery**
- [ ] Do gates G1–G10 (B.5) pass?
- [ ] Have all A-roll shots been viewed side by side in a split contact sheet (one face crop per segment)? (8.4.30)
- [ ] Has the whole ad been watched through, A-roll into cutaway into A-roll, for continuity? (8.4.36)
- [ ] Is the final encode tagged `bt709` primaries, transfer and matrix, `tv` range? (industry norm)

### B.4 QA (senior-editor review while watching)

| Question | What good looks like |
|---|---|
| Does the skin look like skin? | Warm, alive, neither orange nor grey. No green "gunk" in shadows or beard edge, no magenta forehead, no red patches on nose and cheeks. (8.5) |
| Does the face pop from the room without looking cut out? | Clear separation through luminance (darkened wall) and warmth, and no halo. "Green-screen" separation from correct balance is good; separation from a glowing matte edge is the v1 "aura" failure. (8.5.20; EDIT-STANDARD §2) |
| Across each A-roll cut, does anything other than framing change? | Only the punch-in changes. Face brightness, warmth and saturation are identical; a viewer should never feel "the light changed". (8.4.21–23; EDIT-STANDARD "no sudden dims") |
| Coming out of a cutaway, does the A-roll feel like the same world? | The warm room returns at the same level every time; the accent/black cutaway feels like a deliberate counterpoint, not a different video. (8.4.36, 8.2.28) |
| Is the image flat or crushed? | Real blacks in hair and t-shirt shadows, but texture is still visible in the beard and hair. The face sits in the upper-middle of the waveform, and no area looks milky. (8.7.5–10) |
| Is there a single clear accent per cutaway? | The eye lands on the accent item that matches the spoken word. White type is legible; nothing else competes. (8.6.6) |
| Does the wardrobe help or fight the grade? | Ideally a blue or teal top. With olive or green tops, check that the warm push doesn't make shirt and skin merge into one muddy family. (8.8) |
| Is the vignette visible as a vignette? | It should be felt, not seen: corners darker, no grey ring, no visible centre "spotlight". (8.7.26) |
| Do colour meanings stay consistent? | Accent = solution/brand, white ✕ = problem, gold = client brand, every time. (8.1.15, 8.2.11, 8.3.10) |
| Does colour lead the eye toward the answer? | The accent grows more present as the ad moves from problem to proof to offer, and the end card is its strongest moment; nothing in the accent colour sits on a problem. (8.3.11) |

### B.5 QC (automatable gates)

All gates run on **decoded frames of the final encode** (not on the PNG frames), because encode and tagging errors only show there.
Decode with `ffmpeg -ss t -i final.mp4 -frames:v 1 -f rawvideo -pix_fmt yuv444p -` to get true 8-bit limited-range Y/Cb/Cr code values. Then:
`Cb' = Cb − 128`, `Cr' = Cr − 128`; RGB via the BT.709 matrix; Lab via `cv2.cvtColor(rgb01_float32, cv2.COLOR_RGB2Lab)` (sRGB-encoded input; Rec.709 and sRGB share primaries and white).
**Sample set:** the middle frame of every A-roll segment from `edl_v2.json`/`render_v2.SEGS`, excluding `CUT` ranges ±0.2 s and transitions; the middle and first+1.2 s frame of every cutaway; plus the first and last 2 frames of each A-roll segment for jump checks.
**Face patch:** YuNet box `(x, y, w, h)` re-detected on the output frame; skin core = `rows cy−h/5 … cy+h/6, cols cx−w/4 … cx+w/4` (cheeks, nose, forehead; it avoids beard, eyes and hair).
**Wall patch:** pixels above `0.6·H` that lie outside the face box widened by `w/2` each side, or (better) `matte < 0.05` from `matte_v2`.

Thresholds marked **[industry]** are standard norms. Those marked **[house, v3c-calibrated]** are proposals set just outside the measured baseline of the approved-direction render, so they catch regressions. Re-baseline them when the look is re-approved.

| Gate | Metric and how to measure | Pass | Basis / v3c baseline |
|---|---|---|---|
| **G1 Delivery tags** | `ffprobe -show_entries stream=color_space,color_primaries,color_transfer,color_range` on the deliverable | `bt709 / bt709 / bt709 / tv` all present | [industry]. **v3c FAILS: primaries and transfer are `unknown`.** Fix: add `-colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv` to the x264 encode. |
| **G2 Legal range (broadcast/web-safe)** | % pixels with Y < 16 or Y > 235; % with Cb or Cr outside 16–240; RGB gamut: % pixels with any channel < −5% or > 105% after the BT.709 matrix | Y outside 16–235 ≤ 0.5% of pixels (EBU R103 tolerance allows 5–246 *excursions*; hard fail if any Y < 5 or > 246); chroma outside 16–240 = 0; gamut excursions ≤ 1% of pixels | [industry: BT.709 limited range, EBU R103]. v3c: 0.00–0.11% outside 16–235 (text and graphics overshoot); passes. |
| **G3 Skin hue on the skin line** | Median of `atan2(Cr', Cb')` in degrees over the skin core of each A-roll sample | Within **123° ± 8°** (115°–131°); warn outside ± 5° | Skin line from 8.5/8.8; 123° is the conventional I-line [industry]. The ± tolerance is [house, v3c-calibrated]: v3c is 117.5°–121.3°. Note that the I-line was defined in NTSC/601 YIQ, so compute with the same matrix your reference uses (here BT.709). |
| **G4 Skin hue stability** | Max − min of G3 across all A-roll samples; and |Δ| between consecutive A-roll segments | Spread ≤ **5°**; consecutive |Δ| ≤ **3°** | [house, v3c-calibrated]: v3c spread is 3.8°, max consecutive Δ is 2.8°. Implements EDIT-STANDARD "no desaturation jumps" and 8.4.3. |
| **G5 Skin saturation** | Median chroma `hypot(Cb', Cr')` of the skin core | Within ± 20% of the approved reference shot's value, and globally 18–40 | [house, v3c-calibrated]: v3c 27.3–30.0. Catches the 8.5.4–6 failure modes (global desat or sat). |
| **G6 Shot-to-shot match (ΔE)** | Mean Lab of the skin core and of the wall patch per A-roll sample; ΔE76 (Euclidean) between consecutive A-roll segments | **Direct A-roll→A-roll cut:** skin ΔE ≤ **3.0**, wall ΔE ≤ **3.0**. **Across a cutaway:** skin ΔE ≤ **5.0**, wall ≤ **5.0**. Hard fail at ΔE > 7 anywhere | ΔE ≈ 2.3 is the commonly cited just-noticeable difference [industry]; the split by adjacency is [house]. v3c: direct cuts 0.87, 1.96, 2.53 pass, but **06a_not_better → 06b_listing = 4.16 skin** (face Y 137 → 142, at the 1.0 → 1.12 punch-in) = **fail / investigate**; across cutaways 2.36–6.3, plus **7.61 skin** into segment `08a` (face Y 128 vs 142, about 0.15 stop darker) = **fail**. Fix with a per-segment linear gain on the subject (8.4.22, 8.4.28). |
| **G7 Exposure stability** | Skin-core median Y per A-roll segment; ratio to the approved reference | Within ± 6% (about ± 0.1 stop) on direct cuts, ± 10% across cutaways | [house]. Same data as G6; reported separately because a dim is the most common visible jump (EDIT-STANDARD "no sudden dims"). v3c skin Y spans 128–156. |
| **G8 Black and white points** | Y percentiles per A-roll sample: p0.1 (black) and p99.9 (white); also per cutaway | A-roll: black p0.1 in **16–24** (warm lifted, never crushed below 16, never milky above 24); A-roll picture white (excluding captions: mask caption bboxes) p99.9 ≤ 235. Cutaways: black p1 ≤ 24 | [industry] 16/235 legal points; the 24 ceiling is [house, v3c-calibrated] (v3c A-roll p0.1 = 18–21). `look.py` maths: black lift (0.010, 0.007, 0.004), white ≈ 0.954 → about Y 225 before captions. |
| **G9 Contrast (anti-flat)** | (a) Waveform span `Y p99 − Y p1` on A-roll; (b) face/wall luma ratio = skin-core median Y ÷ wall-patch mean Y | (a) ≥ **130** code values (≈ 60% of the 219 legal range); (b) **2.0–3.5** | 8.7.5 defines flat as a narrow band. Thresholds are [house, v3c-calibrated]: v3c span 150–159, face/wall 2.10–3.05. A ratio below 2.0 means the wall-darkening matte failed (a regression to the raw room); above 3.5 risks the "cut-out" look. |
| **G10 Saturation limits** | Chroma p99 per A-roll frame (excluding caption and graphic bboxes) and per cutaway frame; max HSV S of skin core | A-roll chroma p99 ≤ **45**; cutaway chroma p99 ≤ **95**; nothing beyond the G2 gamut | [house, v3c-calibrated]: v3c A-roll 32–34; the 86–88 values are frames with accent graphics or end card. Catches 8.5.6 oversaturation and 8.7.15 contrast-induced saturation creep. |
| **G11 Palette roles on cutaways (60-30-10 adapted)** | Classify each cutaway pixel in HSV (H 0–360): **dominant** V < 0.25; **accent** 130° < H < 175° (the test accent's band; take it from style `colors.accent`), S > 0.35, V ≥ 0.25; **accent-white** S < 0.2, V > 0.75; **gold** 30° < H < 50°, S > 0.35; everything else is **off-palette** | Dominant **≥ 60%**; accent ≤ **20%**; white ≤ 10%; off-palette ≤ **2%** | 8.6.4–6 (dominant ≥ 60%, accent sparing) and 8.2.28 (limited palette). v3c: dark 88–91%, accent 9–11%, white < 1%, off-palette 0.1–0.5% (pass). |
| **G12 Accent = spoken item** | In each cutaway, the brightest accent bbox (connected component on the G11 accent mask, excluding the bottom glow band below 0.75·H) must overlap the text element tied to the currently spoken word in `cut_words.json`/CAPS | Overlap ≥ 1 per build step | 8.6.6 (accent on the thing that must draw attention) plus EDIT-STANDARD "cutaways build with the words". [house] |
| **G13 Jump-flash continuity** | Mean ΔE between the last frame of segment *n* and the first frame of segment *n+1* on the wall patch, for direct A-roll cuts | ≤ G6 direct-cut limit | 8.4.36. It catches a 1-frame exposure pop that mid-shot samples miss. |
| **G14 Tone-curve monotonicity (unit test on `look.py`)** | Feed a 0→1 grey ramp (and R, G, B ramps) through `grade()` with alpha = 1 and alpha = 0 and no vignette | Output strictly non-decreasing on every channel | 8.7.13–14. Cheap, deterministic, and run on every change to `look.py`. |
| **G15 Motif consistency** | Tag each cutaway element in the cutaway spec / motion log as `problem`, `solution` or `neutral`. On the element's bbox at its settle frame, measure the G11 accent-mask share | Every `solution` element has accent ≥ 5% of its bbox; every `problem` element has accent ≤ 1%; the end-card/CTA frame's accent area ≥ the median of the earlier cutaways' accent area | 8.3.10–11 (motif recurs toward the answer and peaks at the climax), 8.1.15. Thresholds [house], not yet calibrated on v3c. |

**Reference probe** (the calibration code used above, condensed; run with the reelmimic venv `~/apps/reelmimic/.venv/bin/python -I`, which has cv2 5.0):

```python
def ycc(t):   # 8-bit limited-range planes from the deliverable
    raw = subprocess.run(["ffmpeg","-v","error","-ss",f"{t:.3f}","-i",V,"-frames:v","1",
                          "-f","rawvideo","-pix_fmt","yuv444p","-"],capture_output=True).stdout
    return np.frombuffer(raw,np.uint8).reshape(3,H,W).astype(np.float32)
def rgb709(p):
    y=(p[0]-16)/219; cb=(p[1]-128)/224; cr=(p[2]-128)/224
    return np.clip(np.stack([y+1.5748*cr, y-.1873*cb-.4681*cr, y+1.8556*cb],-1),0,1)
skin_hue   = np.median(np.degrees(np.arctan2(Cr[sk]-128, Cb[sk]-128)) % 360)     # G3/G4
skin_chroma= np.median(np.hypot(Cb[sk]-128, Cr[sk]-128))                          # G5
dE         = np.linalg.norm(lab(rgb[sk]).reshape(-1,3).mean(0) - prev_skin_lab)  # G6
black, white = np.percentile(Y,.1), np.percentile(Y,99.9)                         # G8
span, ratio  = np.percentile(Y,99)-np.percentile(Y,1), np.median(Y[sk])/Y[wall].mean()  # G9
```

### B.6 Anti-patterns and failure modes

| # | Failure | Symptom (and detector) | Fix |
|---|---|---|---|
| F1 | **Untagged colour metadata** | Phone and IG players guess the transfer and primaries, so gamma or saturation shifts between devices. ffprobe shows `unknown` (G1). **Present in v3c.** | Tag `bt709` primaries, transfer and matrix, `tv` range on encode; keep x264 output limited range. |
| F2 | Global desaturation to "fix" hot skin | Lifeless face that blends into the wall, low skin chroma (G5 below band), lips dull. (8.5.4–5, 20) | Undo; balance on neutrals instead; if still hot, hue-vs-hue or a gentle reduction in the red-only range. |
| F3 | Global saturation boost to add "life" | Orange or red faces, saturated olive shirt, chroma p99 jumps (G10). (8.5.6) | Balance first (8.5.28–29); add density in skin gamma only (8.5.31). |
| F4 | Green/magenta cast (iPhone AWB drift, LED or monitor spill) | Skin hue below about 115° (magenta) or above about 131° (yellow-green) (G3); wall patch Cb/Cr off its reference. | Per-segment linear gain on neutrals (8.5.15, 26), then re-check G3. |
| F5 | Shot-to-shot dim or warm jump | ΔE spike on a direct cut (G6/G13); skin Y step > 6% (G7). In v3c, segment `08a` is about 0.15 stop darker than its neighbours, and the 06a → 06b direct cut measures skin ΔE 4.16. | Separate balance correction per segment against the hero reference, matched on the face patch, not whole frame (8.4.22–26). |
| F6 | Matching on whole-frame stats after a punch-in | Wall share drops at 1.12–1.14×, so whole-frame mean brightens or darkens and a "correction" breaks skin. | Always compare face-core and wall-patch statistics separately (8.4.23, 26). |
| F7 | Tone inversion or posterised curve | Brighter areas render darker, banding in gradients; G14 fails. (8.7.13) | Keep the curve monotonic; use smooth parametric curves (as `look.py` does). |
| F8 | Flat or milky image | Black p0.1 > 24 or span < 130 (G8/G9); the face looks grey. (8.7.5) | Lower the lift, steepen the S, pull the midtones down slightly (8.7.10). |
| F9 | Crushed blacks | Y p0.1 < 16 or large areas at exactly 16; beard and hair lose texture. (8.4.11) | Reduce the wall darkening factor or lift the black offset; never clip. |
| F10 | Wall darkened via a wide feather (the "aura") | Bright ring at the subject edge; edge-ring luma > wall luma (EDIT-STANDARD Matte gate). | Keep 1 px erode / 3 px feather; never widen (`look.py` docstring). |
| F11 | Cutaway palette creep | New colours (blue UI, red icons, stock imagery) add off-palette pixels > 2% (G11); the look becomes "visually scattered" (8.2.28). | Recolour assets to the palette; tint stock imagery to an accent duotone; reserve one deliberate break. |
| F12 | Accent overuse | The accent on everything, so accent share > 20% and no single focal point (G11/G12). (8.6.6) | Keep the accent for the spoken item, CTA and states; other elements go white or dark green. |
| F13 | Skin-coloured or olive wardrobe | Shirt and skin merge into one warm family under the warm grade (QA). (8.8) | Next shoot: a blue, teal or denim top, or a blue object behind; never key the shirt in post for this. |
| F14 | Teal shadows on A-roll (split tone) | Cool beard and hair shadows; fights "warm shadows" and causes skin hue drift. (8.7.16) | Keep the split tone off the A-roll; teal lives in the cutaways. |
| F16 | **Motif drift** | The accent used on a problem state or a competitor, or white/grey used on the fix; the colour stops meaning "the solution" (G15). (8.3.10–11, 8.1.15) | Re-colour per the role tags: accent for solution and brand only. |
| F17 | **Palette break overused** | Several off-palette moments, so none reads as deliberate; the look scatters (G11 off-palette share). (8.3.13, 8.8.14, 8.2.28) | Keep at most one break, placed at the story turn or CTA; return to the palette everywhere else. |
| F15 | WB multiply in display gamma at large magnitudes | Skin hue shifts unevenly between shadow and highlight; highlights tint differently from mids. (8.5.22) | Linear-light multiply (decode the 709 OETF, multiply, re-encode). |

### B.7 Conflicts and open questions

1. **8.8 "teal and orange" vs the house A-roll look.** 8.8 says to add blue near the skin. The house A-roll is warm on warm: brown wall, olive shirt, warm grade.
   **Call:** keep the warm A-roll for this look (the inspirations were explicit; another client's grade comes from its style profile) and get the complementary contrast from (a) the teal-green accent cutaways alternating with the warm A-roll and (b) wardrobe on future shoots.
   Do not grade blue into the A-roll (8.8.7 agrees: wardrobe, not sliders).
2. **8.6 literal 60-30-10 vs the series cutaway look (89/10/<1).** The test client's inspirations are a near-black stage with green accents, so a literal 30% secondary would mean large grey or green areas the series never uses.
   **Call:** treat 60-30-10 as role ordering (dominant ≥ 60%, accent scarce) with G11 bounds. Treat 8.6.7 (black dominant, off-white secondary, one accent) as the closest model.
3. **8.5 "do temp/tint/gain in linear" vs `look.py`, which multiplies in display gamma.** The measured effect is small (+2.4° toward the I-line), so this is not a defect today.
   **Call:** keep it, but move any future or stronger WB into linear light (F15) and add G14 as a unit test.
4. **8.4 "match on a separate balance node per shot" vs `look.py`, which has no per-segment correction.** A single take normally needs none, but v3c shows one segment about 0.15 stop dark (ΔE 7.6 across a cutaway) and one direct cut at ΔE 4.2 (06a → 06b). Before correcting, confirm the 06a → 06b value is not a sampling artefact of the punch-in moving the face-core patch.
   **Call:** add an optional per-segment `gain` dict (like `ZOOM` in `render_v2.py`), driven by G6/G7 measurements against the hero segment, applied to the subject only and before `grade()`.
5. **`look.py` comment inconsistency.** The module docstring says the wall goes down "~1.3 stops" and the inline comment says "~1.7 stops". The maths gives a luminance factor of 0.40 × (0.2126 + 0.7152·0.93 + 0.0722·0.86) ≈ 0.376, about −1.4 stops before vignette and shoulder.
   This is documentation only; correct the inline comment to about 1.4 stops.
6. **EDIT-STANDARD has no colour gates.** §4 covers Image (noise and banding) and Matte but nothing for skin hue, shot match, legal range or tags.
   **Call:** add G1, G2, G3/G4, G6/G7, G8/G9 and G11 to the §4 gate table. G1 currently fails on v3c.
7. **8.8.5 "everyone's skin hue is the same".** This is a useful simplification, but darker complexions in mixed or warm light measure a few degrees off the line. This presenter sits 2–6° toward red of 123°.
   **Call:** the gate band is ± 8°, and per-person stability (G4) matters more than closeness to exactly 123°.
8. **8.4 print emulation for "creamy highlights" vs "no added grain / single encode".** Print-emulation LUTs carry no grain, so there is no conflict. But `look.py`'s shoulder already gives creamy highlights (white ≈ 0.954), so a LUT is unnecessary. Do not add one.
9. **Open: caption white vs A-roll white point.** Captions are pure white (Y 235), about 10 code values above the graded picture's white (≈ 225). That separation is good for legibility (8.6.11 accessibility); G8 therefore masks caption bboxes when measuring the picture white.
10. **8.3 has been re-sourced** (It's Just Cinema replaced the title-cards-only transcript). Its black-and-white-for-realism (8.3.15–16) and its whole-scene saturated washes (8.3.7) conflict with the house warm, natural A-roll. **Call:** do not use either. Its motif trail (8.3.11) and its one-scene palette break (8.3.13) agree with 8.8.14–15, and they are adopted through G15 and F17.
11. **8.3.11 "the motif peaks at the climax" vs G11's accent cap (≤ 20%).** A peak could push the end card over 20% accent. **Call:** the peak is relative (G15 compares against the median of earlier cutaways), and the G11 cap still applies, so the end card shows the most accent without going over the limit.

---

## Per-video rule counts
| Video | Rules |
|---|---|
| 8.1 StudioBinder, Color Psychology Ep. 5 | 19 |
| 8.2 In Depth Cine, Using Colour To Tell A Story (weak match, on topic) | 33 |
| 8.3 It's Just Cinema, The Power of Colour in Cinema (replacement; was a title-cards-only transcript with 0 rules) | 17 |
| 8.4 Darren Mostyn, Pro Color Match Shots | 37 |
| 8.5 Waqas Qazi, Skin Tones Look Fake | 37 |
| 8.6 Kittl, 60-30-10 Color Rule | 11 |
| 8.7 Graded by Oscar, Why Your Videos Look Flat | 27 |
| 8.8 Matti Haapoja, Teal & Orange | 21 |
| **Total** | **202** (was 185) |
