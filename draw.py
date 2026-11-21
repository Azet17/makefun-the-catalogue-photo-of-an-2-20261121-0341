#!/usr/bin/env python3
"""Procedural catalogue photograph of 'The Ice-Kettle 3000'.

Draws a chrome electric kettle pouring ice cubes into a ceramic mug,
on a warm-grey studio backdrop. Deterministic (fixed seed), 2x
supersampled then downsampled to 1024x1024 for anti-aliasing.
"""
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

random.seed(42)

S = 2                    # supersample factor
W, H = 1024 * S, 1024 * S
OUT = "entry.png"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def multi_gradient(size, stops, horizontal=True):
    """stops: list of (pos 0..1, (r,g,b)). Returns RGB image."""
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    n = w if horizontal else h
    for i in range(n):
        t = i / max(n - 1, 1)
        for j in range(len(stops) - 1):
            p0, c0 = stops[j]
            p1, c1 = stops[j + 1]
            if p0 <= t <= p1:
                f = 0 if p1 == p0 else (t - p0) / (p1 - p0)
                col = lerp_color(c0, c1, f)
                break
        else:
            col = stops[-1][1]
        if horizontal:
            for y in range(h):
                px[i, y] = col
        else:
            for x in range(w):
                px[x, i] = col
    return img


def vertical_gradient(size, stops):
    return multi_gradient(size, stops, horizontal=False)


def paste_masked(base, layer, mask):
    base.paste(layer, (0, 0), mask)


# ---------------------------------------------------------------- background
bg = vertical_gradient((W, H), [
    (0.00, (216, 210, 200)),
    (0.45, (205, 198, 186)),
    (0.72, (188, 180, 168)),
    (1.00, (158, 149, 137)),
])
img = bg.convert("RGBA")

# radial spotlight glow centred behind the kettle
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([W * 0.18, H * 0.02, W * 0.82, H * 0.78],
           fill=(255, 244, 224, 110))
glow = glow.filter(ImageFilter.GaussianBlur(180))
img = Image.alpha_composite(img, glow)

# floor band (subtle, slightly darker warm grey below horizon)
floor = Image.new("RGBA", (W, H), (0, 0, 0, 0))
fd = ImageDraw.Draw(floor)
fd.rectangle([0, H * 0.74, W, H], fill=(120, 111, 100, 70))
img = Image.alpha_composite(img, floor)

# soft elliptical shadow under the products
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow)
sd.ellipse([W * 0.20, H * 0.755, W * 0.88, H * 0.815], fill=(40, 34, 28, 150))
shadow = shadow.filter(ImageFilter.GaussianBlur(28))
img = Image.alpha_composite(img, shadow)

d = ImageDraw.Draw(img)

# ------------------------------------------------------------------- helpers
CHROME_STOPS = [
    (0.00, (52, 56, 62)),
    (0.10, (96, 101, 107)),
    (0.22, (228, 232, 235)),
    (0.38, (150, 156, 162)),
    (0.52, (214, 219, 222)),
    (0.66, (120, 126, 132)),
    (0.80, (198, 203, 207)),
    (0.92, (84, 89, 95)),
    (1.00, (44, 48, 53)),
]


def chrome_fill(bbox):
    """Horizontal chrome gradient clipped to bbox, with a top-light falloff."""
    x0, y0, x1, y1 = bbox
    grad = multi_gradient((x1 - x0, y1 - y0), CHROME_STOPS, horizontal=True)
    grad = grad.convert("RGBA")
    # vertical light falloff: brighter at top, darker at bottom
    shade = vertical_gradient((x1 - x0, y1 - y0), [
        (0.0, (255, 255, 255)),
        (0.5, (255, 255, 255)),
        (1.0, (120, 120, 120)),
    ]).convert("RGBA")
    dark = Image.new("RGBA", grad.size, (0, 0, 0, 0))
    grad = Image.blend(grad, Image.composite(
        Image.new("RGBA", grad.size, (255, 255, 255, 255)),
        dark, shade.convert("L").point(lambda v: 255 - v)), 0.0)
    # simpler: apply vertical brightness by compositing a white/black overlay
    overlay = Image.new("RGBA", grad.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, 0, x1 - x0, (y1 - y0) * 0.35], fill=(255, 255, 255, 26))
    od.rectangle([0, (y1 - y0) * 0.72, x1 - x0, y1 - y0], fill=(0, 0, 0, 60))
    grad = Image.alpha_composite(grad, overlay)
    return grad


