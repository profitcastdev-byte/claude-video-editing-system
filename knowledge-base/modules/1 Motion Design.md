# Module 1: Motion Design (Physics, Easing & Visual Weight)

> **Note (style profiles).** This module was written while CVES was tested on its first ad. Its research rules are universal; where it speaks of the "house" look or a house number for a per-client choice (palette, accent colour, grade, transition kinds, cutaway share, caption position, bed level), read it as the value from the client's style profile (`docs/STYLE.md`). The black stage / green accent / warm moody A-roll measured here is now the optional preset `profitcast-dark`, not the default.

Dissected against `tools/DISSECTION-BRIEF.md`. All 8 transcripts in `transcripts/1 Motion Design/` read in full, start to finish.
Edit standard cross-checked: `knowledge-base/EDIT-STANDARD.md` (hereafter "ES") §1–5.
House code audited: `Edit/gfx.py` (easing + graphics kit) and `Edit/render_v2.py` (per-frame compositor). The project frame rate is
**23.976 fps** (`edl_v2.json` fps = 24000/1001), so 1 frame = 41.7 ms and every duration below is also given in frames at that rate.

Timestamps are the transcript chunk start that contains the idea (chunks are about 30 s long).

**Source caveats up front**
- **1.3** is a manual replacement: Alex Grigg, "The Secret Science of Spacing in Animation" (curriculum asked for Plugin Play's "Spacing & Timing"). On topic, and one of the most useful sources here.
- **1.4** (School of Motion, local Whisper transcript) is about 85% an After Effects interface tour [03:34–22:35]. The motion content is the 12-principles recap [01:00–03:01] and the spacing demo [23:33–26:34]. The interface material is extracted only where it carries a motion rule.
- **1.5** is a manual replacement (Ben Marriott, "The #1 Skill All Animators Need", 761 s). It replaces the 56 s "Motion Foundation" course trailer that was dissected before. It is a full lesson on anticipation, from the same channel. Course promotion at [00:00]–[01:00] and a giveaway at [11:00] carry no technique. The body was checked against the header and matches.
- **1.6** (CRED designer Atul Khola, via Design Sundays) is UI/UX motion, not video. Its 12 "principles" are an adaptation of Disney principles for interfaces. Most still transfer to on-screen graphics (offset & delay, value change, masking, origin, parallax, spotlight). One principle is transcribed as "peony" [17:00]; the description (every element needs a clear point of origin) is what is extracted; the real name is not in the transcript.
- **1.7** is a manual replacement (Ag Motion Designs, "5 Logo Animation Principles", local Whisper). Practical After Effects recipe; its use of "secondary action" is really a settle/follow-through bump (see B.7).
- **1.8** (Motion By Scott) is a learning-path video. Only [06:31–10:36] carries motion rules; the rest is career/learning advice, extracted but marked as not transferable to the edit itself.

---

## A. Per-video dissection

### 1.1 The Principles of Motion Design
- **Source:** 1.1 · "The Principles of Motion Design" · Envato (Envato Tuts+, presenter Jess) · https://www.youtube.com/watch?v=0N0NHlvMEWs · 625 s (10:25) · ~1,770 words · match: search 0.87, on topic.
- **Thesis:** Motion design is graphic design over time: get hierarchy, balance, contrast, space and repetition right first, then apply five animation principles (timing, easing, anticipation, follow-through, secondary animation) to give the design mass, weight and story.

**Graphic design foundation**
1. Get the still design right before animating; good motion design needs good graphic design first. [02:01]
2. Treat hierarchy as the order the brain digests information, controlled by the weighting of elements through scale, colour and alignment. [02:30]
3. Use balance and tension to set mood: a layout can be purposely balanced and in harmony, or dynamic, inviting tension between elements. [02:30]
4. Build contrast from opposing elements: dark/light, warm/cool, sharp/soft. [02:30]
5. Choose palettes with a good amount of contrast in both lightness and saturation. [03:02]
6. Treat negative space as being as important as the element itself; give elements room to breathe, or overcrowd on purpose. Negative space is what creates tension. [03:02]
7. Use repetition/rhythm: the same fonts, colours and styles throughout. Anti-pattern: switching the font halfway through a project confuses the audience. [03:30]
8. Keep the principle list at hand; when a frame "falls flat", evaluate the frame against each principle. [03:30]

**Animation principles (the five that matter most for motion graphics)**
9. Of Disney's (Frank Thomas and Ollie Johnston's) principles, prioritise timing, easing, anticipation, follow-through and secondary animation for motion graphics. [03:30]
10. Remember the difference from graphic design: animation is physical; things have mass and weight and happen in time. [04:03]
11. Block the animation first. Timing is "hierarchy in the fourth dimension": changing the duration and flow of an action changes how the audience understands it, its mood and its legibility. [04:31]
12. Storyboard and decide the keyframes (the main moments of action) before deciding what happens between them. [04:31]
13. Pre-compose each scene, add each scene's key action frames (the throw, the hit), then assemble the scenes in one main comp to see the flow. [05:03]
14. Do not make every scene the same length; equal lengths give "not much story". [05:03]
15. Give the frame before a reveal extra screen time so the audience has a "huh" moment before the reveal lands. [05:31]
16. Keep re-tweaking timing as the piece develops; the blocking prep still makes the biggest difference. [05:31]
17. Choose the frame rate deliberately; it changes the feel of the piece. [06:00]
18. Treat easing as velocity over time; it refines timing, adds character and shows mass and weight. Get comfortable with the graph editor and control the curves. [06:00]
19. Read curves as: steeper = faster, shallower = slower; mix speed-graph and value-graph editing for control. [06:00]
20. Block the main keyframes as hold (stepped) keys first, then add easing. [06:31]
21. Use anticipation to prime the audience for the next move; add "a few frames of opposite animation" before launching the main action (the arm recoil before a throw). [06:31]
22. Add a little squash and stretch, in certain cases, to show how mass is affected by the movement. [07:00]
23. Add follow-through (the reverse of anticipation): the energy of the action goes somewhere after the hit (the ball bounces off, the character falls back). [07:31]
24. Choose the follow-through flavour by feel: "sliding slowly into place" or a snap-back action. [07:31]
25. Add secondary animation that enhances the main action: what the main action causes other elements to do, how the environment affects them (head offset from the arm swing, ball rotation, smoke trails). [08:00]

**Styling and rule-breaking**
26. Lean into styling effects (inner glow, displacement, CC Lens) when asked to "make it pop", but use them with caution and keep the graphic design principles in charge. [08:34]–[09:00]
27. Restyle stock assets to the project's look (Colorama on a stock volleyball) instead of using them raw. [08:34]
28. Break rules deliberately, not by accident: a flowy abstract piece may use barely any easing or anticipation; a clean graphic piece may drop squash and stretch because it looks too realistic or cartoonish; removing all negative space makes a piece feel overwhelming. [09:00]–[09:31]
29. Summary rule: motion design is "graphic design, but over time". [09:31]

---

### 1.2 The 12 Principles of Animation Explained
- **Source:** 1.2 · "The 12 Principles of Animation Explained — The Most Important Rules for Animating" · StudioBinder · https://www.youtube.com/watch?v=tYc1yUt0IeA · 1628 s (27:08) · ~3,310 words · match: direct 1.0, on topic (character-animation framing).
- **Thesis:** Thomas and Johnston's 12 principles (The Illusion of Life, 1981) are physics- and emotion-rooted rules that make movement believable and legible; each is illustrated with film examples.

