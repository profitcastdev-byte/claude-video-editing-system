# Module 7: Shot Composition, Framing & Camera Language

> **Note (style profiles).** This module was written while CVES was tested on its first ad. Its research rules are universal; where it speaks of the "house" look or a house number for a per-client choice (palette, accent colour, grade, transition kinds, cutaway share, caption position, bed level), read it as the value from the client's style profile (`docs/STYLE.md`). The black stage / green accent / warm moody A-roll measured here is now the optional preset `profitcast-dark`, not the default.

Dissected from 8 transcripts in `transcripts/7 Shot Composition, Framing & Camera Language/` (11,099 words total, all read in full).
Target use: the CVES selfie-ad editor, which edits one fixed, front-facing 9:16 take (1080×1920 output, 23.976 fps in the first
test edit). The only framing controls are punch-in scale and centre (`render_v2.py` `ZOOM`, `SNAP`, `scale_about`), the
position of the YuNet face box in the output frame, headroom, the grade/vignette, rotoscoped depth layers, and full-screen cutaways.

Timestamps `[mm:ss]` are the start of the transcript chunk that holds the idea (chunks are ~30 s). Rule ids are `video.rule`
(e.g. `7.5.7`).

---

## A. Per-video dissection

### 7.1 Ultimate Guide to Film Composition & Framing: Key Elements Explained [Shot List Ep. 11]
- **Source:** id 7.1 · StudioBinder · https://www.youtube.com/watch?v=hUmZldt0DTg · 1069 s (17:49) · 2,254 words · search match 1.0 (correct video).
- **Thesis:** Composition is the arrangement of, and relationship between, the elements in a frame; ten elements (points, lines,
  shapes, texture/pattern, space, depth, balance, angle, colour, tone) are levers for directing the viewer's eye and setting meaning.

1. `[00:00]` Treat the shot as the base unit: films are built from sequences, sequences from scenes, scenes from shots.
2. `[00:30]` Define composition as the arrangement of elements in an image.
3. `[01:01]` Compose relationships, not just contents: meaning comes from how the elements relate, not only from what is included.
4. `[01:01]` Make a single frame tell a story: characters, situation, power dynamic, drama, theme and movement can all be in one image.
5. `[01:30]` Compose for the aspect ratio: portraits sit naturally in a vertical frame and landscapes in a horizontal one; a squarish and a rectangular frame need different choices.
6. `[02:00]` Use points (intersections, even a small dot) as focal points to pull the eye; composition is "all about directing the viewer's eye".
7. `[02:31]` In wide shots, keep the canvas uncluttered so the eye goes straight to the point.
8. `[02:31]` A point can be an object detail (e.g. the tip of a sword) that the frame aims the eye at.
9. `[02:31]` Rule of thirds: place the subject on one of the four intersections of the horizontal and vertical third lines.
10. `[03:02]` Golden triangle: draw one corner-to-corner diagonal, then lines from the other two corners meeting it at right angles, giving two balanced focal points.
11. `[03:30]` Read line direction as mood: vertical = height and strength, horizontal = distance and calm, diagonal = off-tilt energy, curved = grace.
12. `[03:30]` Use leading lines to pull the eye in a direction (Nolan uses hallway lines to aim at the subject).
13. `[04:02]` Lines can be built from props and light: ropes and lens flares point at the opponent (Raging Bull).
14. `[04:31]` Clean geometric shapes (triangles, circles, squares) give unity and a tidy, ordered feel; irregular or organic shapes feel natural or chaotic.
15. `[04:31]` Use shapes to make frames within frames, a smaller area of focus inside the image.
16. `[05:01]` A frame within a frame can feel claustrophobic or comforting depending on its shape, placement and the scene.
17. `[05:30]` Every object has texture; texture (including texture made by light) can make a subject pop from the background or blend into it.
18. `[06:00]` Busy texture can signal opulence (Barry Lyndon); contrasting textures between characters signal their personalities (WALL-E vs EVE).
19. `[06:00]` Repetition (pattern) can suggest power, control, harmony or insanity.
20. `[06:30]` Break a pattern to create interest and meaning; a pattern can also disorient (the carpet in The Shining).
21. `[07:00]` Split space into positive (subject) and negative (empty space around it); the ratio sets the mood.
22. `[07:00]` The larger the subject in frame, the more important it is: extreme wides isolate and make the subject vulnerable, extreme close-ups empower.
23. `[07:32]` The location of negative space matters, not only the amount.
24. `[07:32]` Keep headroom (negative space above the head) "usually kept to a minimum".
25. `[07:32]` Give lead room / looking room: more negative space in front of the subject than behind.
26. `[07:32]` Headroom and lead-room rules can be broken on purpose for effect.
27. `[08:01]` Fill the frame (subject takes most or all positive space) for sensory overload or chaos.
28. `[08:01]` A simplified, emptier frame reads as soothing, or as sad.
29. `[08:31]` Build depth with three planes (foreground, middle ground, background) to layer meaning and relationships.
30. `[08:31]` Shallow focus isolates the subject from the other planes; the eye prioritises what is in focus.
31. `[09:00]` Changing focus during a shot (rack focus) moves attention further; an object can be closest to the lens yet ignored until focus lands on it.
32. `[09:00]` Deep focus allows several layers of attention at once and a visible hierarchy of power (Citizen Kane: mother foreground, father middle, child background).
33. `[09:30]` Keep the frame balanced as the default: a subject frame-right with nothing on the left feels unbalanced.
34. `[09:30]` A foreground subject with nothing in the background also feels unbalanced.
35. `[10:01]` Rule of odds: an odd-numbered group of subjects is more pleasing than an even one.
36. `[10:30]` Golden ratio is 1 : 1.618 (Fibonacci); dividing a golden rectangle repeatedly gives the golden spiral, used by Dalí and Cartier-Bresson for natural balance. (Transcript says "the number five", almost certainly a mis-hearing of "phi".)
37. `[11:00]` Draw a horizontal line at the golden ratio of the frame height to find an ideal place for the subject's eyes or the horizon. (Derived: in a 1920 px frame that line is at 1920 / 2.618 ≈ 733 px from the top, i.e. 38.2 %.)
38. `[11:30]` Symmetry is another form of balance (Wes Anderson uses symmetric framing instead of thirds or golden ratio).
39. `[11:30]` Use an unbalanced frame only when you want the audience uneasy.
40. `[12:01]` Angle is under-used; most compositions keep the camera parallel to the ground.
41. `[12:01]` High angle makes the subject smaller and less powerful; low angle the opposite; overhead gives a detached, objective view.
42. `[12:32]` A Dutch (tilted) angle puts the audience on edge or gives kinetic energy, like an unbalanced frame.
43. `[13:00]` Use colour to direct the eye; choose a scheme (monochromatic, analogous, complementary, triadic) deliberately.
44. `[13:30]` Colour can override every other compositional cue: a bright green dress against a red, busy background makes Mrs Chan the subject (In the Mood for Love).
45. `[13:30]` Tone (brightness and contrast) is its own lever; bright and dark images read differently, and mixing both gives a more complex message.
46. `[14:01]` The eye goes to the brightest part of the image: light the subject and surround it with darkness to hold focus.
47. `[14:01]` High tonal contrast can also carry theme (Black Swan: good vs evil).
48. `[15:03]` Combine elements: colour can make patterns, tone can make balance, shapes can make depth.
49. `[15:30]` Composition can make the audience gather clues alongside the character (Skyfall sequence).
50. `[17:02]` Plan composition ahead (storyboard) so each element is used on purpose, not by accident.