def body_mask():
    """Kettle body silhouette mask (RGBA alpha)."""
    m = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(m)
    cx = W * 0.40
    top_y, bot_y = H * 0.375, H * 0.755
    # half-width profile: narrow at lid, bulging low, slightly tucked base
    def half_w(y):
        t = (y - top_y) / (bot_y - top_y)
        t = max(0.0, min(1.0, t))
        return lerp(0.155, 0.175, t) * W * (1 + 0.22 * math.sin(t * math.pi) ** 1.2) \
            - 0.012 * W * t * t
    pts = []
    steps = 60
    for i in range(steps + 1):
        y = top_y + (bot_y - top_y) * i / steps
        pts.append((cx + half_w(y), y))
    for i in range(steps, -1, -1):
        y = top_y + (bot_y - top_y) * i / steps
        pts.append((cx - half_w(y), y))
    md.polygon(pts, fill=255)
    # rounded bottom cap
    md.ellipse([cx - 0.155 * W, bot_y - 0.06 * W,
                cx + 0.155 * W, bot_y + 0.02 * W], fill=255)
    return m


# -------------------------------------------------------------------- handle
# brushed-metal C handle on the left side of the body
handle_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
hd = ImageDraw.Draw(handle_layer)
bbox_h = [W * 0.150, H * 0.44, W * 0.300, H * 0.70]
hd.arc(bbox_h, start=100, end=260, fill=(58, 61, 66, 255), width=int(0.030 * W))
hd.arc([bbox_h[0] + 8, bbox_h[1] + 8, bbox_h[2] - 8, bbox_h[3] - 8],
       start=110, end=250, fill=(168, 173, 178, 255), width=int(0.010 * W))
# handle mounts
for my in (H * 0.465, H * 0.665):
    hd.ellipse([W * 0.270, my - 0.022 * W, W * 0.320, my + 0.022 * W],
               fill=(52, 55, 60, 255))
img = Image.alpha_composite(img, handle_layer)

# ------------------------------------------------------------------ kettle body
mask = body_mask()
bbox = (int(W * 0.40 - 0.20 * W), int(H * 0.375),
        int(W * 0.40 + 0.20 * W), int(H * 0.775))
grad = chrome_fill(bbox)
body = Image.new("RGBA", (W, H), (0, 0, 0, 0))
body.paste(grad, bbox[:2], mask.crop(bbox))
img = Image.alpha_composite(img, body)
d = ImageDraw.Draw(img)  # rebind: alpha_composite returns a new image

# soft vertical specular band on the body
spec = Image.new("RGBA", (W, H), (0, 0, 0, 0))
spd = ImageDraw.Draw(spec)
spd.rectangle([W * 0.315, H * 0.40, W * 0.355, H * 0.72],
              fill=(255, 255, 255, 70))
spec = spec.filter(ImageFilter.GaussianBlur(18))
img = Image.alpha_composite(img, spec)

# dark base ring
d.ellipse([W * 0.265, H * 0.735, W * 0.535, H * 0.775],
          fill=(38, 40, 44, 255))
d.ellipse([W * 0.285, H * 0.740, W * 0.515, H * 0.762],
          fill=(70, 73, 78, 255))

# ------------------------------------------------------------------ lid + knob
lid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ld = ImageDraw.Draw(lid)
ld.ellipse([W * 0.295, H * 0.335, W * 0.505, H * 0.395],
           fill=(96, 100, 106, 255))
ld.ellipse([W * 0.305, H * 0.338, W * 0.495, H * 0.378],
           fill=(150, 155, 160, 255))
img = Image.alpha_composite(img, lid)
d = ImageDraw.Draw(img)  # rebind after composite
# knob: dark sphere with a bright top-left highlight
d.ellipse([W * 0.375, H * 0.295, W * 0.425, H * 0.345],
          fill=(42, 44, 48, 255))
d.ellipse([W * 0.385, H * 0.300, W * 0.405, H * 0.320],
          fill=(210, 214, 218, 255))

# ---------------------------------------------------------------------- spout
# curved spout: bezier from body right side, rising slightly then
# tipping down toward the mug
def bezier(p0, p1, p2, p3, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = ((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0]
             + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0])
        y = ((1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1]
             + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1])
        pts.append((x, y))
    return pts


