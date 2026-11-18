# Module 5: Sound Design & Audio Mixing

> **Note (style profiles).** This module was written while CVES was tested on its first ad. Its research rules are universal; where it speaks of the "house" look or a house number for a per-client choice (palette, accent colour, grade, transition kinds, cutaway share, caption position, bed level), read it as the value from the client's style profile (`docs/STYLE.md`). The black stage / green accent / warm moody A-roll measured here is now the optional preset `profitcast-dark`, not the default.

Dissected against `tools/DISSECTION-BRIEF.md`. All 8 transcripts in `transcripts/5 Sound Design & Audio Mixing/` read in full.
Edit standard cross-checked: `knowledge-base/EDIT-STANDARD.md` §3 (Sound) and §4 (gates).

**Source caveats up front**
- **5.5 was replaced.** The first resolved video (Thomas Flight's "The Real Villain of Nope") had no sound content. It is now Jason Yadlovski's "Proper Audio Levels for Video Editors (Dialogue, Music & SFX)", the module's only source with explicit dialogue, music, SFX and master-loudness numbers. Its transcript file had to be re-fetched (see A.5).
- **5.8 is a weak title match but on topic.** The curriculum asked for "Sound effects without being cheesy"; the resolved video is "How Dialog Should Sound! (Basic Film Audio Design)": a dialogue EQ walkthrough. Useful, but nothing on SFX cheesiness. The cheesiness angle is covered by 5.1 [12:00–13:32] and 5.4 [03:00–03:30].
- **5.3** is the same StudioBinder diegetic/non-diegetic video as 2.7; dissected here for its sound and mix use.
- **5.4** is Herman Huang's "3 Sound Design Secrets That Feel Like CHEATING" (manual replacement).
- **5.7** is "A Quiet Place: How to Write Sound into a Screenplay" (Lessons from the Screenplay), so it is a film analysis plus interviews with the supervising sound editors.

**Level vocabulary used in this file.** The videos give **peak-meter dBFS** (5.1) and **EQ/fader gain changes in dB** (5.6, 5.8). 5.5 gives peak-meter dB targets per stem and LUFS for the **master** only. None of them gives LU/LUFS figures between stems. The house spec uses **LU** (integrated loudness difference, EBU R128). These are not interchangeable. Speech is peakier than a mastered music bed, so a given peak gap is usually larger than the matching loudness gap. Where I convert, I say so and label it as my estimate, not the video's.

---

## A. Per-video dissection

### 5.1 How to SOUND DESIGN a Video | Step-By-Step Tutorial
- **Source:** 5.1 · "How to SOUND DESIGN a Video | Step-By-Step Tutorial" · Film Editing Pro · https://www.youtube.com/watch?v=Wcxw3BPSt3A · 1026 s (17:06) · 2,512 words · direct match (1).
- **Thesis:** Sound design is built in layers: first the score, then ambience and Foley, then creative accents. Each layer is cut to the edit, varied, placed in the room, and used sparingly, so that only the key moments hit hard. The final mix holds dialogue above SFX above music.

**Rules**
1. Treat footage as arriving MOS ("without personality"); the editor supplies its character through sound. [00:00]
2. Do a quick first pass, critique it, then do a slower second pass. Plan for at least two versions. [00:00]
3. Build in three steps, in order: (1) score, (2) ambience + Foley, (3) creative sound design. [00:30–01:00]
4. Lay temp music even if a composer will score later. It lets you design SFX in context and communicates your vision to others. [00:30]
5. "We should be able to hear everything we see." Give every visible action a sound. [00:30]
6. Nothing is silent. Even an empty room makes noise, so never leave a location in digital silence. [00:30]
7. Sound does not have to match what it looks like. Add sound for things we cannot see: thoughts, feelings, **camera moves**. [01:00]
8. Use the first-pass critique checklist: (a) does the score's tone match the edit throughout? (b) is there ambience in quiet moments? (c) do the SFX vary? (d) are any sections uncovered? (e) are studio-dry assets placed in the room? (f) is sound used non-literally anywhere? [02:36–03:30]
9. Anti-pattern: a music cue that drifts into a different mood (it turned "lighter-hearted… crime drama") partway through. Cut away before the tone change. [02:36, 04:01]
10. Anti-pattern: no ambience in quiet moments makes the soundscape "noticeably dead", missing the hum and hiss of everyday life. [02:36]
11. Anti-pattern: the same keyboard sound for every keystroke, the same pen sound for every stroke. [03:01]
12. Once sound design starts, gaps become very obvious. Cover the whole edit consistently. [03:01, 06:31]
13. Studio-recorded assets lack the reverberation of the on-screen room. Add matching room reverb. [03:01, 07:30]
14. A stock cue won't line up with your edit unless it was scored for it. Cut it up to match the edit instead of playing it straight. [03:30–04:01]
15. Use a cue's beginning (cut before its tone change) for the opening, then a small section from its end for a later key moment, with the **final hit lined up to the on-screen event** (the staple pull). [04:01]
16. Join cue sections that sound alike so the music edit is invisible. [04:01]
17. Arrhythmic orchestral music is easy to edit because there are no beats to line up. [04:01]
18. Cut the cue so its hits and dips land on the loud and quiet moments of the picture. [04:30]
19. Work on ambience with score and SFX muted, so you hear what you're building. [05:07]
20. Every location needs ambience unless the film is set in space. Ask what the place really sounds like (an empty office: air-conditioner hum). [05:07–05:31]
21. Give exterior shots their own bed (wind for the single outside POV). [05:31]
22. Lower every ambience to "a suitable level" below the foreground. [05:31]
23. For repeated actions, take a long multi-variant clip (a 10 s typing clip), cut out individual hits, and **use each variant once**, aligned to the on-screen action. [06:01]
24. Edit SFX with waveforms visible and line up the **apex** (transient peak) of each sound with the visual event. Use markers. [06:01–06:31]
25. Be thorough: blinds, watch, door knocks; every small action gets a sound. [06:31]
26. When a library lacks a sound, substitute one with the same character (scissors' metal-on-metal for a staple remover). [06:31]
27. Record Foley at your desk straight into the timeline while watching the edit. The performance can be rough because you chop it to sync afterwards. [07:00]
28. Route all Foley through one **submix/bus** and put the room reverb on the bus, not per clip. [07:30–08:00]
29. Sound is most powerful when it says what the audience cannot see (emotions). This is "the single biggest" improvement available. [08:00]
30. Don't let titles/credits play in complete silence. Add chimes synced to the text reveal and a drone leading into the first cue. [08:30]
31. A **reverse impact** makes a moment more sinister. [08:30]
32. Whooshes add levity and reinforce comedy. Put them on quick character movements and on camera moves. [09:01–09:31]
33. A reverberating **hit** tells the audience an ordinary action (a box set on a desk) has consequences. [09:31]
34. Sound design is iterative; you won't get it right in one pass. [10:01]
35. Reinforce the score with SFX: an impact on the first musical stab. [10:01]
36. Layer additional sounds that share **tone and frequency** with the natural sound; then they blend in (bone crunch layered on a staple remover and shredder). [10:34]
37. Once you commit to a style (stylised whooshes/hits), stay consistent through the whole piece. [11:01]
38. Visual movement and lighting changes are the cues for accent moments. [11:30]
39. Accent recipe for a transition: a **reverse cymbal** rising into the cut, plus a **bass drop starting exactly on the cut**. [11:30]
40. Not every moment needs an accent, and not every accent needs full intensity. Balance them. [12:00]
41. Anti-pattern: a bass drop plus a hit on a soft, non-climactic pause is "far too intense". [12:31]
42. "If you try to make every moment special none of them will be special." Pick the key moments. [13:00]
43. A secondary moment still gets design, just subtler (the cymbal alone, hits removed). [13:00]
44. Climax recipe: score lined up, plus a reverse cymbal ("suckback"), plus a boom, signalling resolution and setting up the next scene. [13:32]
45. The mix sets score, dialogue and SFX at correct levels **relative to each other**. [14:01]
46. Nothing should peak (clip). [14:01]
47. **Dialogue around −12 dB** on the meter; it is one of the loudest things in the mix so it can be understood. [14:01]
48. **Sound effects anywhere from −10 to −30 dB**, depending on what they are. [14:01]
49. **Score around −20 to −30 dB.** [14:01–14:31]
50. Build like a brick wall: many small touches. Lay the foundations first (score, ambience, Foley), then add creativity. [15:30]
51. Follow a consistent workflow, but think outside the box creatively. [15:30–16:00]

**Count: 51 rules.**

---

### 5.2 Sound Design for Cinematic Filmmaking | My Process
- **Source:** 5.2 · "Sound Design for Cinematic Filmmaking | My Process" · Jacob Nordin · https://www.youtube.com/watch?v=I66_LmOTlSk · 636 s (10:36) · 1,915 words · direct match (1). Contains an Artlist sponsor segment [04:35–05:30]; only its stems point is kept.
- **Thesis:** Work in priority order (voice first, then music, ambience, realistic SFX and creative SFX). Use space (panning, reverb), EQ, J/L-cuts and silence to make it feel immersive. Finish with a clean, normalised mix checked on several speakers.

**Rules**
1. Sound shapes a film's flow and pacing, adds depth to the edit, and connects the viewer, often unconsciously. [00:03]
2. Don't obsess over visuals at audio's expense. Sound sets mood the way lighting and grading do. [00:03–00:31]
3. **Vocals (dialogue or VO) are usually the most important sound.** Never let them get lost: not too quiet, never overpowered by other elements. [00:31–01:00]
4. Background music is second. It sets the pacing and overall mood. [01:00]
5. Option: choose the music before shooting, so its energy informs the shoot (doesn't suit every video). [01:00]
6. Add sound design after voice and music, starting with ambience. [01:00–01:33]
7. Ambience is usually the first sound-design layer. It establishes place and makes the scene feel alive, and it **shouldn't be overpowering** ("just be there in the background"). [01:33]
8. Pick ambience for the location: wind, city noise, lapping water, birds. Subtle, but it grounds the audience. [01:33–02:00]
9. SFX category 1: sounds from the environment (doors, footsteps, anything that would make a sound). They don't draw attention but form the foundation. Foley belongs here. [02:00–02:30]
10. SFX category 2: creative SFX added as a choice rather than for realism (whooshes, impacts, risers). [02:30]
11. Use **whooshes** to make cuts, transitions and movements feel intentional. [02:30–03:00]
12. Use **risers** to build anticipation and suspense, most often leading up to a reveal or smoothing a cut into a very different environment or energy level. [03:00]
13. The absence of sound matters as much as its presence. Silence or a quieter moment builds contrast and makes the return of sound or music hit harder. [03:00–03:30]
14. Sound needn't be literal. Decide how the audience should feel and choose sounds for that emotion (rain, neighbour's music, a tuk-tuk turned into a sports car). [03:30–04:00]
15. Use music **stems** to mute a distracting instrument and build an underscore that fits the story. [05:00]
16. **Pan** sounds left/right to match their on-screen position. Subtle panning makes the soundscape dynamic and realistic. [05:30–06:01]
17. Use a **J-cut**: start the next scene's audio before the visual cut, fading it in, so the cut is hidden and feels motivated. [06:01–06:30]
18. Use an **L-cut**: let the previous scene's audio linger after the visual changes. [06:30]
19. Ambience tracks fade in and out across cuts as J/L-cuts. [06:30]
20. Three effects used on every project: reverb, EQ, and (implicitly) filters. [07:01]
21. Reverb amount follows room size: a small room gets a tiny amount, a large church a lot. [07:01]
22. Add reverb to a dry or abrupt SFX to make it feel larger and more fluid. [07:31]
23. More reverb pushes a sound further into the background (distant birds). [07:31]
24. Use EQ to enhance voices. [07:31–08:01]
25. Use EQ to make room. When music and VO share frequencies, **remove the voice's frequencies from the music** so the voice is more prominent. [08:01]
26. A high-pass cuts lows and a low-pass cuts highs. Use them to fake a phone speaker, muffled audio or underwater. [08:01–08:31]
27. In the mix, nothing should be too loud or too quiet, and **levels stay consistent throughout**. [08:31]
28. Stacked layers make levels creep into the red. **Clipping** sounds bad after export. [08:31–09:02]
29. If the balance is right but the overall level is too hot, lower the master bus. [09:02]
30. On export, **normalise the whole mix to the target platform's loudness standard** (Resolve Deliver > Audio normalisation) to avoid extra platform compression. [09:02]
31. Before publishing, listen on several different speakers. [09:31]
32. Method: watch each clip, list the sounds present in that environment and the feeling you want, and build from that. [09:31–10:01]
33. Sometimes one or two layers of sound are enough. [10:01]

**Count: 33 rules.**

---

### 5.3 Ultimate Guide to Diegetic vs Non-Diegetic Sound (sound-mixing angle)
- **Source:** 5.3 · "Ultimate Guide to Diegetic vs Non-Diegetic Sound — Definitions, Examples, & How to Break the Rules" · StudioBinder · https://www.youtube.com/watch?v=2vlwm4VyyTc · 1047 s (17:27) · 1,880 words · search match (0.83), confirmed on topic. Same video as 2.7.
- **Thesis:** Every sound is either inside the story world (diegetic) or heard only by the audience (non-diegetic), and on-screen or off-screen. Deliberately crossing, withholding or subverting these categories is a storytelling tool.

**Rules**
1. Most sound design is meant to go unnoticed, but it is a key tool. Listen to films, not just watch them. [00:00]
2. Diegetic = everything the characters can experience in their world. Non-diegetic = what only the audience perceives. [00:30–01:01]
3. Non-diegetic elements can be visual too: title cards, captions ("tyrants" is a transcription error for chyrons) and external inserts. [01:01–01:31]
4. Chion's three zones: off-screen diegetic (unseen birds), non-diegetic (score), and visualised (the source is on screen). Every sound falls into one, and sounds can switch zones. [02:04–03:00]
5. Diegetic sound includes weather, vehicles, weapons, music inside the film, dialogue and some voice-over. [03:00–03:30]
6. A voice-over of a character's thoughts is **internal diegetic**: part of the story world even though no one else hears it. [03:30]
7. Diegetic sound builds the world. **Off-screen** diegetic sound informs the setting and extends the world beyond the frame. [03:30–04:01]
8. Audiences take diegetic sound for granted; breaking expectations makes exciting cinema. **Silence where a huge sound is expected** (The Last Jedi). [04:36–05:01]
9. Juxtapose a sound against the action for counterpoint (Singing in the Rain over violence). [05:01]
10. Point-of-view sound: let us hear what the character hears, like a POV shot. [05:01–05:30]
11. Sound can show a compromised mental state as well as imagery can. [05:30]
12. Non-diegetic sound = SFX the characters can't hear, the score, and narration. [06:32]
13. A narrator who plays no role in the film is non-diegetic; this harks back to verbal storytelling. [07:01]
14. Risk: recognisable, intrusive non-diegetic narration breaks the illusion and the fourth wall (Tarantino's voice). Use it only deliberately. [07:30–08:01]
15. **Non-diegetic SFX can enhance motion and add intensity.** [08:01]
16. Non-diegetic SFX can land a punchline for comedy. [08:31]
17. The score is the most-used non-diegetic sound. Audiences accept it, and it carries emotion: transcendence, heartbreak, triumph. [08:31–09:30]
18. **Trans-diegetic sound** (switching modes) subverts expectations: a "score" turns out to be playing in the scene. [09:30–10:01]
19. Score can become diegetic (on a character's radio), and diegetic music can become non-diegetic over a montage to **smooth time jumps**. [10:01–11:08]
20. Carry a sound effect across a scene cut and let it change function. The wind starts diegetic and becomes non-diegetic over the next scene (Raising Arizona). [11:08–11:31]
21. A narrator who later appears on screen re-frames everything heard before (The Big Lebowski). [11:31–12:02]
22. Switching between diegetic and non-diegetic blurs fantasy and reality. Revealing the "score" drummer in scene shows an unstable mind (Birdman). [12:02–12:30]
23. Breaking the boundary completely (a narrator arguing with characters) is a comedic device. [12:30]
24. Some sounds fit no category (narration from a disembodied spirit, narration that turns out to be testimony, a character singing along to "score" that is in his head). Ambiguity can be the point. [13:01–15:00]
25. Diegetic background music can become internal music in a character's head to motivate a choice (La La Land). [15:00–15:36]
26. Plan sound in pre-production like cinematography and editing. [16:34–17:00]

**Count: 26 rules.**

---

### 5.4 3 Sound Design Secrets That Feel Like CHEATING (replacement for "How Sound Design Tricks Your Brain")
- **Source:** 5.4 · "3 Sound Design Secrets That Feel Like CHEATING" · Herman Huang · https://www.youtube.com/watch?v=tzfzkTAQsnE · 442 s (7:22) · 1,406 words · manual replacement (1.0). Happy Editing sponsor segment [02:01–03:30]; its "commit to a style" point is kept.
- **Thesis:** (1) Layer by frequency: in SFX, and between music and dialogue by carving a mid-range pocket. (2) Commit to one coherent sound palette for the piece, or break it deliberately for emotional realism. (3) Get into and out of music cleanly: reversed risers in, a reverb tail out, sweetened with SFX.

**Rules**
1. People scroll on mute, but **visuals grab attention and sound keeps viewers hooked**. [00:01]
2. Flat SFX come from how sounds are used, not which. One whoosh suits a small movement but is too thin for a big, dramatic one. [00:30]
3. A deeper whoosh alone still lacks weight. **Layer sounds that cover different frequency ranges** ("like a cake") for a full, dynamic sound. [00:30–01:01]
4. Thinking in layers beats endlessly scrolling for the "one" right SFX. [01:01]
5. Anti-pattern: dropping dialogue on the timeline, lowering the music gain, "and just call it a day". [01:30]
6. **Carve a pocket in the music's mid frequencies** for the dialogue, using a de-esser/dynamic EQ on the music track. The dialogue "naturally sits in that pocket". [01:30]
7. EQ the dialogue to cut its low and high ends so it fits the pocket better. [01:30]
8. Giving each element its own frequency space makes a fuller mix. [01:30–02:01]
9. A generic all-purpose SFX library sounds "safe". Match the SFX palette to the genre (athletic commercial vs wedding vs corporate). [02:30]
10. **Commit to a style instead of mixing random sounds.** The sounds should match the visual aesthetic so the piece feels coherent. [03:00]
11. Genre fit examples: gritty bass hits don't suit corporate videos; clean bell dings don't suit a streetwear promo. [03:30]
12. Using one sound pack keeps a video, or a body of work, consistent. [03:30]
13. Cheat code: deliberately **mismatch** sounds with picture ("emotional realism", from Euphoria) to show how something feels rather than what it literally is. [03:30–04:01]
14. Constrain the mismatch to a theme (only nature sounds: coffee grounds become cracking icebergs, a coffee swish becomes an ocean crash). [04:01–04:31]
15. Problem: fitting a 3-minute song into a 30-second promo. Ending a song early feels like slamming the brakes. [04:31–05:01]
16. Auto-remix tools are decent, but you usually need manual control to fit visuals and emphasise key moments. [05:01]
17. **Entry:** if the song has no natural lead-in, take its opening beat, reverse it, and use it as a riser into the song. [05:01]
18. Or reverse the song's tail and use it as the riser. [05:30]
19. Reversed-riser entries also work for introducing a second song or coming back in after a bridge or quiet moment. [05:30]
20. **Exit:** cut before the next beat hits and put reverb on the final beat (nest the clip and extend it so the tail can ring; start from a "Great Hall" type preset). [05:30–06:00]
21. Option: fade the original's end slightly and play the reverb version underneath. [06:00–06:33]
22. Make it seamless by **layering SFX on these joins**: risers, swells or a suckback under an entry. [06:33]
23. Use SFX on exits too, to emphasise the moment. [06:33]
24. To make a song ending hit harder, add impacts, slams or hits to "wrap it all up with a bang". [07:01]

**Count: 24 rules.**

---

### 5.5 Proper Audio Levels for Video Editors (Dialogue, Music & SFX) (replacement for "The Art of Sound Mixing in Film")
- **Source:** 5.5 · "Proper Audio Levels for Video Editors (Dialogue, Music & SFX Explained) [Works in Any Video Editor]" · Jason Yadlovski · https://www.youtube.com/watch?v=sbCd91VG22w · 2012 s (33:32) · 7,558 words · manual replacement (match 1.0). It replaces the off-topic Thomas Flight "Nope" essay.
- **Transcript note:** when this module was re-dissected, the transcript file still held the old "Nope" body under the new header. The real captions (YouTube auto `en-orig`) were re-fetched on 2026-11-18 and written into the file, and the dissection below uses them. The auto-captions drop the "1" in some numbers: "minus4 lus" means −14 LUFS ([21:01], [26:32], [31:31]), "minus2 dB" means −2 dB, and the "−6.1 / −6 dB" integrated readings at [26:00] are almost certainly −16.1 / −16 LUFS (flagged where used). The demo is in DaVinci Resolve, but the numbers are presented as editor-independent. Course plug [32:01–32:30] ignored.
- **Units:** the stem and clip levels are **peak-meter readings in dB (dBFS)** on the NLE mixer meters. His normalise mode is "sample peak program". The only **loudness (LUFS/LU)** figures are for the **whole master** (−14 LUFS for YouTube). The video gives no LU offsets between stems.
- **Thesis:** Stop setting levels by feel. Organise the tracks, set clip levels to fixed meter targets with headroom (dialogue ≈ −10 dB, music ≈ −10 dB alone or ≈ −20 dB under dialogue, SFX −2 to −30 dB), process, then mix with faders, then master to the platform loudness (YouTube −14 LUFS, aim ≈ −15) through a −1 dB limiter, then check on several devices. Meters set levels; ears finish the mix.

**Rules**
1. Don't set audio levels by feel ("turn the music down a bit, the dialogue up a bit"). There are guidelines to follow. [00:00]
2. The guideline numbers are the same in every editor (Resolve, Premiere, Final Cut, CapCut, Pro Tools). Match the meter targets in whatever tool you use. [00:31, 03:30, 31:31–32:01]
3. **Step 1, organise:** put dialogue on separate tracks by **microphone**, by **speaker** and by **location**, so each type can be worked on separately. [01:30–02:00, 27:30]
4. Give music its own track or tracks, and keep SFX on separate tracks below it so they can be worked on individually and blended later. [02:00]
5. **Order of work:** organise → set clip levels → edit or repair (noise reduction, EQ, compression/dynamics, de-esser, effects) → mix (blend with faders) → master (loudness for the platform) → test on several devices. [02:31, 17:01, 27:30–30:30]
6. Don't skip level-setting and plan to "fix it at the end" in mastering. Good starting levels are what make the master sound right on a phone, a computer and a TV. [03:00, 28:31]
7. **Hierarchy: dialogue is the most important audio**, music supports the dialogue, and SFX support the story by selling what is on screen. [03:30–04:30]
8. Where music and dialogue overlap, the **music is quieter than the dialogue** and must not compete with it. [04:00, 10:01]
9. **Dialogue target: about −10 dB on the meters.** [04:30, 09:01, 27:30]
10. **Use the meters, not just your ears, to set levels.** Your monitoring volume fools you. Ears matter more once you mix. [04:30–05:00, 22:00–22:30, 31:00–31:31]
11. Worked example: dialogue reading about −15 dB is about 5 dB low, so raise its gain about 5 dB. It needn't be exact; small swings over and under −10 are fine, and a compressor evens them out later. [05:31–06:01, 06:31]
12. **Normalise shortcut:** normalise mode "sample peak program", **target −9 dB**, which usually lands dialogue near −10 dB on the meters. (In his demo it raised a clip by 2.2 dB.) [07:00–07:31]
13. Match clips that share a mic, location and recording to each other (he raised a second clip to match the first). [07:31–08:00]
14. **Don't set dialogue at −2 dB**, the common YouTube advice. With no headroom, the later mixing and processing push it into clipping, or the platform turns it down. [08:00–09:01]
15. −10 dB dialogue leaves headroom to process, blend and then master. [09:01, 10:01, 27:30]
16. Level every dialogue clip, whatever its mic or track. When batch-normalising, use **relative** mode (all selected clips together), not **independent**, so the clips stay consistent with each other. [09:30–10:01]
17. **Music with no dialogue: about −10 dB** (the same as dialogue), a little louder or quieter to taste. [10:30, 13:30, 27:30]
18. **Music under dialogue: −20 to −30 dB** usually. It "may need to be a little bit louder", **−15 to −20 dB**, depending on the track. In any case it should be "a decent amount quieter" than the dialogue. [10:30–11:01, 13:01, 28:02]
19. Imported music usually comes in much louder than levelled dialogue. Always set its level; never leave it at its import level. [11:01–11:31]
20. In the demo, music at −20 dB under dialogue "might even sound a little quiet". Even out the track's own quiet and loud passages with **keyframes** (or other effects) so the bed stays consistent. [12:01–13:01]
21. With no dialogue, the music should feel louder and "surround the viewer". [13:30]
22. **In the mix, the music ebbs and flows:** it swells when no one is talking and becomes more subdued under speech. [19:01]
23. **SFX levels range from about −2 dB to −30 dB**, depending on the sound (a loud thunder crack or boom vs a quiet rumble underneath). A wide range is fine as long as nothing clips. [16:00, 28:02]
24. Example SFX clip levels from his mix: −3.7, −8.3, −6.5 and −10 dB. Set SFX per scene according to the dialogue and music around them. [15:03]
25. Keep SFX from competing with the dialogue and from running hot. Headroom is needed for mastering, and no SFX may clip. [15:03, 16:30]
26. If each SFX gets its own track, its level can be set with the faders during the mix. Otherwise SFX levelling is partly mixing already. [15:32, 28:02]
27. **Set clip levels with clip gain (inspector or clip volume). Mix with the track faders.** [17:31–18:01]
28. **A bad mix can't be saved by mastering.** Mastering only makes it louder "and a little bit worse". [17:31]
29. Mixing is the "meat and potatoes": blend everything into one cohesive whole where nothing competes. Get the mix right before mastering. [19:01–19:31, 29:00]
30. **Master sweetening EQ** on the main bus: a small boost from about **4 kHz up** and around **100–200 Hz** ("150, 200, 100"), **less than 5 dB**. It can be barely noticeable, and it is optional. [20:00–21:01, 29:31]
31. Sweetening only works if the problems were already fixed in the tracks. Otherwise it accentuates them. [20:30]
32. **Loudness (LUFS) is a measure of the whole mix's perceived loudness, not of a clip or track.** Measure it at the end, over the whole timeline. [21:01–21:31, 30:01]
33. **YouTube target: −14 LUFS integrated, "close to but not exceeding" it.** For Netflix or broadcast he thinks it is −23 (he is unsure). [21:01, 23:01]
34. His pre-master mix measured **−21.8 LUFS integrated**, which means there is room to raise the whole mix. [23:01]
35. To raise it, either push the master fader (watching for peaks) or, his preferred way, use a **limiter with its ceiling at −1 dB** and raise the limiter's **input gain**. [23:30–24:32]
36. If the integrated reading overshoots or the meters show clipping, back the input gain off. He settled on a **+3 dB** input boost. [25:03]
37. Integrated loudness is a running average. A short loud stretch is fine if the whole stays under target. Only a mix that sits consistently above −14 LUFS gets turned down by YouTube. (He says "compressed" and "clipped"; see B.7 for why that wording is inaccurate.) [25:30–26:32]
38. **Keep a limiter or compressor on the master as a safety net** for the occasional stray peak (often an SFX), even when the levels are set well. [26:32–27:01]
39. **Aim about 1 LU below the platform target: about −15 LUFS for YouTube**, so you don't get too close to clipping or to being turned down. [29:31]
40. **Final step: test on studio monitors, headphones, a phone and a home theater.** Either pick the device most viewers will use or balance across several. Expect tweaks, e.g. a mix that sounds muddy on the phone. [30:30–31:00]
41. Trust the process and the meters. Levels can be set "without even listening". [31:00–31:31]

**Count: 41 rules.**

---

### 5.6 How To Mix Dialogue with Music for Film and Video
- **Source:** 5.6 · "How To Mix Dialogue with Music for Film and Video" · Curtis Judd · https://www.youtube.com/watch?v=fvUn8l30VLc · 310 s (5:10) · 971 words · search match (1.0).
- **Thesis:** When music competes with dialogue, turning the music down helps only partly. Scooping an EQ notch out of the music where the voice's energy lives (about 1–1.5 kHz) keeps the music present and makes the dialogue effortless to hear.

**Rules**
1. Music under dialogue often competes with it. Both are needed: music for emotion, dialogue for the story. [00:00]
2. The technique is **EQ notching/scooping**: scoop a small region out of the middle of the music to make room for dialogue. [00:00]
3. Test: if you must "push" to understand the words, the music is competing. [01:39]
4. Don't rely on subtitles to rescue intelligibility; the dialogue itself should be clearly audible. [01:39–02:00]
5. The obvious first move is to pull back the music fader. **About −4.5 dB** ("4 and a half dB") was "definitely better" but still left "a little bit of competition". [02:00–02:30]
6. The scoop is a standard music-production engineering technique, not a hack. [02:30]
7. Insert an EQ on the **music track** (any EQ plugin works). [03:00]
8. **Most of dialogue's energy lives around 1–1.5 kHz.** [03:32]
9. Set a bell at **about 1.5 kHz, cut about −4 dB**, then adjust to taste. [03:32]
10. Side benefit: the scoop also unmasks quiet background layers (gentle crickets on the Foley track became audible again). [04:01]
11. Success criterion: dialogue "nice and clear", music "still very present", and you hear the dialogue **without straining**. [04:30]
12. Net recipe as demonstrated: fader −4.5 dB **plus** a 1.5 kHz notch of −4 dB, about −8.5 dB on the music in the voice-presence region and −4.5 dB elsewhere. (Sum is mine; both steps are the video's.) [02:00, 03:32]

**Count: 12 rules.**

---

### 5.7 A Quiet Place: How to Write Sound into a Screenplay (for "Making Movies: Sound Design")
- **Source:** 5.7 · "A Quiet Place — How to Write Sound into a Screenplay" · Lessons from the Screenplay · https://www.youtube.com/watch?v=T-s81-Wl2v0 · 729 s (12:09) · 2,083 words · search match (0.64), on topic. Audible sponsor segment [10:33–11:32] ignored.
- **Thesis:** Plan sound at the script stage. Use sonic point-of-view, hard cuts in perspective and above all **dynamics**: build up from quiet, peak briefly, reset. Contrast is what makes anything feel loud or tense; "the loudest sound can only come from a quiet place."

**Rules**
1. Make sound part of the story, not an afterthought. Here "the sound design is a main character". [00:00–00:30]
2. Most screenwriting guidance ignores sound; don't. Write sonic intent into the script or plan. [01:02–01:31, 03:02]
3. Annotate sound and silence visibly in the script (underlines, caps, font size, word placement) to show silence, tension and pacing. [02:03–03:02]
4. When the script itself can't use dialogue as a crutch, sound and silence carry the story. [01:31–02:03]
5. Screenwriters should think about "what is happening sonically in the world". [03:02]
6. Audiences experience film with two senses; hearing is "half of the experience". [03:31]
7. We don't notice sound until it is gone, and that unconscious effect is its power. [03:31]
8. Murch: images come in through the front door, **sound through the back door**, so sound can manipulate emotion more stealthily. [03:31–04:00]
9. Use sound to reach the "reptilian" senses and steer emotion. [04:00]
10. Use sound to make the audience experience what a character experiences, viscerally. This builds empathy. [04:00–04:32]
11. Write and design **sonic point of view**: hear the scene as one character hears it (hearing-aid static, faint baby crying, breathing). [04:32–05:31]
12. Several POVs can exist (family members, the creature hearing a clock tick). [05:31]
13. Put the audience in a specific character's sonic perspective from the opening sequence. [05:31–06:00]
14. Make perspective shifts **hard cuts**, not crossfades ("really nice, hard cuts"), so the contrast is felt: normal atmosphere, then into her head with a low tone underneath. [06:00–06:34]
15. Stark shifts are what make the perspective change powerful. [06:00–06:34]
16. Design for **dynamics** in both sound and plot. [06:34–07:02]
17. Don't let silence (or any single state) run the whole film. Pace where sound-design moments go. [07:02]
18. A flat amplitude envelope, with little difference between top and bottom, flattens the experience, and **viewers disengage**. [07:02–07:30]
19. If everything is loud start to finish it's annoying, and no loud moment can land. [07:30]
20. Begin sequences quiet and **build volume over time**, mirroring rising tension. [07:30–08:00]
21. Peak at the climax but **don't stay at 100% long**. Drop low again to reset the tension. [08:00–08:30]
22. The rise-peak-reset arc works over a whole sequence **and within a few moments** of a scene. [08:30]
23. Counterpoint: an intense performance with **complete silence** under it can be the most terrifying beat. [08:30–09:04]
24. Silence is often the best way to create suspense. [09:04]
25. After a long stretch of tension, give the audience catharsis (release) before more. [09:04–09:32]
26. Build sound into the DNA of the script and you get a better film "every time". [09:32]
27. Sound is most effective used dynamically, to create moments of contrast. [10:02]
28. "The loudest sound can only come from a quiet place." [10:02]

**Count: 28 rules.**

---

### 5.8 "Sound Effects: How to Use Them Without Being Cheesy", resolved as "How Dialog Should Sound! (Basic Film Audio Design)"
- **Source:** 5.8 · "How Dialog Should Sound! (Basic Film Audio Design)" · This Guy Edits (guest Mark Edward Lewis, CinemaSound) · https://www.youtube.com/watch?v=Xy31jShyKEY · 744 s (12:24) · 2,369 words · search match (0.62). **Weak title match:** it is about dialogue EQ, not SFX. On topic for the mixing half of the module. Epidemic/challenge promo [09:00–12:03] ignored.
- **Thesis:** Give dialogue a "basic grade" with EQ before mixing. On a bus, sweep a narrow boosted bell from about 100 Hz to 5 kHz, find the resonances that "sing", and cut them 10–15 dB, leaving the fundamental alone. Then the dialogue can sit louder and the music and SFX can balance in. EQ is the scalpel; the fader is the blunt tool.

**Rules**
1. Poor audio throws viewers (and directors) out of the moment and generates notes that are really audio problems. [00:30–01:00]
2. Shape dialogue by boosting the frequencies that help and removing those that hurt. [01:00–01:30]
3. Do a **basic dialogue grade** (like a primary colour grade) before any "secondary" audio work. [02:00]
4. Raw dialogue usually has frequencies that are "too loud". Pull them out so dialogue can balance with music and SFX. [02:30]
5. Without EQ, the **fader** is your only balancing tool, and it's blunt. **EQ is the surgical knife.** [02:30–03:00]
6. Route all dialogue (every take, every actor) through **one dialogue bus** and EQ the bus. [03:00–03:31]
7. EQ has four controls to understand: filter type, frequency, gain (boost/cut), width (Q). [03:31–04:02]
8. Use **bell (parametric)** bands, not shelves, for this work; they are the most flexible. [04:02]
9. The audible range is 20 Hz to 20 kHz. [04:02]
10. **The voice makes essentially nothing under 100 Hz.** Male voices start around **150 Hz**, female around **200 Hz**. [04:30]
11. **Sweep from about 100 Hz up to about 5,000 Hz** looking for frequencies that "poke out" and "sing" (a whistling, humming resonance). [04:30]
12. Sweep settings: **+20 dB boost, very narrow (Q ≈ 10)**, playing the track. [05:01, 05:31]
13. Start the sweep near the voice's floor (about 150 Hz for this female voice). [05:31]
14. **Leave the first resonance alone: it is the fundamental.** Cutting it alters the voice too much. Work on the second and above. [06:00]
15. When you find a resonance, **cut it about 10–15 dB** and widen the band slightly. [06:30]
16. Move to the next band and repeat (the next was around 272 Hz in this example, then about 300 Hz). [06:30–07:02]
17. With few bands (Fairlight has 4), prioritise the **loudest** resonances. [05:01–05:31, 07:02]
18. If two resonances sit close together, cut about **10 dB** with a wider band to cover both. [07:31–08:01]
19. **No need to go above 5 kHz** for this pass. Above that is mostly sibilance, which is not a resonance problem. [08:01]
20. The goal is a flatter response from the recording. [05:01]
21. The result is subtle on solo but matters in the mix: it lets you **bring the dialogue up louder** and lets the music balance in. [08:35–09:00]
22. Apply the same resonance-sweep method to the **music bus** and the **SFX bus** so all elements "congeal". [09:00]

**Count: 22 rules.**

---

**Rule counts:** 5.1 = 51 · 5.2 = 33 · 5.3 = 26 · 5.4 = 24 · 5.5 = 41 · 5.6 = 12 · 5.7 = 28 · 5.8 = 22. **Total 237 audio rules.**

---

## B. Module synthesis

### B.1 Best practices (de-duplicated, ordered by impact)

| # | Rule | Sources | Scope |
|---|---|---|---|
| 1 | **The voice is the priority signal.** It must be clear without straining, never masked by music or SFX, and never rescued by captions alone. | 5.2 [00:31], 5.6 [01:39, 04:30], 5.1 [14:01] | UNIVERSAL |
| 2 | **Make room for the voice with EQ, not just the fader.** Notch or scoop the music in the voice-presence band (about 1–1.5 kHz, −4 dB to taste), on top of a broadband pull (−4.5 dB). A dynamic EQ or de-esser keyed to the music works too. | 5.6 [02:00, 03:32], 5.4 [01:30], 5.2 [08:01], 5.8 [03:00] | UNIVERSAL |
| 3 | **Relative level hierarchy:** dialogue loudest (about −10 to −12 dB on the meter), music under dialogue −20 dB (range −15 to −30 dB by track), SFX −2 to −30 dB by type. Nothing clips. Imported music is always re-levelled, never left at its import level. | 5.1 [14:01], 5.2 [08:31], 5.5 [04:30, 10:30–11:31, 16:00] | UNIVERSAL (numbers are peak-meter guides, not LU) |
| 3b | **The music bed ebbs and flows:** it tucks under speech and swells when nobody is talking. Music with no dialogue sits at about the dialogue's own level (both ≈ −10 dB), so it "surrounds the viewer". Even out the track's own loud and quiet passages with keyframes. | 5.5 [10:30, 12:01–13:30, 19:01] | UNIVERSAL |
| 4 | **Basic dialogue grade on a bus first:** high-pass below the voice (nothing under 100 Hz), sweep 100 Hz–5 kHz with +20 dB at Q≈10, keep the fundamental, cut resonances 10–15 dB; skip above 5 kHz (sibilance is de-esser territory). | 5.8 [03:31–08:01], 5.4 [01:30] | UNIVERSAL |
| 5 | **Dynamics and contrast:** build from quiet, peak briefly, reset. Silence or a dip before a key hit makes it land. A flat-loud mix makes viewers disengage. | 5.7 [07:02–08:30, 10:02], 5.2 [03:00–03:30], 5.3 [04:36] | UNIVERSAL |
| 6 | **Accent economy:** only key moments get full-intensity accents. Secondary moments get a subtler single layer. "If every moment is special none are." | 5.1 [12:00–13:32] | UNIVERSAL |
| 7 | **Sync SFX transients to the visual event:** waveform visible, apex on the frame, markers; for transitions, reverse cymbal/riser into the cut and drop/boom starting exactly on the cut. | 5.1 [06:01–06:31, 11:30, 13:32], 5.2 [03:00] | UNIVERSAL |
| 8 | **Commit to one SFX palette that fits the genre and look**, and stay consistent through the piece. | 5.1 [11:01], 5.4 [02:30–03:30] | UNIVERSAL |
| 9 | **Cut music to the edit:** align cue hits/dips to picture; avoid tone changes; join similar sections; enter with a reversed beat/tail riser; exit by cutting before the next beat with a reverb tail on the last beat; sweeten joins with risers/suckbacks/impacts. | 5.1 [03:30–04:30], 5.4 [04:31–07:01] | UNIVERSAL |
| 10 | **No repeated identical SFX:** cut variants from a longer recording and use each once. | 5.1 [03:01, 06:01] | UNIVERSAL |
| 11 | **Layer for weight across frequencies:** big moves get low + mid + high layers. Integrate stylised layers by matching tone and frequency to the natural sound. | 5.4 [00:30–01:01], 5.1 [10:34] | UNIVERSAL |
| 12 | **Order of work:** organise tracks (dialogue split by mic, speaker and location; music and SFX on their own tracks), voice, then music (temp if needed), then ambience/Foley, then creative SFX; set clip levels, then repair/process (NR, EQ, compression, de-ess), then mix with faders, then master to the platform loudness, then multi-device check. | 5.1 [00:30–01:00, 15:30], 5.2 [00:31–02:30, 08:31–09:31], 5.5 [01:30–02:31, 17:01, 27:30–30:30] | UNIVERSAL |
| 13 | **Normalise the final mix to the platform loudness standard** so the platform doesn't apply its own compression or turn-down. Lower the master if overall hot. Measure integrated loudness over the whole finished mix, never per clip. Get close to the target but never exceed it (YouTube −14 LUFS; aim about 1 LU under, ≈ −15). Raise the level through a limiter with a −1 dB ceiling, which stays on as a safety net for stray peaks. | 5.2 [09:02], 5.5 [21:01–21:31, 23:01–27:01, 29:31] | UNIVERSAL |
| 14 | **No dead air:** every location has a bed (room tone or ambience) at a background level. Titles never play in silence (chimes on text reveal, drone into the cue). | 5.1 [00:30, 02:36, 05:07–05:31, 08:30], 5.2 [01:33] | CONTEXT: when there is no continuous music bed; intentional silence (rule 5) excepted |
| 15 | **Hear what you see:** every visible action and every camera move gets a sound, Foley or creative. | 5.1 [00:30, 01:00, 06:31, 09:01] | CONTEXT: stylised/motion-graphic pieces; not every micro-action in a talking head |
| 16 | **Use sound for the unseen:** feelings, stakes, thoughts (a reverberating hit makes an ordinary action consequential; non-literal or "emotional realism" substitution). | 5.1 [08:00, 09:31], 5.2 [03:30], 5.4 [03:30–04:31], 5.7 [04:00] | CONTEXT |
| 17 | **Place sounds in space:** reverb matched to room size (on a bus); more reverb means more distance; subtle panning to the on-screen position. | 5.1 [07:30–08:00], 5.2 [05:30–07:31] | CONTEXT |
| 18 | **Hide cuts with audio:** J-cuts (incoming audio fades in before the picture) and L-cuts (outgoing audio lingers). Carry a sound across the cut and let it change role (trans-diegetic). | 5.2 [06:01–06:30], 5.3 [11:08] | UNIVERSAL |
| 19 | **Whooshes for movement and transitions** add intent and levity. Risers build to reveals and to energy or environment changes. | 5.1 [09:01], 5.2 [02:30–03:00] | UNIVERSAL |
| 20 | **Bus architecture:** dialogue bus (EQ), Foley/SFX bus (room reverb, EQ), music bus (EQ), so one process treats a whole stem. | 5.1 [07:30], 5.8 [03:00, 09:00] | UNIVERSAL |
| 21 | **Use stems** to mute an instrument that fights the voice. | 5.2 [05:00] | CONTEXT: when stems are licensed |
| 22 | **Filters for perspective:** HPF/LPF for phone, muffled or underwater sound. Hard-cut perspective shifts for POV. | 5.2 [08:01], 5.7 [06:00–06:34], 5.3 [05:01] | CONTEXT |
| 23 | **Plan sound in the script/brief**, not as an afterthought. | 5.7 [01:02–03:02, 09:32], 5.3 [16:34] | UNIVERSAL |
| 24 | **Iterate:** first pass, critique against a checklist, second pass. | 5.1 [00:00, 02:36, 10:01] | UNIVERSAL |
| 25 | **Narrator illusion:** intrusive or recognisable narration breaks immersion. Use it on purpose only. | 5.3 [07:30] | CONTEXT (film) |
| 26 | Sometimes one or two layers are enough. Don't stack for its own sake. | 5.2 [10:01] | UNIVERSAL |
| 27 | **Meters set levels; ears finish the mix.** Don't trust monitoring volume for levels or loudness. | 5.5 [04:30–05:00, 22:00–22:30, 31:00–31:31] | UNIVERSAL |
| 28 | **Start with headroom, not hot.** Dialogue ≈ −10 dB (normalise sample-peak to −9 dB), never −2 dB. Hot starting levels clip later or get turned down by the platform. | 5.5 [04:30, 07:00, 08:00–09:01] | UNIVERSAL |
| 29 | **Mastering can't fix a bad mix.** Fix problems in the tracks first. Master sweetening is small: a shelf from ≈ 4 kHz up and ≈ 100–200 Hz, under 5 dB, optional. | 5.5 [17:31, 20:00–21:01] | UNIVERSAL |
| 30 | **Clip gain sets levels; track faders mix.** | 5.5 [17:31–18:01] | UNIVERSAL |
| 31 | **Consistent dialogue across clips:** level every dialogue clip; match clips from the same mic and location; batch-normalise in relative (not independent) mode. Small swings are fine and a compressor evens them out. | 5.5 [06:01, 07:31–08:00, 09:30–10:01] | UNIVERSAL |

### B.2 Short-form ad translation (9:16, 30–60 s talking head, Meta Reels, phone speakers)

- **Rule 1 (voice priority):** transfers fully and matters more here. The ad's message is the spoken offer, and phone speakers roll off below about 150–200 Hz, so the music's mids are what fight the voice. Many viewers start muted (5.4 [00:01]); burned-in captions (house spec) cover them, but captions must not be the intelligibility crutch (5.6 [01:39]).
- **Rule 2 (EQ carve):** transfers directly and is the backbone of the house frequency-split duck (voice band −8 dB, lows/highs −3 dB). 5.6's demonstrated recipe (−4.5 dB broadband, plus −4 dB at 1.5 kHz, giving about −8.5 dB in-band) has nearly the **same shape** as the house duck (−3 broadband, −8 in-band). Keep the voice-band notch centred around 1–1.5 kHz (5.6) and covering the 150 Hz–5 kHz speech range (5.8). Ducking is dynamic, applied only while the voice is present; restore the bed in gaps and on cutaway moments without speech.
- **Rule 3 (level hierarchy):** the ordering transfers. The **numbers do not transfer as-is**: they are peak-meter levels for film and documentary scenes, and the house deliberately runs a bigger, more present bed for an ad (see B.7). 5.5's own numbers (dialogue −10, music under dialogue −20, "may need to be a little louder", −15 to −20) put its typical bed at roughly 0–7 LU under the voice by my estimate. That is **as loud as or louder than** the house −7 LU, so 5.5 gives no reason to turn the bed down.
- **Rule 3b (ebb and flow):** transfers directly and matches the house dynamic duck. In practice: pre-voice intro, cutaways with no speech, and the outro tail get the bed up near voice level; under speech it tucks. Gaps under 0.25 s (house pause gate) are too short for a full swell, so the swell only shows on spans of about 1 s or more without speech.
- **Rule 4 (dialogue grade):** transfers. It is already in `voice_chain.sh` (denoise, EQ, de-ess, compression, expander). Add the resonance-sweep logic as an automated spectral check (QC).
- **Rule 5 (dynamics):** transfers in miniature. A 30–60 s ad has room for perhaps 1–3 arcs: hook, problem, offer, CTA. Use dips (pull the bed or a beat of near-silence before the offer/price reveal) to make the payoff land, and don't hold the bed at full energy for 60 s. Platform loudness normalisation (−14 LUFS) means short-term contrast, not absolute level, is what the viewer feels. Long silences do **not** transfer: the house rule bans speech gaps over 0.25 s, and dead air on Reels invites a swipe.
- **Rule 6 (accent economy):** transfers strongly. Earshot's salient-hit density already flags density. In a talking head, the voice already provides about 2 salient events/s (EDIT-STANDARD §5), so SFX accents compete with syllables. Reserve the big hit (riser into boom/drop) for one or two moments, for example the first cutaway and the offer/CTA reveal.
- **Rule 7 (transient sync):** transfers fully and is measurable. Every whoosh, hit or click goes on the cut or animation frame from the EDL (house: "real sound effects on the frame").
- **Rule 8 (one palette):** transfers. Match the SFX palette to the series look: a UI-card look (e.g. preset `profitcast-dark`: black, green grid, accent UI cards) suggests a clean UI/digital palette (soft whooshes, UI ticks, light glitch if the style uses glitch transitions), not gritty bass hits or cinematic horror booms (5.4 [03:30]).
- **Rule 9 (music edit):** transfers fully; this is the 3-minute-song-into-30-s problem (5.4 [04:31]). Start the bed with a reversed riser into the first downbeat at the hook. End on a reverb-tailed final beat or an impact aligned with the sign-off (the brand name), never a hard stop or fade-out mid-phrase.
- **Rule 10 (no repeats):** transfers. UI ticks on list items appearing line by line are exactly the "same keystroke every time" trap. Use 3+ variants or pitch/gain variation.
- **Rule 11 (layering):** transfers for the one or two hero transitions (zoom-blur whip into a cutaway: low thump + mid whoosh + high air).
- **Rule 12 (order):** transfers. The voice chain runs first; music and SFX are then built around the cleaned voice.
- **Rule 13 (normalise):** transfers. Meta and Instagram normalise playback, so deliver at −14 LUFS integrated, ≤ −1 dBTP (house spec), and never above −14 (5.5). A 30–60 s ad has no long quiet stretches to average out a hot passage, so 5.5's "short overshoot is fine" leaves little room here: measure the full file.
- **Rules 27–31 (meters, headroom, mastering, clip gain vs faders, dialogue consistency):** transfer as pipeline rules. The code pipeline already "listens" by meter (ebur128, librosa). Gain-stage the stems in `mix_v2.py` with headroom before the master limiter. Keep the master EQ sweetening to small shelves. `voice_chain.sh` compression plays the role of 5.5's "compressor evens it out". The multi-device check maps to a phone-speaker listen plus a headphone listen (and earshot).
- **Rule 14 (no dead air / ambience):** **partly transfers.** The house denoises the voice to a podcast-dry sound and runs a continuous music bed, so the bed is the "room". Don't add a location ambience under the A-roll; it would undo the denoise and fail the voice-floor gate (which applies to the voice **stem**, not the mix). Do apply "titles never in silence": cutaways and the opening card get sound.
- **Rule 15 (hear what you see):** **context.** Apply it to motion graphics (cards landing, counters counting up, checkmarks, the punch-in) but not to the speaker's micro-actions.
- **Rule 16 (sound for the unseen / non-literal):** context. Light use: a soft hit under a pain-point line, a "success" chime on a ranking or result. Avoid emotional-realism substitution; it confuses a 30 s commercial message.
- **Rule 17 (reverb/panning):** **mostly does not transfer.** Reels are mostly heard on mono-ish phone speakers, and a dry, close voice is the house sound ("no audible room tail" gate). Use reverb only on music exits (5.4) and on SFX tails. Use panning at most subtly on stereo whooshes; never pan the voice.
- **Rule 18 (J/L cuts):** transfers. Start the whoosh or riser slightly before the visual cut into a cutaway (J-style). Let a card's landing sound ring briefly into the next shot (L-style). The voice stays continuous across cutaways (house spec), which is itself an L/J bridge.
- **Rule 19 (whoosh/riser):** transfers. These are the house's zoom-blur whip and glitch transitions.
- **Rule 20 (buses):** transfers as stems: voice / music / SFX stems rendered separately by `mix_v2.py` so each can be measured (QC).
- **Rule 21 (stems):** transfers when the track has stems. Muting a lead vocal line or a lead synth in the 1–3 kHz region is cleaner than heavy EQ.
- **Rule 22 (filters/POV):** context. An LPF "muffled" effect can sell a phone-screen cutaway or a before/after. Rarely needed.
- **Rule 23 (plan in brief):** transfers. Mark SFX/music moments in the script or EDL (hook hit, offer reveal, CTA).
- **Rule 24 (iterate):** transfers. Use the earshot critique plus a first-pass/second-pass checklist (B.3).
- **Rule 25 (narrator):** does not transfer. In a selfie ad the speaker is on-camera and diegetic; no narration-illusion issue.
- **Does NOT transfer at all:** film-scale Foley for every prop, room reverb on Foley to match a set, script-typography for sound (5.7 [02:03–03:02]), trans-diegetic storytelling devices (5.3 [09:30–15:36]), and long silent suspense passages (5.7 [08:30–09:04]). These are feature-film tools that conflict with the 0.25 s gap rule and 30–60 s attention economics.

### B.3 Checklist

**Pre-edit**
- [ ] Voice stem cleaned by `voice_chain.sh` (denoise, EQ incl. HPF ~80–100 Hz, de-ess, compression, expander) and passed the words gate? [5.8, house]
- [ ] Voice, music and SFX kept as separate stems (and voice segments from different mics or locations kept apart until levelled)? [5.5 [01:30–02:00]]
- [ ] Music chosen for the ad's energy and genre (not a generic "safe" track)? [5.2 [01:00], 5.4 [02:30]]
- [ ] Stems available? If yes, is any instrument fighting the voice muted? [5.2 [05:00]]
- [ ] One SFX palette chosen to match the series look (no mixing of gritty/cinematic and clean/UI)? [5.4 [03:00], 5.1 [11:01]]
- [ ] Key accent moments marked in the EDL: hook, first cutaway, offer/price, CTA (≤ 2 full-intensity)? [5.1 [13:00], 5.7]
- [ ] At least 3 variants prepared for any SFX that repeats (list ticks, card pops)? [5.1 [06:01]]

**During edit**
- [ ] Music cut so its entry (reversed riser), hits and exit (reverb tail or impact) land on picture events and beat lines? [5.1 [04:01–04:30], 5.4 [05:01–07:01]]
- [ ] No mood or tone change inside the used section of the cue? [5.1 [02:36]]
- [ ] Every SFX transient aligned to its cut or animation frame? [5.1 [06:01]]
- [ ] Transition SFX lead into the cut (riser/whoosh starts before, drop/thump on the cut)? [5.1 [11:30], 5.2 [06:01]]
- [ ] No two consecutive uses of the identical SFX sample? [5.1 [03:01]]
- [ ] Hero transitions layered across lows, mids and highs; minor ones single-layer? [5.4 [01:01], 5.1 [13:00]]
- [ ] Opening card and every cutaway have sound (no silent graphics)? [5.1 [08:30]]
- [ ] At least one deliberate dip or contrast moment before the key payoff? [5.7 [07:30], 5.2 [03:00]]
- [ ] Music ducked dynamically with a voice-band notch (about 1–1.5 kHz centre, covering speech) deeper than the broadband duck? [5.6, 5.4, house]
- [ ] Voice not panned or reverbed; SFX reverb used only for tails or exits? [house, 5.2]
- [ ] Music re-levelled from its import level, with its own loud and quiet passages evened out (keyframes or gain automation)? [5.5 [11:01–13:01]]
- [ ] Bed swells up toward voice level in every no-speech span of about 1 s or more (intro, silent cutaways, outro)? [5.5 [13:30, 19:01]]
- [ ] Dialogue level consistent sentence to sentence (no segment about 5 dB off the rest)? [5.5 [05:31–06:01, 07:31]]
- [ ] Stems gain-staged with headroom (voice ≈ −10 dBFS peaks, nothing near 0 dBFS) before the master limiter? [5.5 [08:00–09:01]]

**Pre-delivery**
- [ ] Integrated loudness between −15.0 and −14.0 LUFS (never above −14), true peak ≤ −1 dBTP? [house, 5.2 [09:02], 5.5 [23:01, 29:31]]
- [ ] Master limiter on as a safety net, with any master EQ sweetening under 5 dB? [5.5 [20:00, 26:32–27:01]]
- [ ] Zero clipped samples on any stem or the master? [5.1 [14:01], 5.2 [08:31]]
- [ ] Music-to-voice loudness offset within the house target (about −7 LU; see B.5)? [house]
- [ ] Words gate passes on the **final mix** (music doesn't mask words)? [5.6 [04:30], house]
- [ ] Music ends cleanly (reverb tail or hit), with no abrupt cut or truncated beat? [5.4 [04:31]]
- [ ] Listened on a phone speaker and on headphones (plus monitors or a TV if available), with fixes made for any device where it turns muddy? [5.2 [09:31], 5.5 [30:30–31:00]]
- [ ] earshot critique run on the final mix, with salient-hit flags checked against the voice stem? [house]

### B.4 QA (human-judgement review)

| Question | Good looks like | Source |
|---|---|---|
| On a phone speaker at mid volume, can I follow every word without effort and without reading captions? | Zero "push to understand" moments. The music still feels full. | 5.6 [01:39, 04:30] |
| Does the music feel big enough for an ad, yet never sit on top of a word? | The bed swells in gaps and cutaways and tucks under syllables. The duck isn't audible as pumping. | 5.6, 5.4 [01:30], 5.5 [19:01], house |
| Does the bed sound "a little quiet" under the voice? | If yes, raise it (and deepen the voice-band carve if words suffer). 5.5's own −20 dB demo bed "might even sound a little quiet". | 5.5 [12:01] |
| When nobody is talking (intro, silent cutaway, outro), does the music fill the space? | It comes up to about the voice's level and "surrounds" the viewer, then tucks back under the next word. | 5.5 [13:30, 19:01] |
| Does the voice level jump between sentences or takes? | Even, as if one recording. No sentence noticeably quieter or louder. | 5.5 [07:31–08:00, 09:30–10:01] |
| Does it hold up on a phone, on headphones and on a bigger speaker? | Clear on all of them. Not muddy on the phone, not harsh on headphones. | 5.5 [30:30–31:00], 5.2 [09:31] |
| Does the music's mood match the ad's arc start to finish? | No tonal swerve (e.g. from upbeat to dramatic) mid-ad. | 5.1 [02:36] |
| Do the music's entry and exit feel designed? | It eases in on a riser and resolves on a tail or hit, not "slamming the brakes". | 5.4 [04:31–07:01] |
| Does each SFX feel like part of one family that matches the visual style? | Same texture and character throughout. Nothing cheap or off-genre. | 5.4 [03:00–03:30], 5.1 [11:01] |
| Is anything over-accented? | Big hits only on the hook and offer/CTA. Soft moments get subtle or no sound. | 5.1 [12:00–13:32] |
| Are there sonic dead spots (silent graphics, a dead tail)? | Every cutaway and card has sound. The ending has a designed tail. | 5.1 [02:36, 08:30] |
| Does anything repeat audibly (the same tick, the same whoosh)? | Variations feel natural. | 5.1 [03:01] |
| Is there contrast, a moment the energy drops so the next beat lands? | One clear dip before the payoff. The mix doesn't feel uniformly loud. | 5.7 [07:02–08:30], 5.2 [03:00] |
| Does the voice sound like a close podcast mic, with no boxy or honky resonance and no harsh "s"? | Even tone. No ringing frequency. Sibilance controlled. | 5.8, house |
| Do transitions feel motivated by sound (whoosh into whip, thump on landing)? | Sound and picture move together, with the sound slightly ahead into the cut. | 5.2 [02:30–03:00, 06:01] |

### B.5 QC (automatable gates)

Toolchain: `ffmpeg -af ebur128` (integrated/momentary/short-term loudness, true peak with `peak=true`), librosa (STFT, onset detection, beat tracking, spectral analysis), soundfile (sample access), earshot CLI (critique, salient-hit density, masking listening). Stems come from `mix_v2.py` (voice, music, SFX, master). Speech regions come from whisper.cpp word timings.

| # | Gate | Metric | Pass threshold | How to measure |
|---|---|---|---|---|
| Q1 | Integrated loudness | Master integrated LUFS | **−15.0 ≤ I ≤ −14.0 LUFS** (house target −14; 5.5 [23:01, 29:31]: "close to but not exceeding" −14, aim about 1 LU under). Previously −14 ±0.5, which allowed −13.5 | `ffmpeg -i master.wav -af ebur128=peak=true -f null -` and read `I:` |
| Q2 | True peak | Master TP | ≤ −1 dBTP (house; industry norm). 5.5 [24:01] sets its limiter ceiling at −1 dB (sample peak); the house true-peak gate is the stricter of the two, so keep it | Same ebur128 run, read `Peak:` |
| Q3 | No clipping | Count of samples with \|x\| ≥ 0.999 FS on each stem and master | 0 | soundfile read and numpy count. Videos: "nothing peaks" [5.1 14:01], clipping [5.2 08:31], no SFX clipping [5.5 16:00–16:30] |
| Q4 | Music-under-voice offset | Integrated LUFS of the music stem minus voice stem, **computed only over speech regions** (gated on whisper word spans) | House target ≈ −7 LU. **Fail if quieter than −9 LU** (thinner than the user-approved bed). **Above −4 LU: allowed only if Q6 words gate passes, plus review** (5.5's peak figures put its typical bed at roughly 0–7 LU under the voice, my estimate, see B.7). Band edges are proposals | Concatenate speech-region slices of each stem and run ebur128 `I:` on each. Also report the full-length offset. |
| Q4b | Music-under-voice peak gap (5.5's own units) | Voice-stem peak level minus music-stem peak level in speech regions (95th percentile of 400 ms-window sample peaks, dBFS) | **Report; flag < 5 dB** (5.5's loudest allowance: music −15 vs dialogue −10). Typical per 5.5 ≈ 10 dB (−20 vs −10); its quiet end is 20 dB (−30). A gap above 20 dB is quieter than anything 5.5 suggests (flag as too quiet) | soundfile + numpy windowed peaks on the voice and music stems, masked by whisper word spans |
| Q5 | Voice-band notch depth | Music-stem energy in the 1–2 kHz band during speech vs the same band in non-speech gaps (after mix automation) | Reduction ≥ 8 dB in-band (house voice-band duck); broadband reduction ≈ 3 dB. In-band minus broadband ≥ 4 dB (5.6's notch = −4 dB relative) | librosa STFT on the music stem, band-sum 1000–2000 Hz and 20 Hz–20 kHz, mean dB in speech vs gap frames |
| Q6 | Masking / intelligibility | Words gate on the **final mix** (re-transcribe the mix, not the voice stem) | No missing or misheard words vs script (house words gate) | `gate_words.py final raw` on the mixed master |
| Q7 | SFX sync | \|SFX onset − event frame time\| for each SFX in the mix JSON | ≤ 1 video frame (≈33 ms at 30 fps; house "on the frame") | librosa `onset_detect` (backtrack) on the SFX stem within ±150 ms of each EDL event; compare to the frame timestamp. For pre-cut risers, check the **end/peak** against the cut. |
| Q8 | Transition lead | Riser/whoosh energy peak time vs cut time | Peak at or within 1 frame of the cut; onset before the cut (5.1 [11:30], 5.2 [06:01]) | RMS envelope argmax of each transition SFX region |
| Q9 | SFX repetition | Consecutive uses of the same SFX file (from mix JSON), or cross-correlation > 0.95 between adjacent SFX events | 0 identical consecutive repeats for repeated actions (5.1 [03:01, 06:01]) | Hash the file paths in the mix JSON; fallback `np.correlate` on normalised clips |
| Q10 | Accent budget | Count of "max-intensity" accents (SFX events whose short-term loudness exceeds the voice's short-term median by ≥ 0 LU, i.e. as loud as the voice) | ≤ 2 per ad (derived from 5.1 [13:00]; house proposal, no number in the videos) | ebur128 short-term (3 s) on the SFX stem vs voice stem at each event |
| Q11 | SFX vs voice level | Peak of each SFX event relative to voice peak | SFX peaks in the −10 to −30 dB range per 5.1 [14:01], widened to **−2 to −30 dBFS** by 5.5 [16:00] for loud hero hits, as a **relative** guide: no SFX peak above the voice peak except the designated hero hits; no SFX peak above −2 dBFS on the SFX stem | Per-event peak dBFS from soundfile slices |
| Q12 | Dynamic contrast | Range of the music stem's short-term loudness across the ad | At least one dip ≥ X LU before the payoff. **No number from the videos**; report the value, human review decides (5.7 [07:02–08:30]) | ebur128 short-term series of the music stem; min in the 2 s before marked payoff vs ad median |
| Q13 | Dead air | Master RMS in any 250 ms window | No window below −50 dBFS except a marked intentional silence (5.1 [00:30, 02:36]; threshold is a proposal) | soundfile + numpy windowed RMS |
| Q14 | Silent graphics | Each cutaway/card start in the EDL has SFX or music energy above the bed within ±100 ms | 100% coverage (5.1 [08:30]) | EDL event list vs onset list from Q7 |
| Q15 | Music exit | Last 500 ms of the music stem: decaying envelope (tail) or a hit aligned to the last word or sign-off | No truncation: final-frame music RMS ≥ 20 dB below its peak in the last 2 s, or a hit at sign-off (5.4 [04:31–06:33]; threshold is a proposal) | librosa RMS on the music stem |
| Q16 | Music edit on beat | Each music edit point vs nearest librosa beat | Within 1 frame (≈33 ms) (5.1 [04:01], 5.4 [05:30]; tolerance is a house proposal) | `librosa.beat.beat_track` on the source track and edit points from the mix JSON |
| Q17 | Voice resonances | Peaks in the voice stem's long-term average spectrum 250–5000 Hz that stand above a 1/3-octave-smoothed curve, excluding the fundamental region (≈80–250 Hz) | Flag any peak ≥ 6 dB above the smoothed curve for review (detection threshold is a proposal; 5.8 cuts found resonances 10–15 dB) | librosa STFT mean, smoothed by median filter; peak picking |
| Q18 | Voice low end | Voice-stem energy below 100 Hz relative to 100–5000 Hz | ≤ −20 dB (5.8 [04:30] "nothing under 100 Hz"; threshold is a proposal) | librosa band energy |
| Q19 | Voice floor | Voice stem between words | ≤ −60 dBFS (house gate) | Existing house gate |
| Q20 | Salient-hit density | earshot salient hit density | Read against the voice-only baseline (~2/s); flag SFX additions > +1/s over baseline (proposal) | `earshot` on master vs voice stem |
| Q21 | Bed swell in no-speech spans | Music-stem short-term loudness in each no-speech span ≥ 1 s (intro, silent cutaways, outro) vs its level under speech; and vs the voice stem's integrated loudness | Swell ≥ 3 dB above its under-speech level (the house broadband duck depth; 5.5's own lift is 10 dB, −20 → −10). In spans ≥ 2 s, music within ±3 LU of the voice's integrated loudness (5.5 [10:30, 13:30]: music alone ≈ dialogue level; tolerance is a proposal) | ebur128 short-term on the music stem; spans from whisper word timings |
| Q22 | Dialogue consistency | Per-sentence integrated loudness of the voice stem vs the voice median | **Fail any sentence ≥ 5 LU off the median** (5.5 [05:31–06:01]: a clip ≈ 5 dB low is corrected); report sentences ≥ 3 LU off (proposal) | ebur128 `I:` on voice-stem slices per whisper sentence |
| Q23 | Pre-master headroom | Sample peak of each stem and of the summed mix **before** the master limiter | Voice stem peaks around −10 dBFS (5.5 [04:30, 07:00]; report the value); **fail any stem or pre-limiter mix peak above −2 dBFS** (5.5 [08:00–09:01]: −2 dB leaves no headroom) | soundfile on the stems and pre-limiter bounce from `mix_v2.py` |
| Q24 | Master sweetening limits | Gain of each master-bus EQ band in the mix config | Every boost ≤ +5 dB; high shelf ≥ ~4 kHz, low boost ≈ 100–200 Hz (5.5 [20:00]) | Read the master EQ parameters from the mix JSON / `mix_v2.py` config |

### B.6 Anti-patterns / failure modes

| Anti-pattern | Symptom | Fix | Source |
|---|---|---|---|
| Fader-only ducking | The voice is clear only when the music is so low that it feels thin. The user asks for louder music; raising it masks words. | Add a voice-band notch (≈1–1.5 kHz) or frequency-split duck so the music can stay up | 5.6 [02:00–04:30], 5.4 [01:30], house |
| Captions as the intelligibility crutch | Words readable on screen but hard to hear | Fix the mix; the words gate runs on the master | 5.6 [01:39] |
| Same SFX every time | A machine-gun feel on list ticks or typing | Cut variants from a long take; use each once | 5.1 [03:01, 06:01] |
| Over-accenting | Every cut has a boom; ears fatigue; nothing feels important | Budget ≤ 2 hero accents; subtle single layers elsewhere | 5.1 [12:00–13:32] |
| Random-library mash | Cinematic boom, then cartoon pop, then glitch; feels cheap or "safe" | One palette matched to the series look | 5.4 [02:30–03:30], 5.1 [11:01] |
| Thin hero whoosh | A big whip transition with a weak sound | Layer low/mid/high | 5.4 [00:30–01:01] |
| Music slammed to a stop | The song cuts mid-phrase at the end ("slamming the brakes") | Cut before the next beat; reverb tail on the last beat or an impact on the sign-off | 5.4 [04:31–07:01] |
| Cold music start | The track pops in at full energy | Reversed first beat or tail as a riser; layer a swell or suckback | 5.4 [05:01–06:33] |
| Mood drift in the cue | The music changes character mid-ad | Edit out the section after the tone change | 5.1 [02:36, 04:01] |
| Flat-loud mix | No contrast; the CTA doesn't land; viewer disengages | A dip before the payoff; build toward it | 5.7 [07:02–08:30] |
| Silent graphics | A cutaway or card appears without a sound | A tick, whoosh or chime on the reveal | 5.1 [08:30] |
| Late/early SFX | A whoosh after the cut; a hit not on the landing | Align the apex to the frame (Q7) | 5.1 [06:01] |
| Clipping from stacking | Distortion on hits; TP over −1 | Gain stage SFX; lower the master; true-peak limit | 5.1 [14:01], 5.2 [08:31–09:02] |
| Unnormalised delivery | The platform turns it down or compresses it; the level is inconsistent across ads | Normalise to −14 LUFS / −1 dBTP | 5.2 [09:02], house |
| Boxy or honky voice | A ringing resonance; the voice can't be raised without harshness | Resonance sweep-and-cut on the voice bus (keep the fundamental) | 5.8 [04:30–08:01] |
| Cutting the fundamental | The voice sounds thin or unlike the speaker | Leave the first (lowest) resonance alone | 5.8 [06:00] |
| Room ambience under a denoised voice | Undoes DeepFilterNet; fails the voice-floor gate | No location ambience on A-roll; the music bed serves as room | house vs 5.1 [05:07] |
| Reverb on the voice | Room tail; feels amateur | Keep the voice dry; reverb only on SFX tails and music exits | house, 5.2 [07:01] (inverse) |
| Hot start | Dialogue levelled near −2 dB; later processing clips, or the platform turns it down | Level the dialogue to ≈ −10 dBFS peaks and keep headroom until the master limiter (Q23) | 5.5 [08:00–09:01] |
| Music left at import level | The bed buries the first words, or jumps loud between phrases | Always re-level the music; even out the track's own dynamics with gain automation | 5.5 [11:01–13:01] |
| Static bed level | The music stays tucked during no-speech cutaways and the intro, so those moments feel empty | Let the bed swell in no-speech spans (Q21) | 5.5 [13:30, 19:01] |
| Over-quiet bed | The bed sits 20 dB+ under the voice; the ad feels thin; the user asks for louder music | Raise it to the house −7 LU and carve the voice band instead (Q4, Q4b) | 5.5 [12:01], house |
| Mastering a bad mix | Loudness pushed up to target; problems get louder | Fix the mix first; master only sweetens and levels | 5.5 [17:31, 20:30] |
| Over-target master | Integrated above −14 LUFS; the platform turns it down and the limiter pumps | Bring it to −15 to −14 LUFS (Q1) | 5.5 [23:01, 26:32, 29:31] |
| Uneven dialogue | One sentence or take audibly quieter than the rest | Level per clip; relative normalise; compressor (Q22) | 5.5 [07:31–10:01] |
| Ears-only levels | Levels judged at whatever volume the monitors are at; inconsistent across ads | Set levels from meters; use ears for the blend | 5.5 [22:00–22:30, 31:00] |

### B.7 Conflicts & open questions

**1. Dialogue-vs-music level: where the videos land, with numbers.**

| Source | What it says | Units | Implied music-under-voice gap |
|---|---|---|---|
| 5.1 [14:01] | Dialogue ≈ −12 dB; SFX −10 to −30 dB; score −20 to −30 dB; nothing peaks | Peak-meter dBFS (NLE meters) | **8–18 dB** below dialogue on peaks |
| 5.6 [02:00] | Fader pull of the music ≈ −4.5 dB was better but still competing | Gain change (dB), relative to an unstated start | Broadband −4.5 dB |
| 5.6 [03:32] | Plus a notch at ≈1.5 kHz, −4 dB to taste; dialogue energy 1–1.5 kHz | EQ gain (dB) | About −8.5 dB total in the voice-presence band, −4.5 dB elsewhere |
| 5.4 [01:30] | Dynamic EQ/de-esser carving a mid pocket in the music; "lower the gain and call it a day" is the anti-pattern | No numbers | Frequency carve over fader |
| 5.2 [08:01, 09:02] | Remove voice frequencies from the music; normalise the mix to the platform standard | No numbers | Frequency carve |
| 5.8 [09:00] | Dialogue EQ lets the dialogue go "a little bit louder" and the music "balance in" | No numbers | — |
| 5.3, 5.7 | No level figures | — | — |
| 5.5 [04:30, 10:30–13:30, 16:00, 28:02] | Dialogue ≈ −10 dB; music alone ≈ −10 dB; music under dialogue −20 to −30 dB, "may need to be a little louder" −15 to −20 dB, and the −20 demo "might even sound a little quiet"; SFX −2 to −30 dB | Peak-meter dB (NLE mixer; normalise mode "sample peak") | **≈ 10 dB** typical on peaks (range 5–20 dB); **0 dB** with no dialogue |
| 5.5 [21:01–29:31] | Master: YouTube −14 LUFS integrated, "close to but not exceeding", aim ≈ −15; limiter ceiling −1 dB | Integrated loudness (LUFS) | — |
| **House (EDIT-STANDARD §3)** | Bed ≈ **−7 LU** under the voice; duck voice band −8 dB, lows/highs −3 dB; master −14 LUFS, −1 dBTP | Integrated loudness (LU) + duck gain (dB) | **7 LU** |

**Converting 5.1's peak figures to loudness (my estimate, not the video's).** Speech typically runs a higher peak-to-loudness ratio than a mastered music bed. Taking speech at roughly 15–18 dB PLR and mastered music at roughly 8–12 dB PLR (typical values, not from the videos): dialogue peaking at −12 dBFS would read roughly −27 to −30 LUFS, and a score peaking at −20 to −30 dBFS would read roughly −28 to −42 LUFS. That puts 5.1's music anywhere from **about 0–2 LU to about 12+ LU** under the dialogue, with the −20 dB end of its range landing **close to the house −7 LU**, or even louder than it. The only video giving numbers therefore **brackets** the house setting rather than contradicting it. The peak-level gap (8–18 dB) overstates the loudness gap.

**Converting 5.5's peak figures to loudness (my estimate, same assumptions).** Dialogue at ≈ −10 dBFS peaks reads roughly −25 to −28 LUFS. Music under dialogue at −20 dBFS reads roughly −28 to −32 LUFS, so the gap is **about 0–7 LU**. His louder option (−15 dBFS music) lands at roughly level with the voice or a few LU **above** it. His quiet end (−30 dBFS) is about 10–17 LU under. With no dialogue he puts music at the **same** meter level as dialogue. So 5.5's central recommendation puts the bed **at or louder than** the house −7 LU, and only the −30 dB end of his range is clearly quieter. He also hears his own −20 dB bed as possibly "a little quiet". The only source that states dialogue/music numbers outright therefore does **not** support turning the house bed down. If anything, it allows the louder bed the user keeps asking for. Caveat: the meter-to-LU conversion is mine, and it depends on the crest factor of the actual voice and track. Q4b now measures the peak-domain gap in 5.5's own units, so the house mix can be compared directly with his 5–20 dB (typically 10 dB).

**My call on level:** keep the house **≈ −7 LU** setting. Reasons: (a) the user asked three times for a louder bed and rejected −23, −14 and −10 LU (EDIT-STANDARD §3), so −7 LU is a user-validated value for this ad format; (b) the videos' consensus is about **how** to keep music loud without masking (EQ carve over fader: 5.6, 5.4, 5.2, 5.8), not a fixed level, and the house frequency-split duck has almost exactly the shape of 5.6's demonstrated fix (house −8 dB in-band and −3 dB broadband vs 5.6's −8.5 dB in-band and −4.5 dB broadband); (c) 5.1's −20 dB score figure is compatible with a single-digit LU gap; (d) 5.5, the one source with an explicit dialogue/music level recipe, lands at roughly 0–7 LU by estimate, i.e. **at or above** the house bed, and its −20 dB demo bed already risks sounding "a little quiet" [12:01]. What the videos add is the **acceptance test**: the music may be as loud as the user likes **provided the voice is heard "without straining"** (5.6 [04:30]). So the binding gate is intelligibility (Q6 words gate on the master, plus earshot listening), with Q4 (offset) and Q4b (peak gap) reported and Q5 (notch depth) enforced. **Updated after 5.5:** −7 LU is now the **floor** for bed loudness under speech (Q4 fails below −9 LU). If the user asks for louder again, it is supported to go to about −5 or −4 LU, provided the words gate passes and the voice-band carve deepens to match. 5.5 also adds the missing half of the picture: in no-speech spans the bed should come **up** to about voice level (Q21), which makes the music feel bigger without touching intelligibility.

**2. Ducking practice.** The videos never use the word "sidechain" or give attack/release times. 5.6 uses a **static** notch plus a static fader drop; 5.4 uses a **dynamic EQ/de-esser** on the music (which reacts, so it is effectively frequency-selective ducking). The house uses dynamic frequency-split ducking. *Conflict:* none of substance; the house is the most advanced of the three. *Open question:* where exactly is the house "voice band"? The videos point to a centre around **1–1.5 kHz** (5.6) inside a speech range of **≈150 Hz–5 kHz** (5.8). If the house voice band is narrower than that (e.g. 1–4 kHz only), consider extending its lower edge to about 200–300 Hz on male voices, where music low-mids mask on phone speakers. Verify with Q5 and A/B in earshot. No attack/release numbers are given by any source; keep whatever avoids audible pumping (QA item).

**3. "Nothing is silent / always ambience" (5.1 [00:30, 05:07]) vs the house voice-floor gate (≤ −60 dBFS between words) and denoising.** *Call:* no conflict once stems are separated. The floor gate applies to the voice stem; the master is never dead because the music bed runs throughout. Do not add location ambience under the A-roll.

**4. Silence and dynamics (5.7, 5.2 [03:00], 5.3 [04:36]) vs the house "no gap > 0.25 s" pause rule.** *Call:* the house rule governs **speech** gaps. Contrast in a 30–60 s ad is achieved by a **music dip** (pull the bed 6–10 dB or strip it to a single element for a beat; magnitude not from the videos, so tune by ear) under continuous speech, or a ≤ 0.25 s pre-payoff breath, not true silence. Long silent suspense does not transfer.

**5. Reverb (5.1 [07:30], 5.2 [07:01–07:31]) vs the house "no audible room tail" on the voice.** *Call:* house wins for the voice. Reverb is allowed on SFX tails and on music exits (5.4 [05:30–06:00]).

**6. Panning (5.2 [05:30]).** *Open:* Reels playback is often mono or near-mono on phones. Keep the voice and key SFX centred, and check mono-compatibility (sum to mono; no cancellation) before using wide stereo whooshes.

**7. "Hear everything we see" (5.1 [00:30]) vs accent economy (5.1 [13:00]) and earshot's salient-hit density.** Both come from the same video. *Call:* every **graphic event** gets sound, but at low level (ticks, soft pops). Only ≤ 2 events get hero intensity. Don't sound-design the speaker's gestures.

**8. Evidence gaps.** No source in this module gives LU/LUFS **stem** offsets, ducking attack/release, or Meta/Instagram-specific delivery targets. 5.5 (the replacement) closes part of the gap: it gives explicit peak-meter dialogue, music and SFX targets and a −14 LUFS / −1 dB-ceiling master (for YouTube). The −7 LU figure can now be compared with a stated professional recipe, and it sits at the quieter edge of 5.5's typical range (B.7.1). Still missing: a source in LU between stems, and a platform-specific Meta target (the house uses −14 LUFS, the common streaming norm).

**9. Master target: house −14 LUFS vs 5.5's "aim about −15".** 5.5 says get close to −14 but never above, and in practice aims 1 LU under [29:31]. *Call:* keep the house −14 target, but treat −14.0 as a **ceiling**. Q1 now passes −15.0 to −14.0 LUFS (it used to be −14 ±0.5, which let −13.5 through). The ad is too short for 5.5's "a short loud stretch averages out" leniency [26:00] to be relied on.

**10. Inaccuracies in 5.5 to ignore.** (a) He says a mix above −14 LUFS gets "compressed" or "clipped" by YouTube [26:00–26:32]. In practice, loudness normalisation on YouTube, Meta and similar platforms turns playback **gain down**; it doesn't add clipping. The practical rule (don't exceed the target) is unchanged. (b) He is unsure about Netflix and broadcast ("I think −23"). The industry norms are EBU R128 −23 LUFS for broadcast; Netflix specifies −27 LKFS dialogue-gated. Neither applies to Reels. (c) His per-stem numbers are **peak** readings presented as universal. They are good gain-staging guides, but they are not loudness targets and are not comparable with the house LU figures without conversion (B.7.1).

**11. Peak targets vs a code pipeline.** 5.5's "−10 dB dialogue" is a gain-staging step for an NLE. In `mix_v2.py`, absolute stem levels before the master stage are internal. What transfers is the **headroom principle** (Q23: nothing above −2 dBFS pre-limiter) and the **relationships**: music ≈ 10 dB under the voice on peaks, music ≈ voice level with no dialogue, SFX spread −2 to −30 dB. *Call:* gate the relationships (Q4, Q4b, Q21), and only report the absolute stem levels.
