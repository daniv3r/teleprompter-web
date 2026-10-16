# Screenshot assets


Five original application captures are included as ten proportionally resized WebP files:

| Website image | Real capture | Widths |
| --- | --- | --- |
| Hero reader | iPhone `01_hero` | 480, 960 |
| Cards tour | iPhone `03_key_feature` | 480, 960 |
| Reading settings | iPhone `05_personalize` | 480, 960 |
| Script library/editor | iPad `04_collection` | 640, 1200 |
| Native Mac reader | Mac `01_hero` | 960, 1600 |

`inputs/screenshots.json` records original capture hashes, dates, binary identity, reused status,
and exact website variant hashes/dimensions. No app controls or text are redrawn, retouched,
or stretched. The three iPhone images use the existing silver iPhone 17 Pro hardware artwork,
with its exact screen opening, rounded screen mask, and camera cutout. The frame source pack,
hash, and screen geometry are recorded per image. No AI-generated pictures are used.
The iPad image uses the existing Space Gray 13-inch iPad Pro frame with its exact screen opening.
The frame pack labels this artwork M4; the original capture remains from the M5 simulator.
Mac has no added device frame. No image has extra CSS corner rounding or clipping.

The iPad library capture was reused from October 13. The Mac capture includes a visible system
capture indicator. All captures are Debug review assets, not final release qualification.
Final-build matching and publication review remain open; do not hide these limits by editing images.

Optional asset regeneration requires Pillow. Install it in your own virtual environment;
normal builds and publication do not need it. Run these commands from the repository root:

```sh
python3 -m pip install -r tools/requirements.txt
python3 tools/refresh_assets.py --marketing ../marketing
```

This verifies each source against its canonical capture manifest, preserves original reused-capture
identity, regenerates the same proportional variants, and resets screenshot approvals. Review
original content rights, iPhone/iPad artwork rights, and final candidate matching before setting each
asset's `publication_ready`, its `frame.publication_ready` where present, and the website's
`screenshots_approved` to true. A hash mismatch fails the build even in preview mode.


The resized WebP images live in `assets/screenshots/` and must be committed: the website is
self-contained and cannot regenerate them during a Pages build. Original captures and full-size
hardware artwork remain in the separate marketing repository and are not needed to host the site.

Refresh writes `inputs/screenshots.json` and resets screenshot approval in `inputs/policy.json`.
Do not hand-edit image hashes to bypass a changed-asset review.