1. Treat the 12 principles as the rules of the trade; they still apply to 3D/computer animation. [01:00]–[02:30]
2. **Squash and stretch** gives an object weight and lifelike malleability; the amount signals mass and rigidity: the more it squashes and stretches, the more gelatinous it reads. [02:30]–[03:00]
3. Use squash and stretch on faces to exaggerate expressions (Snow White's dwarves read as harmless). [03:32]
4. Keep volume constant: when an object stretches on one axis it must squash on the other; if volume shifts too much, believability fades. [04:00]
5. **Anticipation** is the wind-up before the move; it makes the action legible because the audience is prepared for and expects the move before it happens. [04:32]
6. Precede each major action with a specific move that tells the audience what is about to happen. [04:32]
7. Scale the anticipation to the action: a huge wind-up signals a hard punch (Gaston), sold further by stretch on impact. [05:00]
8. Anticipation can be subtle (Yao pulls his mouth back before biting the pole). [05:00]–[05:31]
9. Anticipation adds realism as well as clarity (a back-swing before a golf shot). [05:31]
10. **Staging**: every element in the frame should present the core idea clearly: action understood, personality recognisable, expression seen, mood felt. [06:02]
11. Stage like live action: wide shots for big actions, close-ups for facial expression. [06:30]
12. Use eye trace for clarity: keep each step of the key action where the eye already is (Lampwick's transformation stays centre frame) so the viewer never searches. [07:01]
13. Deliver the core idea in as few shots as possible, with set dressing and palette reinforcing it (The Incredibles: close-up on a red "DENIED", pan to the claimant; desaturated palette = joyless job). [07:30]–[08:00]
14. Work in silhouette: if the action reads without the face, the staging works (Pixar, Toy Story). [08:32]
15. Judge staging by speed of understanding: if the viewer quickly gets the purpose of a shot, it works. [09:00]
16. **Straight-ahead vs pose-to-pose**: use straight-ahead (frame after frame) for unpredictable motion such as quick reactions, fire and water. [09:31]
17. Use pose-to-pose (keys first, in-betweens after) when you need control and must hit several important beats. [10:02]
18. **Follow-through**: appendages keep moving after the body stops; it represents inertia. [11:00]
19. Show follow-through with late-settling secondary parts (pant legs land after the feet; the Genie's feather keeps going while his head turns the other way). [11:30]
20. Use **drag** (the other side of inertia): appendages start moving only after the body has started; it adds life or comedy (Looney Tunes). [12:01]
21. Use **overlapping action**: different parts move at different rates (Peter Pan's jump: torso first, then arms, then legs). [12:31]
22. Use the **moving hold**: living things are never totally still; they breathe, blink and adjust, and these small moves inform character (Fang breathes more because she is big). [12:31]–[13:02]
23. **Slow in and slow out**: a move starts slower than its full speed and slows before it ends; "nothing can stop on a dime". [13:32]
24. Implement slow in/out with more in-betweens near the start and end poses and fewer in the middle; on a computer, give the motion curve an S-curve (easing). [14:01]
25. **Arcs**: very few organisms move with mechanical in-out/up-down precision; natural action moves in arcs (bouncing ball, head turn, even small dialogue gestures). [14:30]–[15:02]
26. On a computer, create arcs by curving the x and/or y motion paths. [15:02]
27. **Secondary action** supports the primary action and can characterise (Perfect Blue: Mima pumps her arms, her double barely moves her upper body, which reads as effortless and terrifying). [15:33]–[16:01]
28. Never let secondary action distract from the primary action. [16:01]
29. Keep secondary business out of the face: Anastasia fidgets with her hair but her hands never cross her face, so focus stays on the expression. [16:33]
30. **Timing**: more in-between frames make an action longer and slower; fewer make it faster. [17:02]
31. Use timing as characterisation: the same action slow means something different from fast (Jack's many-frame tentative move vs a quick few-frame head shake). [17:31]–[18:01]
32. Choose the drawing rate: on ones (new image every frame) for detailed movement, on twos for faster action (most common), on threes for generalised or background action. [18:01]–[18:30]
33. Mixed rates within one subject create a deliberately chaotic collage feel (Spider-Punk: body on twos and threes, jacket on fours, guitar on sixes). [19:01]
34. Use a variety of speeds within one performance for nuance; timing is more than fast vs slow. [19:30]
35. **Exaggeration**: aim for convincing, not literal realism; exaggerate to serve the emotional truth. [20:00]
36. Exaggerate more when the action must read in a wide shot (Timon and Pumbaa's flying tears). [20:00]–[20:32]
37. Exaggeration can be subtle and anatomy-rooted (Bambi's long legs and clumsy walk). [21:01]
38. If the core idea of a shot is not coming across, exaggerate. [21:01]
39. **Solid drawing**: give forms weight, depth and balance; a flat-looking character reads false however good the motion. [21:32]–[22:01]
40. Use 3D reference (maquettes) for awkward angles. [22:30]
41. Avoid **twinning**: perfectly symmetrical poses or limbs moving identically look lifeless. [22:30]
42. **Appeal**: charm, pleasing design, simplicity, communication, magnetism; not just cuteness. [23:32]–[24:01]
43. Round, baby-like proportions are a consistent route to appeal (Dumbo). [24:01]–[24:31]
44. Simplify to bare necessities; a strong design is recognisable from one feature (Mickey's two circular ears). [24:31]
45. Appeal needs purpose: the shape must carry the personality inside it; exaggerated angular design can make a villain appealing (Anton Ego). [24:31]–[25:32]

---

### 1.3 The Secret Science of Spacing in Animation (replacement for "Spacing & Timing")
- **Source:** 1.3 · "The Secret Science of Spacing in Animation" · Alex Grigg // Animation for Anyone · https://www.youtube.com/watch?v=F4_wbj2Sw2Y · 509 s (8:29) · ~1,680 words · match: manual replacement 1.0, on topic.
- **Thesis:** Spacing (distance between successive frames) has only three states (speeding up, slowing down, constant), and the choice should follow the forces acting on the object; random spacing reads as shake.

1. Decide spacing from two things: how fast the object should move, and whether it is speeding up, slowing down or constant. [00:00]
2. Fast = frames far apart; slow = frames close together. [00:00]
3. To speed up, make the next gap larger than the previous two; to slow down, make it smaller; to stay constant, make it exactly the same. [00:31]
4. Think of motion as caused by forces (the finger pushing the coin): nothing starts moving before a force touches it. [01:00]–[01:31]
5. Do not default to constant speed just because the software does (dividing distance equally by frame count is the default in many programs); decide whether constant speed is right. [01:31]
6. Constant speed (or rest) means all forces are perfectly balanced (cyclist: pedalling = wind + road friction); that balance is rare, so constant motion is rare in reality and usually sits between a speed-up and a slow-down. [02:00]–[02:31]
7. Slowing down needs an unbalanced resisting force (friction stops the rolling ball); speeding up needs a driving force bigger than the resistance (an engine overcoming friction). [03:01]
8. Gaps that shrink = deceleration; gaps that grow = acceleration; animators call both "easing". [03:30]
9. Easing always implies some force greater than the others at play. [03:30]
10. Example sequence for a pushed heavy ball: accelerate while pushed, a brief constant phase when push equals friction, then decelerate once contact is lost. [04:02]–[04:31]
11. Do not blindly ease in and out of every move; it is "true a lot of the time" but not always. [04:31]
12. A bouncing ball eased at both ends of each arc does not read as a bounce; follow gravity instead: speed up moving with gravity, slow down moving against it. [04:31]–[05:00]
13. Once you know which phases speed up and slow down, exaggerate them as much as you like and the move still works. [05:00]
14. Exaggerate spacing for two reasons: impact/appeal, or communication (give a few extra frames and less movement on the most important poses so the audience can focus on them). [05:31]
15. "Break the laws of physics as much as you like" but in a believable direction; use forces to find that direction. [05:31]
16. Even when ignoring physics, there are still only three choices (speed up, slow down, constant), and the brain reads meaning into each. [06:00]
17. Anti-pattern: shaky animation = spacing that changes randomly every frame, which implies a different force acting 24 times a second; avoid unless shake is intended. [06:00]–[06:30]
18. While animating, check the spacing of the previous frames before placing the next; look back 3–4 frames, not just 2, for smoother results. [06:30]–[07:00]
19. Pay special attention to contact poses: that is where forces change most dramatically. [07:00]
20. Practice: make three 1–3 s animations: one speeding up, one slowing down, one constant. [07:30]

---

### 1.4 Animation in After Effects | The Power of Animation Principles
- **Source:** 1.4 · "Animation in After Effects | The Power of Animation Principles" · School of Motion · https://www.youtube.com/watch?v=mT2Fv5bF6Ik · 1633 s (27:13) · ~4,790 words · match: direct; transcript by local Whisper. Mostly an AE interface tour; motion rules at [00:34]–[03:01] and [23:33]–[26:34].
- **Thesis:** A motion designer is animator + designer + filmmaker; master the 12 principles and, above all, spacing (distance between frames), because every After Effects keyframe and graph edit is still just positioning still images in time.

**Why principles; the 12 in brief**
1. Study the three roles (animator, designer, filmmaker) separately by deconstructing them. [00:00]–[00:34]
2. Squash and stretch gives the illusion of weight and volume. [01:00]
3. Anticipation prepares the audience for a major action; precede each major action with specific anticipating moves. [01:00]
4. Staging presents an idea so that it is clear. [01:00]
5. Pose-to-pose = key drawings at intervals; straight-ahead = drawing to drawing from start to end. [01:00]–[01:38]
6. Follow-through and overlap: when the main body stops, other parts keep catching up; "Nothing stops all at once." [01:38]
7. Slow in/out: more drawings near the start pose, one or two in the middle, more near the next pose. [01:38]
8. Fewer drawings = faster; more drawings = slower. [02:04]
9. Arcs: with few exceptions, all actions follow an arc or slightly circular path; arcs give natural action and flow. [02:04]
10. Secondary action supplements and reinforces the main action and adds dimension. [02:04]
11. Timing: more drawings between poses = slower and smoother; fewer = faster and crisper; timing keeps an object obeying physics. [02:31]
12. Exaggeration: stay true to reality, presented in a wilder or more extreme form. [02:31]
13. Solid drawing: account for forms in 3D space; give them volume and weight. [02:31]
14. Appeal: charm, the "charisma of the action". [03:01]
15. Expect to return to the principles for years; get them on the radar now. [03:01]

**Tool facts that carry motion rules**
16. Set the comp's frame rate deliberately (1–120 possible; 24 film, 30 broadcast TV, 60 live sports, 120 for ultra slow motion). [07:08]
17. Use square pixels for standard web content. [06:31]–[07:08]
18. Vector layers (shape layers) scale infinitely without quality loss; pixel images (PNG) break down and pixelate when scaled up. Know which you are animating before you scale it. [15:33]–[16:30]
19. Position, scale and rotation (P, S, R) are the foundational animatable attributes of every layer. [17:01]–[17:31]
20. Keyframes are per property: animating scale does not animate position; set each property separately. [18:01]–[18:30]
21. Align and distribute elements with the align tools (align bottom; distribute horizontally for even gaps). [21:02]–[22:05]

**Spacing demo**
22. Animation is a series of still images on a timeline; the illusion of motion comes from how you position each one. [23:33]–[24:07]
23. Spacing = the distance between frames: close = slow, far apart = fast. [24:07]–[24:32]
24. The demo uses seven poses per move (at 24 fps that is about 0.29 s). [24:07]
25. "Smash" move: frames close at the start (ease out of the first pose), then about three frames dart through the middle and it smashes into the final pose with no slow-down. [25:41]
26. Classic ease in/ease out: frames close at both extremes, far apart through the middle. [26:04]
27. Jump: frames far apart at contact (velocity and energy), easing up near the top where frames get close. [26:04]
28. Spacing tells a story: the same seven frames read as a smash, a glide or a jump depending only on spacing. [25:41]–[26:04]
29. In After Effects the graph editor replaces drawing every frame, but the spacing idea is identical. [25:03]

---

### 1.5 The #1 Skill All Animators Need (replacement for "Motion Foundation")
- **Source:** 1.5 · "The #1 Skill All Animators Need" · Ben Marriott · https://www.youtube.com/watch?v=LcWJKYbYvi8 · 761 s (12:41) · ~2,830 words · match: manual replacement 1.0, on topic. It replaces the 56 s course trailer that was filed here. Course and giveaway promotion at [00:00]–[01:00], [11:00] and [12:00] carries no technique.
- **Thesis:** Anticipation, a small move in the opposite direction before the main move, is the one principle that most improves motion. It makes motion read as natural, shows how much energy the move took, and pulls the viewer's eye to the element before it moves. The graph-editor work it needs is simple.

**Why anticipation**
1. Treat anticipation as the highest-leverage of the 12 principles; the presenter credits it with getting him off a skill plateau. [01:00]–[01:30]
2. Do not dismiss the 12 principles as only for cel-animated characters; they apply to moving keyframes on abstract shapes in After Effects. [01:30]
3. Define anticipation as a smaller motion that precedes a larger one: the square moves slightly left before it moves right, which builds energy and leads the viewer to expect the move. [02:00]
4. Almost all motion in nature has a moment of anticipation. Throwing without a wind-back looks robotic. [02:00]
5. Scale the wind-up to the result: the further the arm is drawn back, the further the throw. [02:00]
6. Make the anticipation move in the opposite direction to the main motion. [02:31]
7. Use anticipation to tell the audience how much energy and effort went into the move; a small opposite move first makes the main move look more natural and usually more interesting. [02:31]
8. Skip it where precision is the point: a precise piece of machinery should go straight from A to B. Simple A-to-B motion is sometimes the best choice. [03:01]
9. Default to engaging motion: most animation exists to entertain so the audience absorbs the information, even in an explainer of dry financial statistics. A client who only wanted to inform "would have sent out a word document". [03:01]–[03:30]
10. Treat the anticipation as often more important than the motion between the two points. [04:01]

**The three-frame test (pose blocking)**
11. Demo: three hold (stepped) keyframes, no interpolation: start pose, one middle pose, end pose. Put the single middle pose slightly *behind* the start (opposite to the travel), not between start and end. [04:31]
12. With poses 4 frames apart (about 6 frames per second at its fastest), that one opposite pose still communicates a believable move with tension, like a slingshot. [05:02]
13. Anti-pattern: putting the one in-between pose halfway between start and end. It reads as boring; behind the start reads as natural. [05:02]–[05:30]
14. Block with limited keyframes and poses first. If the scene works with a few frames, "everything else is just icing on the cake". [05:30]

**Anticipation directs attention**
15. Use anticipation to direct the viewer's eye (eye tracing). Moving one element draws the eye to it, which gives you control of pace, flow and the viewer's experience. [06:00]
16. Without anticipation, a move away from where the viewer is looking catches them late, and they miss its start. [06:31]
17. With anticipation, the eye arrives in time to see the whole move. Anticipation is a signal: "look over here, something is about to happen". [07:00]

**Graph-editor recipe**
18. Keep the curves simple: the main move eases out of its start and into its end, and the anticipation eases into a small opposite move. [07:00]–[07:30]
19. When the move is on one axis, separate the position dimensions and delete the unused axis's keys so the graph is clear. [07:30]
20. Start from easy ease (F9) on the keys. [08:00]
21. Recipe: copy the first keyframe, paste it a little earlier, then nudge the second keyframe (the old start) in the opposite direction. [08:00]
22. Pull the graph handles out so the easing is more severe and the anticipation more noticeable. [08:00]
23. The presenter prefers the value graph because it shows direction (out, then back); the speed graph shows only speed. Learn both, since each has strengths. [08:30]–[09:01]
24. First pass in the graph editor: smooth everything so the curves flow into each other, with no sharp angles, unless you want something very snappy. [09:01]
25. For a stronger anticipation, hold longer in the wound-up pose: lengthen the handles and drag the first key earlier until the anticipation takes almost **3×** as long as the main motion. This builds more energy before the release. [09:30]
26. Do not let the wind-up hang dead at its extreme: tilt the handles slightly so the value keeps changing slowly while energy builds. [10:00]
27. With only two keyframes, raise the first key's outgoing handle so the curve dips slightly backwards. That gives a tiny anticipation bump with no extra key. [10:30]
28. The two-key bump has no ease into the anticipation (a sudden acceleration). Use it only on small, fast moves: "the smaller and faster the motion the more you can get away with". Otherwise add the extra key. [10:30]–[11:00]

**Anticipation on other properties**
29. The anticipation does not have to be on the same property as the main move: a left-to-right position move can be anticipated by a rotation in the opposite direction, easing out of the rotation as the position eases in. [11:00]–[11:31]
30. Anticipate with a shape-path deformation or with scale as well, or combine several properties (position, rotation, path). [11:31]–[12:00]
31. Smoothness comes from the anticipation leading into the main move (a "running start" that prepares eye and brain), not from graph tricks or a high frame rate. [12:00]

---

### 1.6 CRED's Designer Explains: 12 Principles of Motion Design ft. Atul Khola
- **Source:** 1.6 · "CRED's Designer Explains: 12 Principles of Motion Design ft. Atul Khola" · Rohan Mishra (Design Sundays) · https://www.youtube.com/watch?v=V7jg6kwwImc · 1366 s (22:46) · ~4,530 words · match: direct 1.0. On topic but for product/UI motion; auto-captions are rough.
- **Thesis:** Motion is behaviour, not decoration: it must meet physical-world expectations, stay consistent, push the narrative and show relationships; 12 UI motion principles (easing, offset & delay, parenting, transformation, value change, masking, overlay, origin, obscuration, parallax, dimensionality, dolly & zoom) make that concrete; use motion in moderation, like a spotlight.

**Motion as storytelling and behaviour**
1. Treat motion as visual storytelling: a product (or ad) is a sequence, and good motion tells that sequence well. [01:31]–[02:02]
2. Video is the most efficient storytelling form because it shows exactly what the creator imagined; executed well, motion is storytelling at its best. [02:02]
3. Separate "UI animation" (cosmetic afterthought, adds charm, e.g. confetti, badges) from motion design (behaviour that helps or hinders the experience, e.g. a button's hover state change). [04:00]–[04:30]
4. Distinguish real-time motion (responds instantly to input) from non-real-time motion (plays after the input, as a result of it, e.g. the globe spin to India). [04:30]–[05:30]

**Four ways motion supports usability**
5. **Expectation**: motion must behave the way users expect from the physical world (a pressed button depresses). [05:30]–[06:01]
6. Anti-pattern: motion that breaks physical expectation (a knife that folds like cloth on the sausage) repels the viewer. [06:30]
7. **Continuity/consistency**: keep motion behaviour consistent across the system, just like visual consistency (one sharp-cornered popup among rounded ones is felt subconsciously). [06:30]–[07:30]
8. Make every interactive element share one motion character (radio buttons, toggles and checkboxes all in the same fluid nature). [07:30]
9. Every break in motion continuity disrupts seamlessness; viewers absorb it subconsciously even if they cannot name it. [08:00]
10. **Narrative**: motion must follow a logical progression of the sequence (answer a question, the form auto-slides to the next one). [08:00]–[09:00]
11. **Relationship**: motion should show how elements' spatial, aesthetic and hierarchical attributes relate (changing an input visibly changes the image above). [09:00]–[09:31]
12. Motion that shows relationships lowers cognitive load and makes a flow engaging. [09:31]

**The 12 principles**
13. **Easing**: mimic how real objects accelerate and decelerate (a car speeds up and brakes); nothing starts at full speed and stops dead. [10:00]–[10:32]
14. Momentum scrolling (start at pace, slow, come to rest) is easing in every app. [11:01]
15. **Offset & delay**: humans group things; staggering elements communicates hierarchy and relationships. [11:01]–[11:31]
16. Bring in the main element first (the total), then stack the related items one by one, updating the main element as each lands. [12:01]
17. Anti-pattern: "slapping complete screens together" so the viewer must work out the relationships themselves. [12:01]–[12:31]
18. **Parenting**: link properties so a change in the parent changes the child; it shows how elements relate (light intensity slider drives saturation). [12:31]–[13:00]
19. **Transformation**: one element turns into another to show status (a progress ring that completes and becomes a tick). [13:00]–[13:31]
20. The ring-to-tick transformation is the most widely used success/confirmation motion. [13:31]–[14:00]
21. **Value change**: animate changing numbers so they read as dynamic; static numbers reduce willingness to engage (claimed from studies; no source given). [14:00]–[14:30]
22. Live-changing numbers (portfolio value, crypto price) communicate that the value responds to the viewer's action. [14:30]
23. **Masking**: strategically reveal and conceal parts of an element while keeping it identifiable (a square photo shown in a circle). [15:00]–[15:31]
24. Use a mask shape to frame a process (face placed in a circle during a scan). [15:31]
25. **Overlay**: on a flat 2D plane (no Z), layering creates foreground/background and lets elements be hidden or revealed (swipe-to-reveal options). [16:00]–[16:31]
26. **Origin** (transcribed "peony"): every element needs a clear point of origin tied to something already on screen; elements cannot burst into or out of existence from nowhere (dropdowns, three-dot menus, sliding panels). [17:00]–[17:30]
27. Expand/collapse: the interface stretches out of the tapped element and returns to the same place. [18:00]
28. **Obscuration**: a frosted-glass layer tells the viewer something is behind it without showing it (bottom sheet dimming the background, blurred sensitive content). [18:00]–[19:00]
29. **Parallax**: two elements moving at the same time at different speeds establish hierarchy: faster = foreground/interactive, slower = background. [19:00]
30. **Dimensionality**: elements can appear to fold, flip, float or have depth like physical objects. [19:30]
31. **Dolly vs zoom**: dolly travels into the space (camera walks to the building, AR arrows stuck to the street); zoom magnifies from where you stand (zooming into a garment's detail). [20:02]–[20:31]
32. Motion is communication: with the principles upheld, even simple elements communicate well. [21:01]
33. If motion has characteristics not found in the natural world, "no amount of aesthetic splendor" can overcome it. [21:01]
34. Use motion in moderation, like seasoning with sweets: take a bit, come back later. [21:30]–[22:00]
35. **Spotlight rule**: if everything is static, the one moving thing grabs attention; if everything moves, the one still thing grabs attention. Use motion to direct attention and develop a taste for the balance. [22:00]

---

### 1.7 5 Logo Animation Principles Every Motion Designer Should Know (replacement for "Bring a Logo to Life")
- **Source:** 1.7 · "5 Logo Animation Principles Every Motion Designer Should Know" · Ag Motion Designs · https://www.youtube.com/watch?v=uAgfLhoPnXw · 571 s (9:31) · ~1,780 words · match: manual replacement (original unavailable); transcript by local Whisper. On topic: a practical recipe for a letter-by-letter logo build at 30 fps.
- **Thesis:** A logo animation is lifted from plain to finished by five additions: a secondary (settle) action after the main move, motion blur, a reflection, a small zoom-out after completion, and a light sweep.

**Setup and main action**
1. Separate the logo into one layer per letter/element before animating (layered PSD imported as composition, retain layer sizes). [01:02]–[01:31]
2. Comp settings used: 1920×1080, 30 fps, title/action-safe guides on. [01:31]
3. Main move: position keyframes at 0 and about 20 frames (0.67 s at 30 fps; 16 frames at 23.976), with the middle raised so each letter travels up and down (a hop). [02:06]
4. Strengthen the ease by dragging the speed-graph influence handles out on every keyframe (strong ease, not the default). [02:31]
5. Combine properties in the main move: scale from about 0 to 100% over the same ~20 frames, plus one full 360° rotation over the same span. [03:02]

**Principle 1: secondary action (settle bump)**
6. After the main action, add a small extra action that continues the animation: a second, smaller position hop ending at about 1 s (about 10 more frames). [03:34]–[04:00]
7. Ease the secondary hop the same way in the speed graph. [04:00]–[04:30]
8. Stagger the letters with Sequence Layers so each starts after the previous one (overlap/offset); then extend the comp duration. [04:30]

**Principle 2: motion blur**
9. Enable motion blur on every moving layer (and the comp switch); real moving objects are never seen perfectly sharp, and the blur adds realism. [05:02]–[05:32]

**Principle 3: reflection**
10. Pre-compose the finished logo animation, duplicate it, flip it with Y scale −100%, and position it below as a reflection. [05:32]–[06:00]
11. Set the reflection to about 20% opacity. [06:00]–[06:35]
12. Feather a mask on the reflection so it fades out; no real reflection is continuous. [06:35]

**Principle 4: zoom-out after completion**
13. Keep a little motion after the animation completes: parent the layers to a null and scale it from 110% to 100% over about 5 frames (0.17 s; 4 frames at 23.976). [07:02]–[07:34]
14. Time-reverse those keyframes for a zoom-in variant; choose by feel. [07:34]

**Principle 5: light sweep**
15. Finish with a light sweep across the completed logo: start at about 1 s, end at about 4 s (a 3 s pass). [08:01]–[08:36]
16. Widen and soften the sweep (edge and width) so it reads brighter and wider. [09:00]
17. Put a solid background behind the finished animation. [09:00]

---

### 1.8 How To ACTUALLY Learn Motion Design (Complete Guide)
- **Source:** 1.8 · "How To ACTUALLY Learn Motion Design (Complete Guide)" · Motion By Scott · https://www.youtube.com/watch?v=sEAbFe0aEHw · 1459 s (24:19) · ~4,670 words · match: direct; transcript by local Whisper. Learning-path video; rules 6–14 are the motion content; the rest is process advice.
- **Thesis:** Learn the tool basics (keyframes, easing, masks, built-in effects), learn design, and above all learn the principles of animation and design; then get past the plateau through inspiration, self-directed experiments, feedback and iteration.

**Tools (not transferable to the edit itself)**
1. For 2D, Adobe Creative Cloud (Illustrator/Photoshop for assets, After Effects for animation). [00:32]–[01:03]
2. For 3D: Blender (free), Cinema 4D (expensive, easy learning curve), Houdini (full control, node-based, VFX-grade). [01:30]–[04:00]
3. 2D runs on modest hardware; 3D needs a strong GPU (VRAM), CPU and RAM. [04:00]–[05:30]

**Motion fundamentals**
4. Learn the basics before the advanced work (the diving-board analogy). [06:03]
5. Learn the interface first. [06:31]
6. Keyframes mark the key moments; the software fills in between. [06:31]–[07:03]
7. Software interpolates linearly by default (straight across at constant speed); add easing so motion goes slow-to-fast or fast-to-slow. [07:30]
8. Learn masks to hide and show parts of layers. [07:30]
9. Learn the built-in effects before building something from scratch that already exists. [07:30]–[08:03]
10. "You can't out-animate bad design": design and animation go hand in hand. [08:31]
11. Anti-pattern: ten neon colours across the screen; unreadable work does not work; colour must not hurt the eyes. [08:31]
12. Typography matters, down to the space between letters. [09:03]
13. Composition = the overall frame; contrast = big/small, dark/light; hierarchy = the order things are seen. [09:31]–[10:03]
14. Put strong focus on the theory and principles of animation and design; they are the foundation of every project (squash and stretch, overshoot; book: The Animator's Survival Kit). [10:03]–[10:36]

**Learning process (not transferable as edit rules; transferable as workflow)**
15. Use YouTube, Google/forums/Reddit, structured courses and the software's own help manual. [11:00]–[14:03]
16. Prefer sources that teach why, not only how. [14:31]
17. Expect a learning plateau where tutorials stop helping. [15:36]–[16:01]
18. Get past it by gathering inspiration: combine what you like from several people's work into the overlap ("Steal Like an Artist"). [16:32]
19. Leave the desk; observe how real things move for ideas. [17:04]–[17:32]
20. First projects can be five seconds of shapes. [18:31]
21. Experiment for yourself: motion design is problem solving, getting from A to B "in the nicest way possible" while making it look good. [19:00]–[19:34]
22. Feed problems back into learning, then back into the next experiment. [19:34]–[20:05]
23. Seek feedback (communities, Discord, Instagram, Reddit, meetups) and iterate; do not be upset by critique. [20:30]–[22:05]
24. Do not put tutorial work in a showreel. [22:32]
25. Inspiration → work → feedback → iteration → portfolio is a loop that never ends. [23:05]–[24:01]

---

## B. Module synthesis

### B.1 Best practices (de-duplicated, ordered by impact)

1. **Ease every start and stop of position, scale and rotation; pick the curve from the force story.** Entries decelerate into rest (ease-out), exits accelerate away (ease-in), a move between two rest positions uses an S-curve (ease-in-out), a "smash" keeps speed into the contact. Linear is allowed only for genuinely constant motion. Curves flow into each other with no sharp angles unless snap is intended. UNIVERSAL. [1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8]
2. **No random spacing.** Per-frame displacement of any element (and of the camera/punch-in) must change smoothly; random per-frame changes read as shake. UNIVERSAL. [1.3]
3. **Timing is hierarchy in time.** Block key moments first, as hold (stepped) poses; if the move reads with three poses, the rest is polish. Vary durations; give the beat before a reveal extra hold; fewer frames = crisp and urgent, more frames = tentative. UNIVERSAL. [1.1, 1.2, 1.4, 1.5]
4. **Spotlight: control how many things move at once, and signal where the eye should go.** One mover in a still frame takes attention; many movers dilute it. A small anticipation move is a "look here" signal: it brings the eye to an element before its main move, so the viewer sees the whole move instead of only its end. Use motion in moderation. UNIVERSAL. [1.6, 1.5, 1.2 (secondary never distracts)]
5. **One motion vocabulary per piece.** The same kind of element always enters, settles and exits the same way; inconsistency is felt subconsciously. UNIVERSAL. [1.6, 1.1 (repetition)]
6. **Offset & delay to show hierarchy and grouping.** Main element first, then related items one by one, with overlap (the next starts before the previous has fully settled). Avoid identical, simultaneous "twinned" moves. UNIVERSAL. [1.6, 1.7, 1.2]
7. **Every element has an origin.** Nothing pops into or out of existence from nowhere; it grows from, slides out of, or is revealed by something already on screen (masking, transformation). UNIVERSAL. [1.6]
8. **Follow-through and settle.** After the main move, energy goes somewhere: a slow slide into place, a small overshoot that snaps back, or a short finishing move (logo 110%→100% in ~5 frames at 30 fps). Keep overshoot small for clean graphics. UNIVERSAL. [1.1, 1.2, 1.4, 1.7, 1.8]
9. **Anticipation for major actions.** A smaller move in the opposite direction before the big move, scaled to the energy of the move; subtle is fine. It can sit on another property (an opposite rotation, a scale dip or a shape squeeze before a position move). Ease into the wind-up; a two-key bump with a sudden start is acceptable only on small, fast moves. A strong wind-up can be held up to about 3× the main move's length, kept slowly moving, not frozen. Skip it where mechanical precision is the point. CONTEXT: hero moves (logo, big number slam, transition), not every list row. 1.5 ranks it the most important principle. [1.1, 1.2, 1.4, 1.5]
10. **Staging and clarity first.** Keep the key action where the eye already is; it should read in silhouette; secondary motion never crosses the face or competes with the main idea. UNIVERSAL. [1.2, 1.4]
11. **Motion blur on fast moves, in the direction of motion.** UNIVERSAL for anything moving more than a few px per frame. [1.7]
12. **Value change and masking as communication.** Numbers count up rather than appear; reveals use masks/wipes rather than plain fades where the shape matters. CONTEXT: numbers, logos, wordmarks. [1.6, 1.7, 1.8]
13. **Moving hold / secondary life.** A completely frozen frame looks dead; a slow push or a breathing element keeps it alive. This includes the wind-up pose of an anticipation, which should keep creeping, not hang. CONTEXT: holds longer than about 1 s. [1.2, 1.5, 1.7]
14. **Parallax and parenting to show relationships.** Parts of one unit move together (parent); layers at different depths move at different speeds (parallax). CONTEXT. [1.6, 1.7]
15. **Squash and stretch only with constant volume, and only when the style wants it.** CONTEXT: playful stickers/icons; skip for clean UI. [1.1, 1.2]
16. **Arcs for natural motion.** CONTEXT: tossed/flying objects, logo hops; straight paths are right for UI cards that mimic interface behaviour. [1.2, 1.4, 1.7]
17. **Exaggerate in a believable direction** when the idea does not read, especially at small sizes. UNIVERSAL. [1.2, 1.3]
18. **Design before motion.** Contrast, hierarchy, negative space, limited palette and typography must already work on a still frame. UNIVERSAL. [1.1, 1.8]
19. **Know raster vs vector before scaling.** Raster assets degrade when scaled up. UNIVERSAL. [1.4]
20. **Choose frame rate and drawing rate deliberately** (ones for smooth detailed motion, twos/threes as a stylistic choice). CONTEXT. [1.1, 1.2, 1.4]
21. **Styling effects (glow, sweep, reflection) with restraint.** CONTEXT: end card/logo only. [1.1, 1.7]
22. **Rules can be broken, deliberately.** Abstract pieces may skip easing; clean pieces may skip squash; precise machinery may go straight A→B without anticipation. CONTEXT. [1.1, 1.3, 1.5]

### B.2 Short-form ad translation (9:16, 30–60 s talking head, Meta Reels, 23.976 fps)

What the ad is: a talking head alternating with full-screen motion-graphic cutaways (ES §1), plus a few roto moments and chest-level text. Graphics are simple UI cards, pills, icons, numbers and a logo end card, all drawn in PIL and animated in Python. Viewed on a phone, often at low attention, often muted.

- **Easing (B.1 #1)** transfers fully. In the house code: card slide-ins and panel rises = `ease_out`; word/element exits = `ease_in`; pops (pills, checks, badges) = `back`. A repositioning move of something already on screen (none exist today) should use `ease_io`. Linear `prog()` should drive only constant-rate processes: typewriter characters, a line drawing on, a continuous drift, a light sweep.
- **No random spacing (#2)** applies to the camera too: the A-roll punch-in is centred on per-frame YuNet face boxes, so detector jitter becomes picture shake (see B.5.2 finding F1). This is the most important transfer from 1.3.
- **Timing as hierarchy (#3)** maps onto the voice: in an ad, the words set the keyframes (ES "nothing appears before it's said"). The "huh" hold before a reveal [1.1 05:31] becomes the beat before the price, the "30+" number or the logo: let the previous element sit still for a moment before the hero arrives.
- **Spotlight (#4)** is critical on a 9:16 phone screen with a moving face: the talking head is already a mover, so on A-roll only one graphic should be animating at a time; on cutaways the newest spoken item should be the only primary mover.
- **Consistency (#5)** maps to a motion token table (B.5.1): same slide distance, duration and curve for every card entry in every cutaway, every ad in the series.
- **Offset & delay (#6)** is ES "lists build line by line on the spoken item". For items not tied to separate words (empty search bars, stars, roads), use a fixed frame stagger.
- **Origin (#7)**: hard pops of "+", pills and brackets break it; use a scale-from-zero pop from a sensible anchor (the pill grows from the cursor, the tick grows inside its circle).
- **Follow-through (#8)**: `back(s=1.6)` gives a 9% overshoot, a clean-graphic level (Penner's standard back constant 1.70158 gives 10%; industry norm). The logo zoom-out settle (1.7) transfers directly to the end card.
- **Anticipation (#9)**: transfers only to hero moments, and only inside the element's own time window (ES forbids showing it before the word). A 2–3 frame dip before a number slam or a card shrinking slightly before it pops its check (anticipation on scale, a different property from the main move, 1.5 [11:31]). Its strongest use in the ad is attention (1.5 [06:00]–[07:00]): on A-roll the eye sits on the face, so a hero graphic that will move somewhere else should give a small lead-in so the viewer catches the whole move. The 3× held wind-up (1.5 [09:30]) fits only the end-card logo or one hero beat where the voice leaves room; at 7 f per row it would cost about 21 f per item. Our pops are 5–7 f, so the two-key bump (1.5 [10:30]) qualifies as "small and fast" if used. Do not add anticipation to every list row: that is motion noise on a phone.
- **Staging (#10)**: matches ES Face gate (zero overlap). Add: test the overlap at the overshoot peak and at the start offset of every move, not only at rest.
- **Motion blur (#11)**: transfers; whips already blur, but slide-ins (up to ~19 px/frame on the first frame) do not.
- **Value change (#12)**: ES "numbers count up" already says this. Masked wipes transfer to client wordmarks.
- **Moving hold (#13)**: already present (2.5% push over 6 s on cutaways, 1.5% creep per A-roll segment).
- **Parallax (#14)**: optional; the stage push currently scales grid and cards together. A slower grid drift than card drift would add depth. Parenting matters for compound text (price + "/ month").
- **Do NOT transfer:** 3D software choice, hardware, After Effects interface, showreel/portfolio advice (1.4 interface tour, 1.8 [00:32]–[05:30], [11:00]–[24:01]); solid drawing, maquettes and character appeal (1.2 #39–45) apply to character animation, not to UI cards; straight-ahead animation (no hand-drawn frames here); reflections and long light sweeps (1.7 #10–16) are a 2010s logo-sting look and should stay out of the A-roll and cutaways (end card at most, and only if the client's inspirations use it); mixed drawing rates (1.2 #33) are a stylistic device the series does not use; UI real-time vs non-real-time (1.6 #4) has no viewer input in an ad.

### B.3 Checklist

**Pre-edit (motion plan)**
- [ ] Every graphic's entry time is tied to a word timestamp from `v2_words.json` (or an explicit stagger from a parent that is).
- [ ] Each animated element is assigned a motion token (B.5.1) — entry curve, duration in frames, distance, exit.
- [ ] Hero beats (price, big number, logo) are identified and have a hold before them in the plan.
- [ ] No more than one primary mover is planned per moment on A-roll.
- [ ] Each hero move is blocked as hold poses first and reads with three poses (start, opposite wind-up, end). (1.5 [04:31]–[05:30])
- [ ] Each new element has a named origin (what it grows/slides/reveals from).
- [ ] Raster assets (logo PNG, icon PNGs) are large enough for their largest on-screen size including overshoot and 2× supersampling.

**During edit (code)**
- [ ] No position/scale/rotation driven by raw linear `prog()` except constant-rate processes (typing, line draw, drift, sweep).
- [ ] Entries use `ease_out` (or `back` for pops); exits use `ease_in`; on-screen repositioning uses `ease_io`.
- [ ] Durations are whole frames, and every start is quantised to a frame boundary.
- [ ] `back()` overshoot ≤ 10% and not applied to large panels.
- [ ] Every hero anticipation moves opposite to the main travel (or on another property), eases into its wind-up unless it is ≤ 3 f, and does not freeze at its extreme. (1.5 [02:31], [10:00], [10:30])
- [ ] A hero graphic that moves away from where the eye currently is (face or last mover) has a lead-in move that draws the eye first. (1.5 [06:31]–[07:00])
- [ ] Siblings in a group use the same token, offset in time (no twinning, no inconsistency).
- [ ] Compound elements (number + unit, "FREE" + "WEBSITE") move as one parent unless the split is intended.
- [ ] Fast moves (> ~4 px/frame) get motion blur along the motion direction.
- [ ] Every element that appears also has a defined way out (exit token, or it leaves under a transition).
- [ ] The A-roll punch-in centre is smoothed (not raw per-frame face boxes).

**Pre-delivery**
- [ ] Motion log (B.5.3) passes all gates.
- [ ] Contact sheet of every entry: first visible frame, overshoot peak, settle frame, reviewed.
- [ ] No graphic overlaps the face box at any frame of its animation, including overshoot.
- [ ] Watched once at full speed muted and once with sound: every move lands on its word or SFX.

### B.4 QA (human-judgement review)

| Question a senior motion designer asks | What "good" looks like |
|---|---|
| Does each element feel like it has weight? | Cards decelerate into place and stop softly; pops overshoot slightly and settle; nothing stops dead or drifts on forever. [1.1, 1.2, 1.3] |
| Where is my eye at every moment? | Always on one thing: the newest spoken item or the face. Nothing else competes. [1.6 spotlight, 1.2 staging] |
| Does every item land on its word? | The settle (not the start) of the element is on or just after the word onset; the voice and the motion feel like one event. [1.1 timing, ES §1] |
| Is the motion vocabulary consistent? | All rows across c1–c5 feel like one designer made them; the end card behaves like the cutaways. [1.6 consistency] |
| Do hero beats breathe? | The frame before the price/"30+"/logo is calm for a moment; the hero then hits harder than the list items. [1.1 05:31, 1.3 exaggeration] |
| Does anything appear from nowhere? | Every pill/tick/badge grows from an anchor, every card slides from a direction, every word is revealed. [1.6 origin] |
| Is the motion readable at phone size with a thumb scrolling? | Each move reads in silhouette; a 50 px slide is visible but not a long journey. [1.2 silhouette] |
| Does anything shake? | The A-roll punch-in, scaled text and drifting stages are perfectly smooth at 1× playback. [1.3 shaky] |
| When a graphic moves somewhere I wasn't looking, did I see the start of the move? | Yes: a small lead-in or anticipation pulled my eye there first; I never catch only the end of a move. [1.5 06:31–07:00] |
| Do hero moves have a running start? | Price, "30+" and logo wind up slightly in the opposite direction (or squash/rotate) and then release; they feel smooth because of the lead-in, not because of extra frames. [1.5 12:00] |
| Is there life in holds? | Long holds have a slow push or breathing element, never a frozen frame. [1.2 moving hold] |
| Do transitions look like the motion that caused them? | Zoom-whips blur radially, not as a vertical smear; glitches are short. [1.7 motion blur, ES §1] |
| Would a viewer call any motion "template-y" or AI? | No random bounces, no identical simultaneous moves, no effects for their own sake. [1.1 styling with caution, 1.6 moderation] |

### B.5 QC (automatable gates)

#### B.5.1 House motion tokens at 23.976 fps (the spec the gates check against)
Ranges marked *videos* trace to the transcripts; *industry norm* is named; *house* values are taken from the current `render_v2.py` and are proposals to be confirmed against the client's inspiration edits (measure them with the motion-log tool in B.5.3).

| Move | Curve | Duration | Distance / amount | Basis |
|---|---|---|---|---|
| Card/row slide-in | `ease_out` (cubic) | 7 f (0.29 s) | 50 px horizontal, fade with same p | house (0.28 s); 1.4 demo uses 7 poses at 24 fps [24:07]; Material Design "standard/decelerate" entry 225–300 ms (industry norm) |
| Large panel rise (behind-head card, browser) | `ease_out` | 8–9 f (0.35 s) | 40–120 px vertical | house; Material "large/complex" 300–375 ms (industry norm) |
| Pop (pill, badge, check, icon well) | `back(s=1.6)` | 5–7 f (0.22–0.28 s) | scale 0→1, peak 1.09 at 59% of duration | house; overshoot ≤ 10% (Penner back 1.70158 = 10%, industry norm); 1.8 overshoot [10:36] |
| Word slam (big kinetic word) | `ease_out` on scale 1.35→1.0 | 3–4 f (0.14 s) | 35% scale | house; 1.4 "smash" (~3 fast frames) [25:41] |
| Exit (element leaves while picture stays) | `ease_in` (cubic) | 5 f (0.20 s), ≤ entry | e.g. 120 px up + fade | house; 1.3 force accelerates [03:01]; Material exits shorter than entries (industry norm) |
| On-screen reposition | `ease_io` (smoothstep) | 8–12 f | any | 1.2 S-curve [14:01] |
| Count-up | `ease_out` on value | 18 f (0.75 s) | 0→N, integer per frame (on ones) | house; 1.6 value change [14:00] |
| Typewriter / line draw-on | linear | ~1 char per frame | n/a | 1.3 constant speed = balanced forces [02:00] |
| Mask wipe reveal (wordmark) | `ease_out` or `ease_io` on the edge | 12–15 f (0.5–0.6 s) | soft edge 120 px | 1.6 masking [15:00]; 1.2 nothing stops on a dime [13:32] |
| Settle/zoom-out after a hero lands | `ease_out` | 4 f (0.17 s) | scale 1.10→1.00 | 1.7 (5 f at 30 fps = 0.17 s) [07:02] |
| Anticipation before a hero move | `ease_io`, opposite direction (or on another property: scale dip, opposite rotation) | 2–3 f default; up to ~3× the main move for a held wind-up on the end-card logo only | ≤ 10% of main travel | "a few frames of opposite animation" 1.1 [07:00]; opposite direction 1.5 [02:31]; other property 1.5 [11:31]; ~3× held wind-up 1.5 [09:30]; frame count and amount are house proposals |
| Stagger, non-spoken siblings | same token each | 3 f (0.12 s) offset | n/a | house (c1 rows 0.12 s); 1.7 sequence layers [04:30] |
| Stagger, spoken items | same token each | on each word onset | n/a | ES §1; 1.6 offset & delay [11:01] |
| Overlapping child (check on its card) | `back` | starts at ≥ 85% of parent entry | n/a | house (t_in + 0.25 on a 0.28 s entry); 1.2 overlapping action [12:31] |
| Moving hold on stage | linear | whole cutaway | ≤ 2.5% scale over 6 s (≈ 0.17 px/frame at frame edge) | house; 1.2 moving hold [12:31] |
| Whip transition | power ease to/through the cut | 3.6 f each side (0.15 s half) | zoom 1.35 pre / 1.22 post, blur ≤ 160 px | house; ES §1 |

Frame conversions used: 0.14 s = 3.4 f · 0.20 = 4.8 · 0.22 = 5.3 · 0.25 = 6.0 · 0.28 = 6.7 · 0.30 = 7.2 · 0.35 = 8.4 · 0.45 = 10.8 · 0.60 = 14.4 · 0.75 = 18.0 · 0.90 = 21.6.

Measured spacing of the current tokens (per-frame displacement, frame 0→1, 1→2, …):
- 50 px / 0.28 s `ease_out`: 19.2, 13.5, 8.8, 5.2, 2.5, 0.8, 0.1 px — monotonic decel, visually at rest after frame 5.
- 120 px / 0.35 s `ease_out`: 38.0, 29.0, 21.2, 14.6, 9.3, 5.1, 2.2, 0.5 px.
- `back` 0.22 s scale per frame: 0, 0.667, 0.995, **1.089**, 1.057, 1.004, 1.0 — overshoot peak on frame 3, settled by frame 5.

#### B.5.2 Code audit of `gfx.py` / `render_v2.py` against the rules

| # | Finding | Rule | Evidence | Fix |
|---|---|---|---|---|
| F1 | **Punch-in shake.** `aroll()` centres `scale_about` on the raw per-frame YuNet box (`prep_faces.py` has no smoothing). Translation = centre × (1 − zoom), so detector jitter becomes picture shake: measured max per-frame jump ≈ 4.6 px on `06b_listing_0` (z 1.12), 4.1 px on `08a2_pure_veg_0`, and on the 1.55× SNAP inside `09_your_turn_0` up to ~0.55 × 34 px ≈ 18 px. The vignette centre in `grade()` moves with it too. | 1.3 random spacing = shake [06:00] | `faces_v2.json` centre steps: median 2.4–7.3 px, p95 up to 33.5 px | Use one fixed centre per segment (median of boxes), or a zero-phase low-pass (e.g. Savitzky–Golay over ≥ 9 frames); gate: punch-in centre second difference ≤ 0.5 px/frame². |
| F2 | **Entry phase not frame-quantised.** `prog(t, t_in, d)` with word times like 15.30 s means the first visible frame lands anywhere from p = 0.01 to 0.149, i.e. 3% to 38% of travel. The same token looks different every time. | 1.6 consistency [07:00]; 1.3 spacing [00:31] | `prog` is continuous; t_in values are word times | Snap `t_in` to `ceil(t_in*FPS)/FPS` and use whole-frame durations (`round(d*FPS)/FPS`). |
| F3 | **Hard pops with no origin.** "+" in c1 (t ≥ 2.52) and c3 (t ≥ 27.52) appear in one frame; c5 "EVERY WEEK" computes `pe` but draws the pill at full size (pe unused, likely a bug); the check-mark stroke and pill labels appear at p > 0.4–0.5 in one frame. | 1.6 origin [17:00]; 1.2 slow in/out [13:32] | `render_v2.py` c1/c3/c5, `gfx.state()` | Drive with `back(pe)` scale from an anchor; draw the tick as a stroke draw-on over 3–4 f (transformation, 1.6 [13:00]). |
| F4 | **Linear position/reveal moves.** Wordmark wipe edge = `p*1.25*W` linear over 0.6 s (constant speed, abrupt stop); road draw-on `clamp(pm*1.6 - k*.15)` linear; several fades (`pq`, `pl`, `ps`, `pm`, end-card label) are linear alpha. | 1.3 constant speed only when forces balance [02:00]; 1.8 linear default [07:30] | c3, end_card, front | Ease the wipe edge (`ease_out`); keep line draw-on linear but ease its last 3 f; opacity: see B.7 Q3. |
| F5 | **Inconsistent distances/durations for the same job.** Card-like entries use 50 px/0.28 s (c2, c4), 30 px/0.25 s (c5 rows), 40 px/0.35 s (browser, hook card), 100–120 px/0.35 s (listing, CTA pack), 30 px/0.45 s (end logo), 16 px/0.3 s (MARKET DIGITAL). | 1.6 consistency [06:30]–[08:00] | listed lines | Collapse to the B.5.1 tokens (row, panel, logo); vary only by size class. |
| F6 | **Whip blur direction does not match the motion.** The whip is a scale about (W/2, 0.4H) (radial motion) but `mblur` applies a vertical line kernel; ES calls it a "zoom-blur whip". | 1.7 motion blur = how real motion looks [05:02] | `compose()` whip branch | Radial/zoom blur (e.g. average of N scaled copies between z_prev and z_now). |
| F7 | **No motion blur on graphic moves.** Slide-ins peak at ~19 px/frame (50 px card) and ~38 px/frame (120 px panel) on the first frame with no blur. | 1.7 motion blur on every moving layer [05:02] | `row`, `c2`, `behind` | Blur each moving layer along its velocity vector with length ≈ 0.5 × per-frame displacement (180° shutter, industry norm); skip below ~4 px/frame. |
| F8 | **Parenting broken in compound text.** Price: "₹4,999" bounces up 30 px with `back` while " / month" sits still; c5 "FREE" bounces while "WEBSITE" is static. During the move the baselines disagree. | 1.6 parenting [12:31] | `front()` price, c5 head | Move the unit as one (or make the split explicit and stagger both). |
| F9 | **Anticipation absent.** No element ever pre-moves. Correct for list rows; missing on hero beats (price, "30+", logo). | 1.1 [07:00]; 1.2 [04:32]; 1.5 [04:01], [06:31] | whole file | Add a 2–3 f counter-move inside the element's own window on hero elements only. |
| F10 | **No parallax in cutaway push.** `stage_frame` scales grid, glow and cards together (one plane). | 1.6 parallax [19:00] | `stage_frame` | Optional: grid/glow drift at ~half the card push. |
| F11 | **Rows enter before they are spoken.** c1 search rows enter empty at 2.95/3.07/3.19 s, typing starts 3.46 s. Acceptable as containers, but conflicts with ES §1 literal reading. | ES §1; 1.6 narrative | c1 | Either enter each row on its spoken query, or document "empty containers may pre-roll". |
| F12 | **Entries running under transitions.** c1 head (1.48), c3 (24.42), c4 (35.20), c5 (42.36) start before the snapped cut, so viewers see only the last 30–40% of the ease — the content arrives "already there". Intentional pre-roll, but it removes the visible entry. | 1.1 timing [04:31] | c1/c3/c4/c5 | Decide per cutaway: either show the full entry after the whip clears, or keep pre-roll and make sure something visibly settles in the first 6 frames. |
| F13 | **Scaled text re-rasterised per frame.** The every-day word slam renders `font(int(sz*sc))` each frame, so size steps by whole px with re-hinting; can wobble. | 1.3 random spacing [06:00] | `behind()` 05_every_day | Render once at the largest size and scale the image with `scale_any`. |
| OK | Things that already follow the rules: `ease_out` entries; `ease_in` exit on the every-day words (0.2 s, shorter than entry); `back` 9% overshoot settling within 2 f; checks pop at t_in + 0.25 on a 0.28 s entry (overlapping action); count-up with `ease_out`; stage 2.5% and A-roll 1.5% moving holds; typewriter at constant rate; whip zoom eased into and out of the cut; 2× supersampled drawing (crisp edges at subpixel positions). | 1.2, 1.3, 1.6 | | |

#### B.5.3 Gates (metric, threshold, how to measure)

Build one instrument first: **motion log.** Wrap every animated draw call in `render_v2.py` so it records, per frame and per element id: x, y, scale, rotation, alpha, bbox (from the layer's alpha channel). Write `motion_log.json`. All gates below read it; F-gates read rendered PNGs in `frames_v2/`.

| Gate | Metric | Pass threshold | How to measure |
|---|---|---|---|
| G1 Easing curve | Shape of per-frame displacement d[k] for each entry | Entry: d monotonically non-increasing after frame 1 (decel). Exit: monotonically non-decreasing. Reposition: rises then falls once. Tolerance 0.5 px. | motion log; second difference sign test. Source 1.3 [00:31], 1.2 [13:32] |
| G2 No linear starts/stops | Ratio of first-frame to mid-move displacement | Entry first step ≥ 1.5× median step OR element is on the linear whitelist (typewriter, draw-on, drift, sweep) | motion log. 1.8 [07:30], 1.3 [01:31] |
| G3 Shake | Second difference of element centre (and of punch-in centre/translation) during holds | ≤ 0.5 px/frame² while an element or the A-roll framing is meant to be static or uniformly moving (house threshold) | motion log for graphics; for A-roll, log `scale_about` tx/ty per frame; on frames: phase-correlate consecutive A-roll frames on background area (cv2.phaseCorrelate outside the matte) and flag oscillation. 1.3 [06:00] |
| G4 Overshoot | Max scale / rest scale for pops; max position past target | ≤ 1.10 (10%, Penner norm); position overshoot ≤ 10% of travel | motion log |
| G5 Settle | Frames from overshoot peak to within 0.5% of rest | ≤ 3 frames for pops; element at rest (≤ 0.5 px/frame) within duration + 1 f | motion log. 1.1 [07:31] |
| G6 Duration tokens | Entry/exit length in whole frames, per element class | Within the B.5.1 token for its class ±1 f; exit ≤ entry | motion log; class tag on each element |
| G7 Frame quantisation | Fractional phase of each entry start | Start time × FPS within 0.01 of an integer | motion log (or static check on `t_in` values) |
| G8 Consistency | Spread of (distance, duration, curve) across same-class elements in the whole ad | Identical token (zero spread) unless the class differs | motion log grouped by class. 1.6 [07:00] |
| G9 Spotlight | Number of primary elements in motion (speed > 2 px/frame or scale change > 0.5%/frame) per frame | A-roll: ≤ 1 graphic mover; cutaways: ≤ 2 primary movers at once (excluding the stage drift and overlapping children). House threshold; videos give the principle, not the count | motion log. 1.6 [22:00] |
| G10 Word sync | Offset between element entry start (and settle frame) and its word onset | Start ≥ word onset − 0 f (ES: nothing before it's said); settle ≤ word onset + 10 f | motion log vs `v2_words.json`. ES §1, 1.1 [04:31] |
| G11 Hold before hero | Total graphic motion (sum of |d|) in the 6 f before a tagged hero element starts | ≤ 2 px (calm beat). House threshold | motion log; tag hero ids. 1.1 [05:31] |
| G12 Origin | First visible frame of every element | Alpha < 0.5 or scale < 0.5 or position offset > 0 on its first frame (i.e. it is not fully formed instantly), except captions (ES style) | motion log; F3 items currently fail |
| G13 Motion blur | Layers moving > 4 px/frame have blur; blur direction matches velocity | Blur length within 0.3–0.7 × per-frame displacement (180° shutter ≈ 0.5, industry norm); angle within 15° | motion log + render flag; on frames, compare edge sharpness (Laplacian variance) of moving vs resting bbox. 1.7 [05:02] |
| G14 Face clearance across the whole move | Overlap of every graphic bbox with YuNet face box, every frame, including overshoot peak and start offset | Zero overlap (ES Face gate), evaluated over all animation frames, not just rest | motion log bboxes vs `faces_v2.json`. 1.2 [16:33] |
| G15 Safe area across the whole move | Text bbox inside the 60 px safe area at every frame (start offset and overshoot included); whip frames exempt | ES Text gate, every frame | motion log. Note c2 rows start at x = 60 px, exactly on the margin |
| G16 Raster scale | Max on-screen size of each raster (logo PNG, icon PNG) × supersample ÷ source px | ≤ 1.0 | static check of `LOGO` and `_icon_img` sizes at peak `back`. 1.4 [16:01] |
| G17 Moving hold | On any hold > 24 f (1 s), something moves | Some element or stage scale changes ≥ 0.05%/frame | motion log. 1.2 [12:31] |
| G18 Transition blur geometry | Whip blur kernel matches zoom (radial) | Radial blur present; no single-axis smear on a scale move | frame check: structure tensor orientation around frame centre on whip frames. 1.7, ES §1 |
| G19 Exit defined | Every element has an exit token or ends under a transition/cut | 100% | motion log: last visible frame classified |
| G20 Anticipation shape | For elements tagged `anticip`: sign of displacement (on the anticipating property) before vs after the turnaround frame; acceleration at the start of the wind-up; motion during a held wind-up | Wind-up displacement is opposite in sign to the main travel; amount ≤ 10% of main travel (house); velocity changes sign exactly once; if the wind-up is > 3 f, its first-frame displacement ≤ 0.5× its peak per-frame displacement (eased, not a sudden start); a held wind-up never has > 2 consecutive frames of zero change. G1 is applied to the main phase only (after the turnaround) | motion log; tag hero ids. 1.5 [02:31], [10:00], [10:30] |

### B.6 Anti-patterns / failure modes

| Anti-pattern | Symptom | Fix | Source |
|---|---|---|---|
| Linear default | Elements glide at constant speed and stop dead; feels "computer-made" | Ease by force story (B.5.1) | 1.3 [01:31], 1.8 [07:30], 1.2 [13:32] |
| Random spacing / jitter | Picture or text trembles at rest; punch-in "breathes" frame to frame | Smooth the driver (face track), render text once and transform | 1.3 [06:00] |
| Ease-everything-the-same | Bounces/hops eased at both ends look like floating, not bouncing | Choose curve per force (gravity: speed up falling, slow rising; smash into contact) | 1.3 [04:31], 1.4 [25:41] |
| Too much overshoot | Rubbery, cartoonish UI; text unreadable while wobbling | ≤ 10% overshoot, settle ≤ 3 f, no overshoot on large panels | 1.1 [09:31] (clean graphic), 1.6 [21:01] |
| Everything moves | Eye cannot find the message; ad feels busy | One primary mover at a time; hold the rest still | 1.6 [22:00] |
| Things pop from nowhere | Elements flash in at full size | Grow from an anchor, slide from a direction, or mask-reveal | 1.6 [17:00] |
| Slapping screens together | Whole card stacks appear at once; viewer must parse relationships | Main item first, children one by one on their words | 1.6 [12:01] |
| Twinning | Several items move identically at the same instant; mechanical | Same token, offset in time | 1.2 [22:30], 1.7 [04:30] |
| Inconsistent vocabulary | Each cutaway animates differently; subconscious "off" feeling | Token table, one per element class | 1.6 [07:00]–[08:00] |
| Secondary competes with primary | Decorative motion near the face or during the key word | Keep secondary small, away from the face, after the primary lands | 1.2 [16:01]–[16:33] |
| No hold before a reveal | Price/number lands while other things are still moving; loses impact | 6+ calm frames before the hero | 1.1 [05:31] |
| Frozen holds | Cutaway looks like a still image | Slow push / moving hold | 1.2 [12:31] |
| Blur that does not match motion | Vertical smear on a zoom transition | Blur along the actual motion vector (radial for zoom) | 1.7 [05:02] |
| Raster scaled up | Soft, pixelated logo or icon at overshoot peak | Source ≥ display × supersample | 1.4 [16:01] |
| Effect-for-effect's-sake | Glows, reflections, light sweeps on everything; template look | Restrict to end card; keep design principles in charge | 1.1 [09:00], 1.6 [21:30] |
| Physically impossible motion without reason | Viewer recoils (the folding knife) | Exaggerate only in a believable direction | 1.6 [06:30], 1.3 [05:31] |
| Equal-length beats | Rhythm feels flat, "not much story" | Vary hold lengths with the script's emphasis | 1.1 [05:03] |
| In-between-only blocking | The hero move goes evenly from start to end with nothing behind the start; it reads as boring | Place the key pose slightly behind the start (opposite to the travel) | 1.5 [05:02] |
| Missed start | A graphic moves away from where the eye is; the viewer catches only its end and darts around | Add a small lead-in or anticipation that pulls the eye first | 1.5 [06:31]–[07:00] |
| Jerky two-key anticipation | A large or slow move snaps backwards with a sudden acceleration | Add the extra key and ease into the wind-up; keep the two-key bump for small, fast moves | 1.5 [10:30] |
| Dead wind-up | The element hangs frozen at the anticipation extreme | Tilt the handles so the value keeps creeping while energy builds | 1.5 [10:00] |

### B.7 Conflicts & open questions

1. **Anticipation vs ES §1 "Nothing appears before it's said."** 1.1 [07:00], 1.2 [04:32] and 1.5 [04:01] want a wind-up before major actions (1.5 also uses it as the attention signal [07:00]); ES forbids anything showing before its word. **Call:** keep ES. Anticipation is allowed only inside an element's own window (starting on the word onset) or on an element already on screen (a card dips 2–3 f before its check pops). Never pre-roll a new element before its word.
2. **Entries pre-rolled under transitions (F12) vs ES §1 and 1.1 timing.** The code starts some cutaway content up to 0.15 s before the snapped cut; it is hidden by the whip so it does not break ES visually, but the viewer loses the entry motion. **Open question for the reviewer:** in their inspiration edits, does cutaway content arrive visibly after the whip, or is it already in place? Measure with the motion log on an inspiration render, then set the rule.
3. **Opacity easing.** The videos only discuss spatial/temporal easing; none says whether alpha fades should be eased. The code fades both eased and linear. **Call (house):** tie alpha to the same eased p as the position (as `c2`/`c4` already do); allow linear alpha only for fades ≤ 4 f. Flag for review.
4. **ES caption style vs 1.6 origin.** ES captions show each word instantly as spoken (no motion). 1.6 says nothing should burst into existence. **Call:** keep ES; captions are text, not objects, and animating each word adds motion noise against the spotlight rule (1.6 [22:00]). G12 exempts captions.
5. **"Secondary action" means different things.** 1.1 [08:00] and 1.2 [15:33] define it as a different motion that supports the main action (head offset, smoke trails). 1.7 [03:34] uses it for a smaller repeat of the main move after it ends, which is really follow-through/settle. **Call:** use 1.1/1.2 definitions; file 1.7's bump under follow-through/settle.
6. **Consistency (1.6) vs avoid twinning (1.2).** Same motion for every row vs no identical moves. **Call:** both hold: identical token, different start times (stagger).
7. **Ease everything (1.6 [10:00], 1.8 [07:30]) vs "don't blindly ease in and out" (1.3 [04:31]) and "smash" with no slow-in (1.4 [25:41]).** **Call:** ease by force story; a slam/smash and a whip legitimately keep speed into contact.
8. **Motion blur on everything (1.7) vs ES §2 "highest quality / no added artefacts".** Blur is not grain, but heavy blur on text reduces legibility during the move. **Call:** blur only frames with > 4 px/frame motion, length ≈ 0.5× displacement; the text is legible again once settled, which is when it is read.
9. **Light sweep, reflection, zoom-out (1.7) vs the test look (black stage, green grid, glow; now preset `profitcast-dark`).** Not in ES. **Call:** the 110%→100% settle transfers (end card logo); reflection and 3-second light sweep do not, unless the client's inspirations use them.
10. **ES has no motion gate.** §4 lists 13 gates; none checks easing, shake, overshoot, consistency or spotlight. **Call:** add a "Motion" row to ES §4 pointing to G1–G19 (motion log), with G3 (shake, which would fail today: F1) and G12 (origin, which fails today: F3) as must-pass.
11. **ES Face and Text gates are checked at rest.** Moves have start offsets and overshoot peaks (c2 row starts at exactly the 60 px margin). **Call:** evaluate both gates over every animation frame (G14, G15).
12. **ES punch-in "about 1.15×" vs code 1.12–1.14 and the 1.55× SNAP.** Not a motion-design conflict, but the larger the zoom, the more face-track jitter is amplified (F1). The SNAP needs a fixed centre.
13. **ES §1 "Numbers count up"** agrees with 1.6 value change [14:00]. No conflict. The "+" appended after the count should pop with an origin (F3), not appear.
14. **ES §1 "Rotoscoping is a spice"** agrees with 1.6 moderation [21:30] and spotlight [22:00]. No conflict.
15. **ES §3 SFX "on the frame"** pairs with 1.3 [07:00] (contact poses are where forces change): the SFX frame for a pop is the frame it first reaches full scale (the overshoot-peak frame for `back`), for a slide the first frame with displacement < 1 px, for a slam the first frame at scale 1.0. Open question for module 5 owners: confirm which frame the inspirations hit.
16. **Numbers without source.** The videos give few hard numbers (7 frames per move at 24 fps in 1.4; three hold poses 4 frames apart and an anticipation up to ~3× the main move in 1.5; 20 frames main + ~10 frames secondary, 110→100% over 5 frames, 20% reflection, 1–4 s sweep at 30 fps in 1.7; 9% overshoot is the house constant). The spotlight count (G9), hold (G11), shake threshold (G3), anticipation size and stagger are house proposals; calibrate them on the client's inspiration edits before making them hard failures.
17. **1.5 has been re-sourced** (Ben Marriott's anticipation lesson replaced the course trailer). **1.4** is still mostly an interface tour; consider replacing it with an overshoot/settle lesson if this module is re-run.
18. **1.5 "anticipation is the most important principle; hold it up to ~3× the main move" vs the house token (2–3 f) and the spotlight/moderation rule (1.6 [21:30]–[22:00]).** On a 30–60 s Reel every word has a graphic, and a 3× wind-up on each would delay every element behind its word and add motion noise. **Call:** anticipation stays hero-only. Use 2–3 f by default; the long held wind-up is allowed on the end-card logo, or on one hero beat where the voice pauses. Its attention role (1.5 [06:31]–[07:00]) is the main reason to use it in an ad. G20 checks the shape whenever it is used.

---

## Per-video rule counts
| Video | Rules |
|---|---|
| 1.1 Envato, The Principles of Motion Design | 29 |
| 1.2 StudioBinder, The 12 Principles of Animation Explained | 45 |
| 1.3 Alex Grigg, The Secret Science of Spacing (replacement) | 20 |
| 1.4 School of Motion, The Power of Animation Principles | 29 |
| 1.5 Ben Marriott, The #1 Skill All Animators Need (replacement; was a 4-rule trailer) | 31 |
| 1.6 Design Sundays ft. Atul Khola, 12 Principles of Motion Design | 35 |
| 1.7 Ag Motion Designs, 5 Logo Animation Principles (replacement) | 17 |
| 1.8 Motion By Scott, How To ACTUALLY Learn Motion Design | 25 |
| **Total** | **231** (was 204) |