sp = bezier((W * 0.53, H * 0.46), (W * 0.60, H * 0.40),
            (W * 0.66, H * 0.42), (W * 0.685, H * 0.52))
spout_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
spd2 = ImageDraw.Draw(spout_layer)
# taper the spout: draw as a series of circles along the curve
for i, (x, y) in enumerate(sp):
    r = lerp(0.052, 0.034, i / (len(sp) - 1)) * W
    spd2.ellipse([x - r, y - r, x + r, y + r], fill=(160, 165, 170, 255))
# chrome shading over the spout tube
spout_grad = multi_gradient(
    (int(W * 0.20), int(H * 0.16)), CHROME_STOPS, horizontal=True).convert("RGBA")
spout_grad = spout_grad.resize((int(W * 0.20), int(H * 0.16)))
tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
tmp.paste(spout_grad, (int(W * 0.51), int(H * 0.40)))
alpha = Image.new("L", (W, H), 0)
ad = ImageDraw.Draw(alpha)
for i, (x, y) in enumerate(sp):
    r = lerp(0.052, 0.034, i / (len(sp) - 1)) * W
    ad.ellipse([x - r, y - r, x + r, y + r], fill=255)
tmp.putalpha(Image.composite(alpha, Image.new("L", (W, H), 0), alpha))
# rebuild: paste gradient only where the tube alpha is
tube = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sx, sy = int(W * 0.51), int(H * 0.40)
sw, sh = spout_grad.size
tube.paste(spout_grad, (sx, sy), alpha.crop((sx, sy, sx + sw, sy + sh)))
img = Image.alpha_composite(img, tube)
d = ImageDraw.Draw(img)  # rebind after composite
# spout tip opening (dark, angled)
tip = sp[-1]
d.ellipse([tip[0] - 0.030 * W, tip[1] - 0.012 * W,
           tip[0] + 0.030 * W, tip[1] + 0.022 * W],
          fill=(30, 32, 36, 255))

# ------------------------------------------------------------------ label text
try:
    font = ImageFont.truetype(FONT_BOLD, int(0.030 * W))
except Exception:
    font = ImageFont.load_default()
label = "ICE-KETTLE 3000"
# draw on its own layer so it sits on the chrome with slight emboss
tl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
td = ImageDraw.Draw(tl)
bb = td.textbbox((0, 0), label, font=font)
tw, th = bb[2] - bb[0], bb[3] - bb[1]
lx, ly = W * 0.40 - tw / 2, H * 0.565 - th / 2
td.text((lx + 2, ly + 2), label, font=font, fill=(255, 255, 255, 90))
td.text((lx, ly), label, font=font, fill=(28, 30, 34, 235))
img = Image.alpha_composite(img, tl)

# ------------------------------------------------------------------------- mug
mug_cx = W * 0.755
mug_top, mug_bot = H * 0.60, H * 0.765
mug_hw = 0.105 * W
# mug handle (behind body)
mh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
mhd = ImageDraw.Draw(mh)
mhd.arc([mug_cx + mug_hw * 0.72, mug_top + 0.02 * W,
         mug_cx + mug_hw * 1.62, mug_bot - 0.01 * W],
        start=270, end=90, fill=(238, 236, 232, 255), width=int(0.016 * W))
mhd.arc([mug_cx + mug_hw * 0.72, mug_top + 0.02 * W,
         mug_cx + mug_hw * 1.62, mug_bot - 0.01 * W],
        start=270, end=90, fill=(190, 186, 180, 255), width=int(0.005 * W))
img = Image.alpha_composite(img, mh)
# mug body: soft ceramic vertical gradient
mug_grad = vertical_gradient((int(mug_hw * 2), int(mug_bot - mug_top)), [
    (0.0, (250, 248, 244)),
    (0.5, (233, 230, 225)),
    (1.0, (196, 191, 184)),
]).convert("RGBA")
mug_mask = Image.new("L", (W, H), 0)
mmd = ImageDraw.Draw(mug_mask)
mmd.rounded_rectangle([mug_cx - mug_hw, mug_top, mug_cx + mug_hw, mug_bot],
                     radius=int(0.02 * W), fill=255)