### 7.2 Ultimate Guide to Camera Shots: Every Shot Size Explained [The Shot List, Ep. 1]
- **Source:** id 7.2 · StudioBinder · https://www.youtube.com/watch?v=AyML8xuKfoc · 763 s (12:43) · 1,644 words · search match 0.98 (correct video).
- **Thesis:** Each shot size has a storytelling job; choosing the most dramatically valuable size for each moment sets the rhythm, tone and meaning of a scene.

1. `[00:30]` Shot choice sets the rhythm, tone and meaning of a scene.
2. `[01:02]` Make picking the most aesthetically and dramatically valuable shot for each moment the top priority.
3. `[01:02]` The establishing shot is the most common opener for a scene or a whole film.
4. `[01:30]` Make an establishing shot wide enough to show geography, time of day and the scale of subjects in their environment; it often bridges scenes.
5. `[02:01]` Establishing shots are crucial when a new world must be introduced (sci-fi; Blade Runner 2049 opens with a series of them).
6. `[02:32]` Use an establishing shot to mark a move to a new location or to introduce key details of the place.
7. `[02:32]` Follow the establishing shot with a master: it confirms the geography, who is in the scene and where they stand relative to each other.
8. `[03:01]` Playing a scene in the master stresses togetherness (Godfather II family dinner).
9. `[03:30]` Leaving the master for a separate framing at a dramatic beat isolates a character ("from this... to this"), and the emptiness around him is felt more.
10. `[04:05]` The master gives the editor something to cut out to when needed.
11. `[04:31]` Wide shot = subject far from camera to show their relationship to the environment; it is about scale, whereas the establishing shot is about location.
12. `[04:31]` Use a wide to make a subject look lost, lonely or overwhelmed, or to comment on their place in the environment.
13. `[05:01]` Ending a scene on a wide rather than close-ups can leave characters together yet isolated (Phantom Thread).
14. `[05:01]` Use the wide for spatial relationships and for statements made with distance, depth or size.
15. `[05:33]` Full shot: the whole body from the top to the bottom edge of the frame; centring is not required but is common.
16. `[06:01]` Use a full shot for statements about physicality: posture, wardrobe, a character "in all their glory", while still tight enough to read the face.
17. `[06:30]` Medium full / cowboy: top of the head to just below the waist (as stated; named after gun-holster height).
18. `[07:01]` Use the cowboy framing to present a subject as confident, dangerous or confrontational.
19. `[07:01]` The medium shot is the most popular size because it is neutral: neither dramatic like a close-up nor distancing like a wide.
20. `[07:01]` The medium shot shows a person at the size we see people when we talk to them.
21. `[07:30]` Medium shot composition: from above the waist (below the chest) to just above the head.
22. `[07:30]` Shot-size rules apply equally to animation (and so to graphic and composited frames).
23. `[08:02]` A medium shot can carry props, a screen and the subject's reaction in one frame (Coco).
24. `[08:31]` Use the medium to dig into a subject without losing their physicality or environment, as a middle ground that is neither jarring nor dramatic.
25. `[08:31]` Medium close-up (MCU): mid-chest to just above the head.
26. `[09:01]` Use the MCU to reduce distraction and prioritise story and character detail; intimate without losing physicality.
27. `[09:31]` An MCU leaves room for a key prop beside the face and the reaction to it (Thanos and the gauntlet).
28. `[10:03]` The close-up is the most powerful tool for showing a change in emotion or a dramatic beat.
29. `[10:03]` Shoot close-ups mostly at eye level.
30. `[10:03]` The close-up gives a front-row seat to thoughts and feelings; it builds empathy, especially at moments of decision or anxiety.
31. `[10:31]` Extreme close-up (ECU) isolates one area (lips, ears, nose), most often the eyes.
32. `[11:01]` Cutting back and forth between ECUs (eyes) and the action builds tension (Kill Bill).
33. `[11:01]` Use an insert shot to show a prop's function or a vital detail.
34. `[11:36]` ECU and insert are the strongest tools for emphasis: the most intimate, dramatic and potentially startling sizes. Use them for emphasis, not as default.

### 7.3 Ultimate Guide to Camera Angles: Every Camera Shot Explained [Shot List, Ep. 3]
- **Source:** id 7.3 · StudioBinder · https://www.youtube.com/watch?v=wLfZL9PZI9k · 812 s (13:32) · 1,584 words · manual replacement, match 1.0. On topic (the curriculum named "Ep. 2"; this is the camera-angles episode, Ep. 3).
- **Thesis:** Shot size picks what we look at; camera angle and height decide how we perceive it. Nine angles/heights each carry a power or mood message.

1. `[00:00]` After deciding shot size and framing, decide camera height and angle as a separate choice.
2. `[00:32]` Size and framing isolate what we see; angle sets how we are meant to perceive it: an extra layer of meaning on every shot.
3. `[01:00]` Low angle = any shot from below the subject's eyeline looking up.
4. `[01:35]` Use low angles to make a subject more powerful (heroes and villains); the degree can be subtle or extreme.
5. `[01:35]` Angle effects apply to non-human subjects too (the monolith in 2001).
6. `[02:02]` Let the angle tie the other cues together (colour, smoke, darkness and expression all read "villain" because of the low angle on Scar).
7. `[02:32]` High angle = complementary to the low angle; it diminishes the subject, making them look weak or vulnerable.
8. `[02:32]` Pair high and low angles in one scene to heighten a power imbalance between subjects.
9. `[03:00]` Aerial = extreme high angle, for establishing cities and landscapes or showing characters moving through a larger world.
10. `[03:33]` A threat shot to dwarf the heroes uses an extreme high angle on them (Avengers).
11. `[04:01]` As a high angle approaches 90° above the subject it becomes the overhead (bird's-eye / God's-eye) shot, looking straight down.
12. `[04:01]` Use overheads to show complex movement, to suggest the divine, or to show the details of a crime scene.
13. `[04:32]` An overhead without context can show a disconnected character (The Master).
14. `[05:00]` Dutch angle = horizontal axis skewed; it creates unease or mania.
15. `[05:30]` Use the Dutch angle to magnify tension, increasing the tilt as tension rises (Do the Right Thing).
16. `[06:07]` A Dutch angle needs careful set-up for maximum impact (Mission: Impossible reference).
17. `[06:32]` Eye level is the most common height and the most natural way for an audience to regard a character.
18. `[07:01]` Eye level imposes no judgment on the character, but can still be engaging and dynamic.
19. `[07:01]` Eye level plus breaking the fourth wall (talking straight into the lens) creates an instant connection and rapport (Wolf of Wall Street monologue).
20. `[07:31]` Shoulder level is just below the eyes and the runner-up to eye level.
21. `[08:00]` Shoulder level gives the illusion of a slight low angle without its heavier connotations.
22. `[08:00]` Shoulder level is common in conversation and often becomes an over-the-shoulder (OTS); it can show a height difference, read as a power difference.
23. `[08:32]` A barely upturned eyeline can make an affectionate glance warmer.
24. `[08:32]` Camera placement can connect or disconnect characters (Westworld OTS).
25. `[09:03]` Hip level lives in westerns, paired with the cowboy shot, because holsters sit at hip height.
26. `[09:30]` Alternating hip-level holster shots with eye-level ECUs builds an exciting, tense sequence (Good, the Bad and the Ugly).
27. `[10:00]` Knee level often doubles as a low angle.
28. `[10:00]` Use knee level to track a character through an environment or to show details a wider shot would miss (Forrest Gump).
29. `[11:02]` Ground level = camera on (or below) the ground; it doubles as a low angle if tilted up at all.
30. `[11:02]` Use ground level as a stylish way to track movement or capture setting details.
31. `[11:32]` A long ground-level move can hold attention through pattern and sound design (The Shining tricycle shot).
32. `[12:00]` Choose angle by the message it sends; do not settle for the expected.
33. `[12:32]` Mix and match shot sizes, framing and angles deliberately.

