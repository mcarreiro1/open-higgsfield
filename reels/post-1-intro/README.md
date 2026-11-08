# Post 1: Intro Reel (pin this)

`post-1-intro.mp4`: 1080×1920, 30 fps, 28 s, with a quiet lo-fi music bed. The host wears a red hoodie with the lime pixel mask. Captions are burned in, so record your voiceover over the top using the timings below.

Re-render with `python3 render.py` (needs Pillow, numpy, ffmpeg).

## Timeline

| Time | Shot | On screen |
| --- | --- | --- |
| 0.0–3.0 | Masked host at desk, slow push-in | Hook: "I'm not a tech person. / I know nothing about AI. / Let's fix that, in public." |
| 3.0–8.6 | Close-up: red-sleeved hands open the laptop, screen wakes | Captions |
| 8.6–15.7 | Blank chat page, blinking cursor | Timer chip starts at 10.6 s, "stuck…" tag at 12.4 s |
| 15.7–24.6 | Back to masked host (the mask flickers as "talking") | Captions, 👇 on the CTA |
| 24.6–28.0 | End card over host | Pixel rooster, "DAY 1 · learning AI from zero. · Stay free range." |

## Voiceover timing (record to this)

```
0.3   Everyone keeps telling me AI is going to change everything.
4.7   Honestly? I don't even know where to start.
6.5   So I'm going to learn it from zero, right here.
8.7   Every week I'll try a free AI tool,
10.6  time how long it really takes me,
12.4  show you where I get stuck,
14.0  and tell you if it was worth it.
15.7  No courses. No "make $10k with AI".
18.0  Just me figuring it out.
19.8  What should I try first?
22.0  Tell me in the comments.
```

Note: the first caption appears at 2.7 s, after the hook clears, but the voiceover can start right away.

## Caption

```
Day 1 of learning AI from zero. 🐓

I'm not a tech person. Every week I'm testing one free AI tool and showing you the real version: how long it took, where I got stuck, and whether it was worth it.

If you've been curious but overwhelmed, follow along. We'll figure it out together.

👇 What should I try first?

Stay free range. 🐓

#learnai #aiforbeginners #freeaitools #techforbeginners
```

## Photoreal version: prompts for the studio

Use these to make live-action versions of the shots in the OpenHiggsfield studio. Make the start frame with Soul Cinema at 9:16, then animate it with Seedance 2.5 or Kling 3 at 9:16. Use the same character description in every prompt so the host stays consistent.

**Character:** a person in a bright red oversized hoodie with the hood up. Their face is fully covered by a glowing lime-green (#d1fe17) pixel-mosaic mask made of square blocks, with no facial features visible.

1. **Masked desk shot (start frame, Soul Cinema 9:16):** "[Character] sitting at a wooden desk in a dim cozy bedroom at night, warm desk-lamp glow, closed silver laptop and white mug on the desk, blue window light behind, facing the camera, centered medium shot, cinematic, shallow depth of field"
   **Animate (Seedance 2.5, 3 s):** "subtle handheld push-in, the person tilts their head slightly toward the camera, gentle breathing, the pixel mask shimmers"
2. **Hands open laptop (Seedance 2.5 / Kling 3, 5 s):** "close-up from slightly above, hands in red hoodie sleeves open a silver laptop on a wooden desk, screen lights up, warm lamp light, shallow depth of field"
3. **Blank screen (Kling 3, 5 s):** "slow push-in on a laptop screen showing a minimal dark AI chat page with an empty text box and a blinking cursor, nothing typed"
4. **Masked CTA shot:** reuse the shot 1 start frame. Prompt: "the person leans in and points down toward the bottom of the frame, playful gesture"

Edit the clips together with the timings above, then lay the captions and voiceover on top.
