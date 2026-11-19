"""Shared layout for the v0.2 UI cutaways (cutaways.py) and roto cards (roto.py): one arrangement per canvas shape.

These templates were designed on a 1080x1920 frame. They are relative templates now (templates._canvas_render): they lay
out on a canvas with a 1080 short side (G.W x G.H) and are rasterised at the real canvas, so they are sharp at 4K.
Three arrangements, picked from the aspect of the canvas:
  tall    (W/H <= 2/3: 9:16, 2:3)   the original vertical layout. On a 1080x1920 layout canvas its numbers are used as they
                                     were (the golden frames hold); on a shorter tall canvas the block is re-centred on the
                                     safe zone (`dy`)
  square  (2/3 < W/H < 1.3: 1:1, 4:5, 3:4)  the vertical layout scaled down to fit the safe zone, centred
  wide    (W/H >= 1.3: 16:9, 2.39:1, 4:3)    a landscape arrangement: wider panels, two columns where a list is long,
                                     type and rows scaled up to fill the safe zone height
Every size inside a template is `value * s` (s = 1 in tall), so the vertical output keeps its exact numbers."""
from .. import gfx as G

TALL_SAFE_CY = (269 + 1248) / 2          # centre of the default 9:16 platform.safe_zone (the design the tall numbers come from)


def mode():
    r = G.W / G.H
    if r <= 2 / 3 + 1e-3: return "tall"
    return "wide" if r >= 1.3 else "square"


def zone():
    """(x0, y0, x1, y1, w, h, cx, cy) of the safe zone on the layout canvas"""
    z = G.safe(); return (z[0], z[1], z[2], z[3], z[2] - z[0], z[3] - z[1], (z[0] + z[2]) / 2, (z[1] + z[3]) / 2)


def tall_dy():
    """vertical offset of the tall layout: 0 on the 1080x1920 layout canvas (the original numbers), else the block follows
    the safe-zone centre"""
    if G.H == 1920: return 0.0
    return zone()[7] - TALL_SAFE_CY * G.H / 1920


def fit(block_w, block_h, grow=1.0, fill=.94):
    """scale s for a block designed at (block_w, block_h) px so it fills the safe zone: never above `grow`, never so big it
    leaves the zone"""
    z = zone(); return max(.35, min(grow, z[4] * fill / max(1., block_w), z[5] * fill / max(1., block_h)))