mug_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
mx, my = int(mug_cx - mug_hw), int(mug_top)
mw, mh = mug_grad.size
mug_img.paste(mug_grad, (mx, my), mug_mask.crop((mx, my, mx + mw, my + mh)))
img = Image.alpha_composite(img, mug_img)
d = ImageDraw.Draw(img)
# rim + dark coffee-less interior
d.ellipse([mug_cx - mug_hw, mug_top - 0.012 * W,
           mug_cx + mug_hw, mug_top + 0.012 * W],
          fill=(244, 242, 238, 255))
d.ellipse([mug_cx - mug_hw * 0.88, mug_top - 0.008 * W,
           mug_cx + mug_hw * 0.88, mug_top + 0.008 * W],
          fill=(88, 96, 104, 255))
# glossy vertical highlight on the mug
hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
hld = ImageDraw.Draw(hl)
hld.rectangle([mug_cx - mug_hw * 0.62, mug_top + 0.01 * W,
               mug_cx - mug_hw * 0.42, mug_bot - 0.01 * W],
              fill=(255, 255, 255, 60))
hl = hl.filter(ImageFilter.GaussianBlur(10))
img = Image.alpha_composite(img, hl)

# ------------------------------------------------------------------- ice cubes
def ice_cube(layer, cx, cy, size, angle_deg, alpha=215):
    """One translucent pale-blue rounded cube with glossy facets."""
    c = Image.new("RGBA", (int(size * 2.4), int(size * 2.4)), (0, 0, 0, 0))
    cd = ImageDraw.Draw(c)
    o = size * 1.2
    cd.rounded_rectangle([o - size / 2, o - size / 2, o + size / 2, o + size / 2],
                         radius=size * 0.22, fill=(178, 214, 235, alpha))
    cd.rounded_rectangle([o - size / 2, o - size / 2, o + size / 2, o + size / 2],
                         radius=size * 0.22, outline=(255, 255, 255, 200),
                         width=max(2, int(size * 0.03)))
    # inner facet lines
    cd.line([o - size * 0.28, o - size * 0.28, o + size * 0.28, o + size * 0.10],
            fill=(255, 255, 255, 170), width=max(2, int(size * 0.035)))
    cd.line([o + size * 0.10, o - size * 0.28, o - size * 0.05, o + size * 0.30],
            fill=(235, 245, 252, 150), width=max(2, int(size * 0.03)))
    # specular dot
    cd.ellipse([o - size * 0.30, o - size * 0.36, o - size * 0.10, o - size * 0.16],
               fill=(255, 255, 255, 235))
    c = c.rotate(angle_deg, resample=Image.BICUBIC, center=(o, o))
    layer.alpha_composite(c, (int(cx - size * 1.2), int(cy - size * 1.2)))


cubes = Image.new("RGBA", (W, H), (0, 0, 0, 0))
# tumbling arc from the spout tip down into the mug
ice_cube(cubes, W * 0.700, H * 0.555, 0.052 * W, -18)
ice_cube(cubes, W * 0.725, H * 0.585, 0.048 * W, 24)
ice_cube(cubes, W * 0.748, H * 0.565, 0.042 * W, -32)
# cubes resting in the mug, peeking over the rim
ice_cube(cubes, W * 0.735, H * 0.598, 0.046 * W, 12)
ice_cube(cubes, W * 0.775, H * 0.600, 0.040 * W, -25)
img = Image.alpha_composite(img, cubes)

# ------------------------------------------------------------- cold vapour
vap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
vd = ImageDraw.Draw(vap)
for x0, amp, ph in ((0.715, 26, 0.0), (0.760, 34, 1.4), (0.795, 22, 2.6)):
    pts = []
    for i in range(41):
        t = i / 40
        y = H * 0.585 - t * 0.085 * H
        x = W * x0 + math.sin(t * math.pi * 2 + ph) * amp * (0.4 + t)
        pts.append((x, y))
    vd.line(pts, fill=(255, 255, 255, 60), width=int(0.012 * W), joint="curve")
vap = vap.filter(ImageFilter.GaussianBlur(14))
img = Image.alpha_composite(img, vap)

# ------------------------------------------------------------------ film grain
noise = Image.effect_noise((W, H), 18).convert("L")
grain = Image.merge("RGBA", (noise, noise, noise, noise.point(lambda v: 14)))
img = Image.alpha_composite(img, grain)

# ------------------------------------------------------- downsample and save
final = img.convert("RGB").resize((1024, 1024), Image.LANCZOS)
final.save(OUT, format="PNG", optimize=True)
print("saved", OUT, final.size)