### 7.4 The 180 Degree Rule in Film (and How to Break The Line)
- **Source:** id 7.4 · StudioBinder · https://www.youtube.com/watch?v=iW0bKUfvH2c · 345 s (5:45) · 808 words · search match 0.73. On topic for the 180° rule; the curriculum's "eyeline match" half is covered only as opposed eyelines (eyeline match proper is in 7.5).
- **Thesis:** Keep cameras on one side of the line between subjects to preserve orientation and screen direction; break it on purpose for chaos, or bend it with a neutral shot or a camera move.

1. `[00:01]` If an edit feels "off" and disorienting, check first for a broken 180° rule.
2. `[00:01]` The 180° line is an imaginary straight line drawn between two subjects in a scene.
3. `[00:31]` Keep every camera set-up on the same side of that line; otherwise you have "crossed the line".
4. `[01:02]` Following the rule establishes orientation and screen direction.
5. `[01:02]` With the line respected, one subject looks camera-right and the other camera-left, so they appear to look at each other (Heat).
6. `[01:32]` For more than two people, treat it like a stage play: keep the camera "in the seats".
7. `[02:00]` Following the line gives tranquillity; breaking it gives chaos.
8. `[02:00]` A deliberate break shows both subjects looking camera-left, used to express a chaotic situation (25th Hour, DEA raid).
9. `[02:32]` Cross the line at a dramatic beat (a reach across the table) to shift tone and the power relationship (Paper Moon).
10. `[03:00]` Bend the rule with a neutral shot: cut to a shot directly on the line, which resets it.
11. `[03:30]` After the neutral shot, the eyeline can flip direction (left-to-right becomes right-to-left) without confusing (Inglourious Basterds).
12. `[03:30]` Bend the rule with camera movement: move the camera across the line on screen so the audience sees the change.
13. `[04:01]` Motivate a line crossing by an emotional change (moving from the characters' backs to their fronts = from suspicion to openness).
14. `[04:34]` The rule protects you; breaking it safely can give unique results.
15. `[04:34]` Plan line breaks deliberately in the shot list and storyboard.
16. `[05:02]` Know the rules before breaking them.

### 7.5 The 30-Degree Rule | Continuity & Jump Cuts
- **Source:** id 7.5 · Zeeo Zia · https://www.youtube.com/watch?v=1XqrwZmJpAA · 394 s (6:34) · 1,282 words · manual replacement, match 1.0. On topic (the curriculum named Filmmaker IQ; this is a narrated explainer on the same rule). It names no shot-size equivalent of the 30° rule.
- **Thesis:** A cut between two nearly identical shots of the same subject reads as a glitch (jump cut); move the camera ≥ 30°, vary shot size, shoot coverage and cut on action so the cut disappears.

1. `[00:30]` Recognise the jump cut: the subject seems to teleport or twitch a few inches between cuts because the camera moved only slightly.
2. `[00:30]` A jump cut pulls the viewer out of the story and reminds them they are watching constructed media.
3. `[01:00]` Cause: two nearly identical shots placed next to each other on the timeline; one of the most common beginner mistakes.
4. `[01:00]` The framing changes enough to distract the eye but not enough to read as a new, intentional perspective.
5. `[01:00]` Jump cuts are acceptable as a deliberate style (vlogs, specific creative edits) but in standard narrative work avoid them.
6. `[01:32]` The goal of continuity editing: keep the audience on the story and never on the cut.
7. `[01:32]` 30° rule: when cutting between two angles of the same subject, the second camera must be at least 30° from the first.
8. `[01:32]` The minimum change makes a clear geometric shift in perspective that the brain reads as intentional, not as "a glitch in the matrix".
9. `[02:00]` A small change (a few centimetres between takes) gives the amateur jump cut; a ≥ 30° change gives an invisible, smooth edit.
10. `[02:30]` Shoot coverage: the same action from several distinct perspectives; pros almost never rely on one angle.
11. `[03:01]` Coverage list: wides to establish space, mediums, close-ups for emotion, over-the-shoulders to connect characters, inserts of hands and objects.
12. `[03:01]` Varied angles of the same action are what make smooth transitions possible; they give the editor a menu to bridge gaps.
13. `[03:30]` Match on action, step 1: the subject begins a motion (reaching for a cup).
14. `[03:30]` Step 2: cut during the fluid motion, not before or after it.
15. `[03:30]` Step 3: complete the action in the new shot, framed from a clearly different angle; the eye follows the motion, not the edit.
16. `[04:00]` Eyeline match: when a character looks off screen, the next shot shows what they are looking at.
17. `[04:00]` Place the looked-at object in the direction of the gaze.
18. `[04:30]` Eyeline match maps spatial relationships between characters and objects without dialogue.
19. `[05:02]` Anti-pattern: two nearly identical medium shots a few centimetres apart.
20. `[05:02]` Anti-pattern: no inserts of the relevant objects (the notebook, the desk).
21. `[05:02]` Anti-pattern: cutting when everything in frame is still; stillness makes the jump cut obvious ("a bad security camera glitch").
22. `[05:02]` Pro version: 30° changes, a range of shot sizes (wide mixed with tight close-ups), and cutting on the action (sitting down).
23. `[05:30]` "The best edit is the one the audience never notices."
24. `[05:30]` You cannot force a smooth cut without the right footage; smooth editing starts on set with camera placement and coverage. Film with the edit in mind.
25. `[06:01]` Plan the invisible edits before turning the camera on.

### 7.6 How to Use Walter Murch's Eye Trace to "Direct the Eye" with Cinematic Editing
- **Source:** id 7.6 · StudioBinder · https://www.youtube.com/watch?v=xUK64UkTmW0 · 371 s (6:11) · 805 words · manual replacement, match 1.0. On topic (the curriculum named Channel Criswell). Murch is in the title only; the transcript does not cover Murch's "rule of six" or cross-cut eye-trace theory in detail, so nothing from it is added here.
- **Thesis:** Decide where the viewer must look and put the important information there, steering the eye with three tools: motion, position and colour.

1. `[00:01]` Leave nothing to chance: draw the eye to a part of the frame, then place the important information there.
2. `[00:31]` Eye trace = intentionally drawing the viewer's eyes to a chosen part of the frame.
3. `[00:31]` How a director steers the eye is a large part of their style.
4. `[01:01]` Three methods: motion, position, colour.
5. `[01:01]` Motion can be camera movement, performer movement, or "a little tiny graphic" moving across the screen.
6. `[01:01]` Position: place new imagery where the viewer's eyes already are; the chance they look elsewhere is "slim to none".
7. `[01:30]` Colour evokes specific emotions in the viewer.
8. `[02:01]` The eye follows a moving subject through the frame (the waiter).
9. `[02:01]` Support motion with a shot size close enough to signal the mover's importance, shallow depth of field so attention does not stray, and camera movement paired with the actor's movement.
10. `[02:33]` Use the moving element to lead the eye to a spot, then reveal the key subject in that spot (the waiter leads us to Schindler).
11. `[02:33]` Merge several beats into a single set-up where possible.
12. `[03:01]` Map the frame's vectors in advance (storyboard) so you know where the viewer's eyes will be, and when.
13. `[03:33]` A single coloured element in an otherwise neutral frame gets singular focus even amid chaos (the girl in the red coat).
14. `[04:00]` Eye trace is a strategy, not a rule: ask what the focus of each shot should be, then use the three methods.
15. `[04:34]` Combine motion, position and colour for the strongest effect.
16. `[05:31]` Restraint is power: not using every bell and whistle when you could is what reads as real cinematic power.

### 7.7 Learn 42 Composition Techniques in 8 Minutes
- **Source:** id 7.7 · Liam S. Photography · https://www.youtube.com/watch?v=HBWYieo5RmU · 524 s (8:44) · 1,490 words · manual replacement, match 1.0. On topic for composition (the curriculum named Wolfcrow's film-specific video); it is about still photography, so nothing here covers motion or cutting.
- **Thesis:** A catalogue of 42 composition techniques (placement grids, balance, lines, depth, light and colour) that each set a feeling or steer the eye.

1. `[00:00]` Golden ratio: placing the subject on one of the four golden-ratio points makes the image feel naturally balanced.
2. `[00:31]` Rule of thirds: divide into three slices each way; place the subject on one of the four intersections.
3. `[00:31]` Symmetry: if nothing is fully symmetric, use water or another reflective surface as a mirror.
4. `[00:31]` Asymmetry still feels balanced when visual interest is equal on both sides.
5. `[01:01]` Rule of odds: three subjects feel more dynamic than four.
6. `[01:01]` Fill the frame by getting closer to the subject.
7. `[01:01]` Negative space (not filling the frame) shows scale or isolation.
8. `[01:30]` Rule of space: leave extra space in the direction the subject looks or moves.
9. `[01:30]` Frame within the frame: use trees, windows, arches to frame the subject.
10. `[01:30]` Golden triangle, two uses: put the subject on one of the two intersection points, or align elements with the diagonals.
11. `[02:00]` Centre-eye dominance: in a close portrait, put the eye nearer the camera at the horizontal centre of the frame for balance and a stronger connection with the viewer.
12. `[02:00]` Leading lines: natural lines that direct the eye to the subject.
13. `[02:00]` Implied lines: lines suggested by how elements are arranged, working like leading lines.
14. `[02:31]` Converging lines create depth and a sense of journey even with no main subject.
15. `[02:31]` Diagonals in the same direction create movement; in opposing directions, tension.
16. `[02:31]` Horizontal lines look stable, calm and peaceful.
17. `[03:00]` Vertical lines add strength and power.
18. `[03:00]` S-curves give elegance and flow; C-curves give harmony or softness.
19. `[03:00]` Shapes: triangles add stability or tension, circles harmony, rectangles and squares order.
20. `[03:30]` Point of view: from above = small and vulnerable, from below = huge and powerful, eye level = most natural, the viewer connects directly.
21. `[03:30]` Use foreground, middle ground and background together for depth.
22. `[04:01]` Overlapping elements add depth.
23. `[04:01]` Scale contrast: play tiny against large.
24. `[04:01]` Leading foreground interest: an object or pattern in the front draws the eye in and on toward the subject.
25. `[04:30]` Visual balance: even out visual weight on both sides; it does not need identical objects.
26. `[04:30]` Several smaller elements can balance one large element.
27. `[04:30]` Bright or saturated elements feel heavier: a small bright area can balance a large dark one.
28. `[04:30]` A busy, detailed area carries weight.
29. `[04:30]` Elements near the frame edge feel heavier than those in the centre; even a sliver at the edge can balance a scene.
30. `[05:00]` Repetition of shapes, colours or patterns creates rhythm and cohesion.
31. `[05:00]` Break the pattern: one element that differs instantly draws attention.
32. `[05:00]` Flow / visual path: combine implied lines, repetition and foreground interest into one path for the eye.
33. `[05:31]` Dynamic tension comes from opposing diagonals, from violating the rule of space (no room to look or move into feels uncomfortable), and from shapes about to collide.
34. `[06:04]` Chiaroscuro: bright areas next to deep shadow for depth and drama.
35. `[06:04]` High key (bright, few shadows) feels clean and cheerful; low key (mostly dark) feels dramatic and mysterious; both are about overall level, not contrast.
36. `[06:31]` Silhouette: main light behind the subject, subject near black against a bright background.
37. `[06:31]` Complementary colours (opposite on the RYB wheel: green/red, blue/orange) give energy and excitement.
38. `[07:02]` Analogous colours (neighbours on the wheel) give a cohesive, harmonious feel.
39. `[07:02]` Triadic colours (evenly spaced) give a vibrant, balanced palette.
40. `[07:02]` Warm + cool: calm, distant cool tones with inviting, energetic warm tones.
41. `[07:31]` Colour dominance: let one colour take over; monochrome is the extreme (100 % one colour), and it shifts attention to shape, texture and light.
42. `[07:31]` Pop of colour: a neutral or muted image with one bright colour that jumps out.
43. `[08:05]` Juxtaposition: put opposites together (new/old, rich/poor, modern/traditional) to highlight contrast.
44. `[08:05]` Storytelling composition: arrange elements to imply a narrative.
45. `[08:05]` Minimalism: keep a few essential elements and remove anything that does not add to the story or impact.

### 7.8 How Pro Editors Use B-Roll
- **Source:** id 7.8 · Inside The Edit (Paddy Bird) · https://www.youtube.com/watch?v=9jRZIqPQHm8 · 592 s (9:52) · 1,232 words · manual replacement, match 1.0. On topic (the curriculum named Motion Array).
- **Thesis:** B-roll is chosen by its connection to the spoken line: primary (literal), secondary (symbolic), wallpaper (vague) or context-building (mood for a new scene). What matters is the editor's intent, not the shot type.

1. `[00:00]` B-roll = secondary images of a person, place or thing that illustrate what the character or voice-over is saying.
2. `[00:30]` At a high level, B-roll is about nuance, variety and above all purpose.
3. `[01:02]` The most basic job of B-roll is to illustrate what the words are talking about.
4. `[01:30]` "Tell me, then show me": the interview line tells, and the B-roll that follows shows. This is the most basic structure in editing.
5. `[03:02]` Master the basic mechanics (where B-roll goes around the dialogue, and in what order) before any higher theory; without them theory "means zero".
6. `[03:30]` For each B-roll shot, ask how strongly it connects to the line it covers.
7. `[03:30]` Primary connection: a literal match ("I love coffee", cut to coffee being made). It is the most repeated mini-structure in editing.
8. `[04:00]` Land the primary cut on the phrase it illustrates (the coffee shot arrives on "cup of coffee").
9. `[04:30]` Secondary connection: symbolism or visual metaphor (talk of peace, cut to doves being released).
10. `[05:00]` A secondary shot suggests as well as shows, and works on the audience in a different way; the choice is about intent.
11. `[05:00]` Classify your intent for each B-roll shot or mini-sequence around each line before placing it.
12. `[05:32]` Wallpaper B-roll: only a vague link between what is said and what is seen, common in observational documentary and reality TV.
13. `[07:30]` Context B-roll: at a new scene, location, character or event, build visual context first to connect the viewer emotionally to the place or person.
14. `[08:00]` Choose context B-roll for mood and tone, "painting a little atmospheric portrait".
15. `[08:30]` It is not the type of B-roll shot that matters but how the editor uses it.

**Rule counts:** 7.1 = 50 · 7.2 = 34 · 7.3 = 33 · 7.4 = 16 · 7.5 = 25 · 7.6 = 16 · 7.7 = 45 · 7.8 = 15 · **total 234**.

---

## B. Module synthesis

### B.1 Best practices (de-duplicated, ordered by impact)

| # | Rule | Sources | Scope |
|---|---|---|---|
| 1 | Never cut between two near-identical framings of the same subject; each cut must make a clear geometric change (≥ 30° in angle, or a clear size change) or be covered. | 7.5.1–9, 7.5.19 | UNIVERSAL (except deliberate jump-cut style) |
| 2 | Decide what the viewer must look at in every shot and put the key information where their eye already is; carry the focal point across the cut. | 7.6.1–2, 7.6.6, 7.6.10, 7.6.14, 7.1.6 | UNIVERSAL |
| 3 | Make the subject the brightest and most contrasting region; the eye goes to the brightest part of the frame. Lit subject, darker surround. | 7.1.46, 7.7.34, 7.7.27 | UNIVERSAL |
| 4 | Talk to the lens at eye level for instant connection; eye level imposes no judgment. Avoid unmotivated high angles (they diminish) and low angles. | 7.3.17–19, 7.7.20, 7.2.29, 7.1.41 | UNIVERSAL for direct-address |
| 5 | Put the eyes on a strong horizontal line: the top third (33.3 %) or the golden-ratio line (38.2 % from the top). | 7.1.9, 7.1.37, 7.7.1–2 | UNIVERSAL |
| 6 | Keep headroom to a minimum. | 7.1.24, 7.1.26 | UNIVERSAL default, breakable |
| 7 | Keep the frame balanced; an off-centre subject with nothing on the other side feels wrong. Centre a close portrait on the dominant eye, or balance it with visual weight (bright/saturated/busy/edge elements). | 7.1.33–34, 7.1.38, 7.7.4, 7.7.11, 7.7.25–29 | UNIVERSAL |
| 8 | Use shot size as the emphasis dial: MCU/medium for neutral delivery, close-up for emotional or decision beats, ECU/insert for the single strongest emphasis (startling, so rare). | 7.2.19, 7.2.25–34, 7.1.22 | UNIVERSAL |
| 9 | Mix shot sizes and cut on motion, not on stillness; stillness makes a jump obvious. | 7.5.13–15, 7.5.21–22, 7.3.33 | UNIVERSAL |
| 10 | Every B-roll/cutaway needs a stated intent and connection to its line: primary (literal) by default, secondary (metaphor) by choice, context for a new place or person. "Tell me, then show me", landing the shot on the phrase. | 7.8.3–14 | UNIVERSAL |
| 11 | Use one moving element to lead the eye, then reveal the key information where the motion ends. | 7.6.5, 7.6.8–10 | UNIVERSAL |
| 12 | One pop of colour in a muted frame takes focus over everything else; colour can override other cues. | 7.1.44, 7.6.13, 7.7.42 | UNIVERSAL |
| 13 | Keep the canvas uncluttered; minimalism: remove anything that does not add to story or impact; restraint reads as power. | 7.1.7, 7.7.45, 7.6.16 | UNIVERSAL |
| 14 | Leave lead/looking room on the side the subject faces or moves toward; no room feels uncomfortable (dynamic tension). | 7.1.25, 7.7.8, 7.7.33 | UNIVERSAL |
| 15 | Build depth with foreground / middle / background layers and overlap; focused layers get priority. | 7.1.29–32, 7.7.21–22 | UNIVERSAL |
| 16 | Keep screen direction and orientation consistent (180° rule); cross the line only deliberately, at a dramatic beat, via a neutral shot or a visible move. | 7.4.1–16 | CONTEXT: multi-subject or multi-camera scenes |
| 17 | Eyeline match: if someone looks off screen, the next shot shows what they look at, placed in the direction of the gaze. | 7.5.16–18 | CONTEXT: shots where the speaker looks away |
| 18 | Establish location first when a new world or place is introduced; a master gives the editor something to cut out to. | 7.2.3–10, 7.8.13 | CONTEXT: new location/scene |
| 19 | Keep the horizon level; a Dutch tilt only for unease, mania or rising tension. | 7.1.42, 7.3.14–15 | CONTEXT |
| 20 | Shoot (or build) coverage with the edit in mind: wides, mediums, CUs, inserts. Plan invisible edits before the camera rolls. | 7.5.10–12, 7.5.24–25, 7.1.50, 7.4.15 | UNIVERSAL (pre-production) |
| 21 | Lines and shapes carry mood: vertical = strength, horizontal = calm, diagonal = energy, curves = grace; geometric = order. Use them in graphic layouts. | 7.1.11–16, 7.7.12–19 | CONTEXT: graphics, set design |
| 22 | Use repetition for rhythm and break it to draw attention to one element. | 7.1.19–20, 7.7.30–31 | UNIVERSAL |
| 23 | Rule of odds: groups of three over groups of four. | 7.1.35, 7.7.5 | CONTEXT: lists, icons, product groups |
| 24 | Colour schemes set feel: complementary = energy, analogous = harmony, colour dominance/monochrome = unity and focus on shape. | 7.1.43, 7.7.37–42 | UNIVERSAL |
| 25 | Fill the frame for intensity/overload; a simplified, emptier frame for calm or sadness; subject size = importance. | 7.1.21–22, 7.1.27–28, 7.7.6–7 | UNIVERSAL |

### B.2 Short-form ad translation (9:16, 30–60 s, single fixed selfie take)

- **R1 (no near-identical cuts) → punch-in alternation.** No second camera means no 30° move. The only geometric change is scale
  (and the reframing a scale change brings). Each uncovered A-roll→A-roll cut must change the face size by the house step
  (≈ 1.15×, EDIT-STANDARD §1) or be hidden under a cutaway. Cut during head or hand motion, never in a still pose (7.5.21).
  *Observation from the current v2 files:* `render_v2.py` uses 1.12–1.14 for the punched segments and adds a 1.5 % creep
  across each segment, so the real step at a cut can drop to about 1.10 (a 1.0 segment ends at 1.015, the next starts at 1.12).
  Measure the step at the actual cut frames, not from the `ZOOM` table.
- **R2 (eye trace) → keep the face anchored across punches; land cutaway content near the eyes.** `scale_about` scales around the
  face centre, so the eyes barely move across a punch: good. On A-roll↔cutaway cuts, the first element that moves in the cutaway
  should start near where the eyes were (upper-middle of frame), and the face on return should sit where the cutaway's last active
  element was, or the whip should carry the eye there.
- **R3 (brightest = subject) →** the warm, dark grade and vignette already do this (EDIT-STANDARD §2). Check that no graphic,
  caption plate or behind-the-head card is brighter than the face over a large area during A-roll.
- **R4 (eye level) → a shoot-brief item, not an edit fix.** A phone held high gives a diminishing high angle; a phone on the desk gives an
  unflattering low angle. The editor can only flag it.
- **R5 (eye line on a third) →** in 9:16 the top-third line is y = 640 px and the golden line is y ≈ 733 px. *Observation:* in v2
  the estimated eye line sits at about 36–45 % of frame height (≈ 690–865 px), below both lines in most segments. With a
  baseline zoom of 1.0, `scale_about` cannot move the frame without exposing an edge, so lifting the eye line needs a baseline
  zoom above 1.0 (e.g. 1.05) with a vertical offset in the punch centre.
- **R6 (minimal headroom) →** in 9:16 a straight-to-lens selfie has a lot of space above the head. Trim it with the punch-in, but
  keep the forehead under the Reels top UI from looking cramped. Hair may be cropped only on the extreme punch-in (an ECU-style beat).
- **R7 (balance / centre eye) →** for direct address, centre the face horizontally (centre-eye dominance 7.7.11, symmetry 7.1.38).
  Off-centre only when a graphic fills the other side. *Observation:* v2 face centres range 514–682 px against a frame
  centre of 540 px, so many segments sit 60–140 px right of centre with nothing balancing the left.
- **R8 (shot size as emphasis) →** baseline ≈ CU in the current takes (face box ≈ 33–38 % of frame height at 1.0). Punch-in
  (+15 %) = "lean in" for claims; the one extreme punch (`SNAP`, 1.55×) = the ECU beat, used once for the key line ("your turn").
  A 9:16 selfie cannot produce a wide or a full shot of the speaker, so wides, establishing and context shots come from cutaways.
- **R10 (B-roll intent) → cutaways.** House cutaways are motion graphics, not filmed B-roll, but the taxonomy transfers: lists and
  numbers built on the spoken word are *primary*; a symbolic graphic (e.g. a rising chart for "grow") is *secondary*; a cutaway
  used only to hide a cut with unrelated content is *wallpaper* and should not appear in a 30–60 s ad. The opening frames of the
  business (storefront, Maps listing) act as *context* B-roll for the client.
- **R11/R12 (motion and colour lead the eye) →** in cutaways, animate one element at a time on the spoken word and give the active
  item the accent colour (the style's `colors.accent`) while the others stay muted (the series look is already near-monochrome, so a single
  accent works as a "pop of colour").
- **R13 (uncluttered) →** at most one non-caption overlay on A-roll at a time; cutaways show only the current idea.
- **R15 (depth) →** rotoscoped "card or big word behind the head" moments are the depth layer (foreground person, mid card,
  background wall). Keep them as a spice (≤ 4, each ≤ 3 s, EDIT-STANDARD §1).
- **R16 (180°) → mostly does NOT transfer:** there is one subject and one camera. What survives: never mirror/flip the A-roll
  (it reverses screen direction, text and features), keep the speaker on the same side of the frame across a sequence, and if a
  cutaway shows another person, keep their facing consistent.
- **R17 (eyeline match) → transfers when the speaker glances off-lens or points** ("look at this listing"): the next cutaway
  should show the thing, entering from the side the speaker looked or pointed toward.
- **R18 (establishing shot first) → partly transfers.** A Reels ad must open on the hook (usually the face and the first line),
  not on a slow establishing wide. Establish the business or place in the first cutaway instead.
- **R19 (level horizon) →** never add rotation in the punch transform; a tilt is only for a flagged glitch/whip transition frame.
- **R21–R25 (lines, shapes, odds, colour, fill) →** these apply to the layout of graphic cutaways: lists in threes, an accent on one
  item, geometric card grids for order.
- **Does not transfer:** knee/hip/ground-level shots, aerials, overheads, Dutch-angle storytelling, deep-focus staging, rack focus,
  the master shot and the full/cowboy sizes for the speaker. None can be created from a single fixed selfie take; they appear only
  inside sourced B-roll.

### B.3 Checklist (tick yes/no)

**Pre-edit**
- [ ] Is the selfie camera at eye level (not looking down at or up at the speaker)? (7.3.17–19)
- [ ] Is the source resolution high enough for the largest punch-in without upscaling (source height ≥ 1920 × max zoom), or has the softening been accepted? (EDIT-STANDARD Image gate)
- [ ] Are YuNet landmarks (both eyes, nose) stored per frame, not only the box? (needed for eye-line and gaze checks; current `prep_faces.py` keeps the box only)
- [ ] Is each cutaway in the plan tagged with its line, keyword and intent (primary / secondary / context)? (7.8.6–14)
- [ ] Is the one extreme punch-in assigned to the strongest emphasis beat? (7.2.34)
- [ ] Does the first cutaway establish the business or place? (7.2.4–6, 7.8.13)

**During edit**
- [ ] Does every uncovered A-roll cut change scale by at least the house step, measured at the cut frames? (7.5.7–9)
- [ ] Is every uncovered A-roll cut placed on head or hand motion, not on a still pose? (7.5.13–15, 7.5.21)
- [ ] Does the eye line sit on or near the top-third / golden line? (7.1.9, 7.1.37)
- [ ] Is headroom minimal (no wasted band of wall above the head)? (7.1.24)
- [ ] Is the face horizontally centred, or balanced by a graphic on the other side? (7.1.33, 7.7.11)
- [ ] If the speaker looks or points off-lens, does the next shot show the thing on that side? (7.5.16–17)
- [ ] Does each cutaway land on (not before) its keyword? (7.8.4, 7.8.8; EDIT-STANDARD §1)
- [ ] Does only one element animate at a time in each cutaway beat, with the active one in the accent colour? (7.6.5, 7.6.13)
- [ ] Is the face the brightest large region on every A-roll frame? (7.1.46)
- [ ] Is there no rotation and no horizontal flip in any A-roll transform? (7.1.42, 7.4.4)

**Pre-delivery**
- [ ] Do the QC gates in B.5 all pass?
- [ ] Has the contact sheet at every cut been checked for focal-point jumps? (7.6.6)
- [ ] Is there no wallpaper cutaway (each one carries its line)? (7.8.12)
- [ ] Was the extreme punch-in used once only? (7.2.34, EDIT-STANDARD §1)

### B.4 QA (senior-editor review while watching)

1. **"Did I notice any cut?"** Good: on A-roll the cuts feel like the speaker leaning in or settling back; no twitch or teleport. (7.5.1, 7.5.23)
2. **"Where did my eye go in the first 5 frames after each cut, and was that the thing being said?"** Good: on the face, or straight onto the item being named, with no searching. (7.6.1, 7.6.6)
3. **"Does the speaker feel like they're talking to me?"** Good: eye level, eyes on the upper third, centred, steady. Bad: looking down from above, or the face sliding sideways between shots. (7.3.19, 7.7.11)
4. **"Is the framing doing emotional work?"** Good: tighter on claims and the call to action, the one big punch on the turning line, base framing on setup lines. Bad: random zoom levels that don't follow the script's emphasis. (7.2.28, 7.2.34)
5. **"Is there air above the head that says nothing?"** Good: headroom tight, the chest area free for captions. (7.1.24)
6. **"Does each cutaway earn its place?"** Good: you could say which word it illustrates. Bad: a decorative screen that just hides a cut. (7.8.6, 7.8.12)
7. **"Is anything competing with the face?"** Good: graphics, cards and captions are dimmer or smaller than the face; one idea on screen. (7.1.46, 7.7.45)
8. **"Does the speaker's gaze or gesture get answered?"** Good: a glance or point toward screen-right is followed by the graphic coming from the right. (7.5.17)
9. **"Does the depth moment (card behind the head) read as 3-D?"** Good: clear foreground person, mid card, background wall, clean edges. (7.1.29)
10. **"Is the restraint right?"** Good: each effect has a reason; nothing added only because it could be. (7.6.16)

### B.5 QC (automatable gates)

Frame: W = 1080, H = 1920 px, diagonal = 2203 px, 23.976 fps. "Eye line" = mean y of YuNet's two eye landmarks after the punch
transform (`y' = cy + (y − cy)·z` with the same centre `scale_about` uses). Thresholds marked **[derived]** are my translation of
a qualitative rule from the videos into a number and should be calibrated on the user's inspirations; thresholds marked **[house]**
come from EDIT-STANDARD; none of the videos gives a pixel number.

| # | Gate | Metric | Pass | How to measure |
|---|---|---|---|---|
| Q1 | Punch step (30° equivalent) | `r = faceH_in / faceH_out` at the last frame before and first frame after every A-roll→A-roll cut not covered by a cutaway | `|ln r| ≥ ln 1.15 = 0.140` **[house]** | YuNet box height on the final rendered frames (or the zoom actually applied, including the 1.5 % creep) from the cut list in `edl_v2.json` |
| Q2 | Cover | Every uncovered cut with `|ln r| < 0.140` | 0 such cuts **[house]** | Cut list ∩ cutaway intervals (`CUT`), frame-exact |
| Q3 | Position jump at a punch cut | Horizontal shift of the eye midpoint across an A-roll→A-roll cut | ≤ 54 px (5 % W) **[derived from 7.5.1, "teleport"]** | YuNet landmarks on the two cut frames |
| Q4 | Cut on motion | Head motion energy (mean landmark speed, px/frame) in the ±2 frames around each uncovered A-roll cut | ≥ the median for that segment **[derived from 7.5.21]** | YuNet landmark track per frame |
| Q5 | Eye line | Eye-line y on every A-roll frame | 576–768 px (30–40 % H), centred on the third (640) and golden (733) lines **[derived from 7.1.9, 7.1.37]** | Landmarks after the punch transform. v2 estimate: ≈ 690–865 px, so most segments fail today |
| Q6 | Headroom | Rows between the frame top and the top of the head (first matte row with alpha > 0.5 within face cx ± 0.6·w) | 77–230 px (4–12 % H) on base and punched A-roll; < 0 allowed only inside the `SNAP` extreme punch **[derived from 7.1.24]** | RVM matte (`matte_v2`) transformed by the punch |
| Q7 | Horizontal balance | Eye-midpoint x | 486–594 px (45–55 % W), unless a graphic layer's centroid sits in the opposite half **[derived from 7.1.33, 7.7.11]** | Landmarks + graphic layer bboxes from `gfx.py` |
| Q8 | Eye-trace across A-roll↔cutaway cuts | Distance between the focal point on the last outgoing frame and the first incoming frame (A-roll focal = eye midpoint; cutaway focal = bbox centroid of the first element to animate) | ≤ 330 px (15 % of diagonal) on straight and glitch cuts; on whips the incoming focal must lie on the whip's direction of travel **[derived from 7.6.6]** | Landmarks + the cutaway's element timeline from `gfx.py` |
| Q9 | Brightest region | Mean luma of the face box vs mean luma of the background (matte = 0) and of every non-caption overlay of area > 2 % of frame | Face ≥ background + 15 (8-bit Y); no large overlay brighter than the face during A-roll **[derived from 7.1.46]** | Rendered frame, matte, layer masks |
| Q10 | One mover | Number of elements that start animating within the same 6 frames (0.25 s) of a cutaway beat | ≤ 1 **[derived from 7.6.5, 7.6.10]** | `gfx.py` element start times |
| Q11 | Accent on active item | Chroma of the active (just-spoken) element vs the others on screen | Active element has the highest mean chroma **[derived from 7.6.13, 7.7.42]** | Per-element masks, Lab chroma |
| Q12 | Show after tell | `onset − keyword_word_start` for every cutaway/list item | 0 to +6 frames (0 to 0.25 s) **[house: never before; upper bound derived from 7.8.4, 7.8.8]** | whisper.cpp word times (`v2_words_clean.json`) vs graphic onsets |
| Q13 | Connection | Each cutaway has an intent tag and, for primary, its keyword appears in the words within ±1.5 s of onset | 100 % tagged; 0 wallpaper **[derived from 7.8.6–12]** | EDL metadata + transcript string match |
| Q14 | Extreme punch count | Segments with zoom ≥ 1.4 | exactly 1 **[house]** | Zoom track |
| Q15 | No roll, no flip | Rotation in the A-roll transform; correlation of each A-roll frame with the un-flipped vs flipped raw plate | rotation = 0; un-flipped correlation > flipped **[derived from 7.1.42, 7.4.4]** | Render parameters; frame vs plate correlation |
| Q16 | Clutter on A-roll | Simultaneous non-caption overlays on an A-roll frame | ≤ 1 **[derived from 7.1.7, 7.7.45]** | Layer list per frame |
| Q17 | Upscale limit | `max zoom × output height / source height` | ≤ 1.0 for lossless sharpness, or flagged **[house: Image gate]** | Source probe + zoom track |
| Q18 | Face vs text | Existing house gate (YuNet box vs every text/graphic layer) | Zero overlap **[house]** | `gate_picture.py` |

To build Q3–Q8 and Q15, `prep_faces.py` must save the 10 landmark values YuNet already returns (`faces[i][4:14]`) next to the
box.

### B.6 Anti-patterns and failure modes

| Anti-pattern | Symptom | Fix | Source |
|---|---|---|---|
| Near-identical A-roll cut | Speaker twitches or teleports a few px between takes | Punch step ≥ 1.15× measured at the cut, or cover with a cutaway | 7.5.1–4, 7.5.19 |
| Zoom creep eats the step | Table says 1.0 → 1.12, the screen shows about 1.10 | Measure at the cut frames; raise the punch level or reset the creep | 7.5.9 (observed in v2) |
| Cutting on stillness | The cut stands out as a "security camera glitch" | Move the cut a few frames onto a head nod or gesture | 7.5.21 |
| Low eye line, big headroom | Face sits mid-frame with a band of empty wall above | Baseline zoom > 1.0 with a vertical offset so the eyes sit at 30–40 % H | 7.1.9, 7.1.24, 7.1.37 |
| Face drifts off-centre | Speaker leans right of centre with nothing on the left | Shift the punch centre to recentre, or place the graphic on the empty side | 7.1.33, 7.7.11 |
| Eye hunt after a cut | The viewer searches the cutaway for the first 0.5 s | Start the first mover where the eyes were; one element at a time | 7.6.6, 7.6.10 |
| Overlay brighter than the face | Card or plate pulls the eye off the speaker | Dim it, shrink it or move it behind the head with depth | 7.1.46 |
| Everything pops | Several accented items; nothing reads as active | Accent only the item being said; mute the rest | 7.6.13, 7.7.42 |
| Wallpaper cutaway | A graphic that says nothing about the line, used only to hide a cut | Replace it with a primary graphic for the line, or use a punch-in instead | 7.8.12 |
| Graphic before the word | A list item appears before it is spoken | Snap the onset to the word start or later | 7.8.4; EDIT-STANDARD §1 |
| Overused extreme punch | ECU-style punches lose their shock | One per video, on the key line | 7.2.34 |
| Mirrored A-roll | Text or features reversed; screen direction flips | Never flip; keep the plate orientation | 7.4.4 |
| Unmotivated tilt | A slight rotation reads as unease | Zero rotation outside a flagged transition | 7.1.42, 7.3.14 |
| Unanswered glance | The speaker points or looks off-lens and the next shot ignores it | Next cutaway shows the thing and enters from that side | 7.5.16–17 |
| High-angle selfie | Speaker looks small, looking up at the viewer | Re-shoot at eye level; cannot be fixed in the edit | 7.3.7, 7.3.19 |
| Clutter | Several stickers or icons on the A-roll | One overlay at a time, minimalism | 7.1.7, 7.7.45 |

### B.7 Conflicts and open questions

1. **House punch-in 1.15× vs the 30° rule (7.5).** The video sets a 30° angle change and calls a few-centimetre move amateur; it
   gives no scale equivalent. A 15 % size change is a modest geometric change.
   **My call:** keep 1.15× as the floor (it comes from the user's own inspirations) but enforce it at the real cut frames (Q1).
   Prefer pairing it with a cut on motion (Q4), and use 1.18–1.25× when the source resolution allows without upscaling (Q17).
   Note that the current `ZOOM` table (1.12–1.14) plus the 1.5 % creep is below the house's own 1.15×; this is an existing gap.
2. **7.5 allows jump cuts as a vlog style; the selfie ad is vlog-like.** EDIT-STANDARD bans visible jumps and the user rejected v1
   as amateur. **Call:** the house rule wins; no deliberate jump cuts.
3. **"Headroom kept to a minimum" (7.1) vs 9:16 Reels.** In a vertical frame, the Reels UI covers the top band and captions sit
   mid-chest, so a face pushed to the top can be crowded by UI. **Call:** trim headroom to 4–12 % H (Q6, derived) rather than zero;
   recheck against the platform's own safe-zone guidance for text, which this module's videos don't cover.
4. **Rule of thirds/golden ratio (7.1, 7.7) vs centred symmetry (7.1.38, 7.7.11).** **Call:** for direct-to-lens A-roll, centre
   horizontally and use thirds/golden only vertically for the eye line. Use horizontal thirds only when a graphic occupies the
   other side.
5. **"Tell me, then show me" (7.8.4) vs "cutaways build with the words" (EDIT-STANDARD §1).** The first suggests showing after
   the line; the house builds on the spoken word. **Call:** no conflict in practice. Land each item on its keyword (0 to +0.25 s,
   Q12), never before; for a whole cutaway, the line that sets it up may start on the A-roll and the cutaway shows it.
6. **Wallpaper B-roll is normal in high-end documentary (7.8.12); the house uses cutaways partly to hide cuts.** **Call:** in a
   30–60 s ad every second sells, so a cutaway that hides a cut must still be primary or context content for its line. No
   wallpaper.
7. **Establishing shot first (7.2.3) vs the Reels hook.** **Call:** open on the hook (face plus first line); establish the
   business in the first cutaway.
8. **Extreme punch-in (EDIT-STANDARD "one extreme punch-in") vs image quality.** 1.55× on a 1080×1920 plate is an upscale that
   softens the image, which could trip the Image gate. **Open:** confirm the source resolution of each take. If it is 1080p, either
   accept the softening for a ≤ 1 s beat or cap the extreme punch to what the source supports.
9. **Eye-line and headroom fixes vs the face/text gate.** Lifting the face (Q5/Q6) moves the chin away from the caption zone
   (`gate_picture.py` requires the chin above y = 1290), which helps. It may push the forehead under the platform's top UI.
   **Open:** calibrate Q5/Q6 against frames from the user's inspirations before making them blocking.
10. **Medium full definition.** 7.2 says "just below the waist"; the common definition is mid-thigh. This does not matter for
    the selfie edit (the size can't be made), but use the common definition if it is ever needed for B-roll briefs.
11. **Eyeline match is only lightly covered** in 7.4 (opposed eyelines) and given properly in 7.5. The Murch eye-trace video (7.6)
    does not explain Murch's cross-cut theory; the cross-cut focal-point gate (Q8) rests on 7.6.6 ("place imagery where the
    viewer's eyes currently live") and is a derived threshold.
12. **v2 measurements are estimates.** The eye line and headroom observations above use the median YuNet box per segment with
    eyes assumed at 38 % of box height, because `faces_v2.json` holds boxes only. Re-measure with stored landmarks before acting
    on them.
