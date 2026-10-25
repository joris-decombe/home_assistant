"""Draw the South Coast theme's panorama (config/themes/south_coast.yaml).

Writes config/www/ipad/coast-day.svg and coast-night.svg: a 1600x260
panorama that the theme lays across the top of the screen at full width,
behind the clock. Its sky and its bottom both fade into the page colour.
Seeded, so reruns draw the same scene.

    python scripts/coast_svg.py
"""
import math, os, random

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "www", "ipad")
W, H = 1600, 260


def leaf(bx, by, length, angle, width, bend):
    """A harakeke blade: base at (bx, by), leaning `angle` degrees from vertical."""
    a = math.radians(angle)
    tx, ty = bx + length * math.sin(a), by - length * math.cos(a)
    # Bend the blade sideways near its tip.
    nx, ny = math.cos(a), math.sin(a)
    mx, my = (bx + tx) / 2 + nx * bend, (by + ty) / 2 + ny * bend
    tx2, ty2 = tx + nx * bend * 1.4, ty + ny * bend * 1.4
    return (f"M{bx - width / 2:.1f},{by:.1f} Q{mx - width * 0.3:.1f},{my:.1f} {tx2:.1f},{ty2:.1f} "
            f"Q{mx + width * 0.3:.1f},{my:.1f} {bx + width / 2:.1f},{by:.1f}Z")


def flax(cx, by, scale, colours, seed, stalks, flower, stalk_col):
    """A harakeke bush, with `stalks` flower stalks behind its leaves."""
    r = random.Random(seed)
    out = []
    for _ in range(stalks):
        x = cx + r.uniform(-25, 25) * scale
        top = by - r.uniform(230, 290) * scale
        lean = r.uniform(-18, 18) * scale
        out.append(f'<path d="M{x:.1f},{by} Q{x + lean / 2:.1f},{(by + top) / 2:.1f} {x + lean:.1f},{top:.1f}" '
                   f'stroke="{stalk_col}" stroke-width="{3 * scale:.1f}" fill="none" stroke-linecap="round"/>')
        for k in range(6):
            t = 0.45 + k * 0.09
            fx, fy = x + lean * t * t, by + (top - by) * t
            side = 1 if k % 2 else -1
            out.append(f'<path d="M{fx:.1f},{fy:.1f} q{side * 9 * scale:.1f},{-6 * scale:.1f} {side * 14 * scale:.1f},{-18 * scale:.1f}" '
                       f'stroke="{flower}" stroke-width="{4 * scale:.1f}" fill="none" stroke-linecap="round"/>')
    n = 15
    for i in range(n):
        ang = -60 + 120 * i / (n - 1) + r.uniform(-6, 6)
        length = (150 + 90 * math.cos(math.radians(ang)) + r.uniform(-20, 20)) * scale
        d = leaf(cx + r.uniform(-12, 12) * scale, by + 4, length, ang, r.uniform(14, 20) * scale, ang * 0.6 * scale)
        out.append(f'<path d="{d}" fill="{colours[i % len(colours)]}"/>')
    return "\n".join(out)


def toetoe(x, by, h, seed, stem, plume):
    """Four toetoe stems with their feathery plumes."""
    r = random.Random(seed)
    out = []
    for i in range(4):
        lean = r.uniform(-30, 30)
        tx, ty = x + lean + r.uniform(-10, 10), by - h * r.uniform(0.85, 1.05)
        out.append(f'<path d="M{x + i * 4:.1f},{by} Q{x + lean / 3:.1f},{by - h / 2:.1f} {tx:.1f},{ty:.1f}" '
                   f'stroke="{stem}" stroke-width="2" fill="none"/>')
        out.append(f'<path d="M{tx:.1f},{ty:.1f} q{lean / 6 + 6:.1f},{h * 0.12:.1f} {lean / 10:.1f},{h * 0.32:.1f} '
                   f'q-8,{-h * 0.16:.1f} {-lean / 10:.1f},{-h * 0.32:.1f}Z" fill="{plume}"/>')
    return "\n".join(out)


def waves(y0, y1, colour, op, seed):
    """Short swell lines, longer and thicker towards the shore."""
    r = random.Random(seed)
    out = []
    for i in range(9):
        y = y0 + (y1 - y0) * (i + 0.5) / 9
        near = (y - y0) / (y1 - y0)
        x = r.uniform(0, W)
        ln = r.uniform(60, 180) * (0.5 + near)
        out.append(f'<path d="M{x:.0f},{y:.1f} q{ln / 2:.0f},-4 {ln:.0f},0" stroke="{colour}" '
                   f'stroke-width="{1.2 + 1.5 * near:.1f}" fill="none" stroke-linecap="round" opacity="{op}"/>')
    return "\n".join(out)


def scene(c, night):
    # Sky fading in from the page colour, the horizon (Cook Strait, with the
    # Kaikoura ranges beyond) just under the date, then sea, beach, and a fade
    # into the page colour where the cards start. Flax and toetoe stand on a
    # dune in the middle, where the header is empty (the clock is on the
    # left, the badges on the right).
    ranges = ("M0,136 L90,130 L170,122 L240,126 L310,110 L370,116 L430,100 L480,108 L540,94 L610,110 L690,106 "
              "L770,118 L850,114 L930,124 L1010,120 L1090,128 L1190,124 L1290,130 L1410,126 L1510,132 L1600,129 "
              "L1600,142 L0,142Z")
    ranges2 = "M390,142 L455,118 L505,124 L560,108 L610,120 L660,116 L720,128 L800,142Z"
    beach = "M0,186 C260,176 520,178 800,184 C1060,190 1320,178 1600,174 L1600,240 L0,240Z"
    surf = "M0,185 C260,175 520,177 800,183 C1060,189 1320,177 1600,173"
    dune = "M640,240 C700,202 780,186 880,184 C980,182 1060,198 1120,240Z"
    rocks = [(1300, 176, 40, 11), (1345, 180, 22, 7), (300, 183, 30, 8), (1480, 172, 26, 8)]
    if night:
        light = (f'<circle cx="1180" cy="40" r="14" fill="{c["moon"]}"/>'
                 f'<path d="M1150,142 L1210,142 L1196,180 L1164,180Z" fill="{c["moon"]}" opacity="0.12"/>')
    else:
        light = '<circle cx="1180" cy="70" r="80" fill="url(#sun)"/>'
    rock_els = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{c["rock"]}"/>' for x, y, rx, ry in rocks)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMin slice">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{c["sky"]}" stop-opacity="0"/><stop offset="1" stop-color="{c["sky"]}"/></linearGradient>
<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{c["sea_far"]}"/><stop offset="1" stop-color="{c["sea_near"]}"/></linearGradient>
<linearGradient id="sand" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{c["sand_top"]}"/><stop offset="1" stop-color="{c["sand_bottom"]}"/></linearGradient>
<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{c["page"]}" stop-opacity="0"/><stop offset="1" stop-color="{c["page"]}" stop-opacity="1"/></linearGradient>
<radialGradient id="sun"><stop offset="0" stop-color="#fff6dc" stop-opacity="0.9"/><stop offset="1" stop-color="#fff6dc" stop-opacity="0"/></radialGradient>
</defs>
<rect x="0" y="0" width="{W}" height="144" fill="url(#sky)"/>
{light}
<path d="{ranges}" fill="{c["ranges"]}"/>
<path d="{ranges2}" fill="{c["ranges2"]}"/>
<rect x="0" y="140" width="{W}" height="50" fill="url(#sea)"/>
{waves(146, 176, c["wave"], c["wave_op"], 3)}
<path d="{beach}" fill="url(#sand)"/>
<path d="{surf}" stroke="{c["foam"]}" stroke-width="3" fill="none" opacity="{c["foam_op"]}"/>
{rock_els}
<path d="{dune}" fill="{c["dune"]}"/>
{toetoe(1000, 204, 105, 7, c["stem"], c["plume"])}
{toetoe(720, 212, 80, 8, c["stem"], c["plume"])}
{flax(860, 204, 0.55, c["flax"], 1, 2, c["flower"], c["stalk"])}
{flax(1060, 212, 0.38, c["flax"], 2, 1, c["flower"], c["stalk"])}
<rect x="0" y="214" width="{W}" height="46" fill="url(#fade)"/>
</svg>
'''


day = dict(page="#f2ede4", sky="#d9e7e8", dune="#e4d3b2",
           sea_far="#9cc6c8", sea_near="#3f8f9b", wave="#ffffff", wave_op=0.35,
           ranges="#c3d3d6", ranges2="#b3c6ca", foam="#ffffff", foam_op=0.8,
           sand_top="#eadcc0", sand_bottom="#dcc6a0", rock="#7d7a70",
           flax=["#56733f", "#4a6636", "#6a8a4c", "#3f5a2f"], flower="#9a3426", stalk="#6b543a",
           stem="#a89a78", plume="#efe6cf")
night = dict(page="#0b1620", sky="#17304a", dune="#262723",
             sea_far="#17344a", sea_near="#0f2636", wave="#9fc3d4", wave_op=0.18,
             ranges="#1a3045", ranges2="#20384e", foam="#a9c7d3", foam_op=0.35,
             sand_top="#2b2b29", sand_bottom="#222321", rock="#171a1c",
             flax=["#1d3324", "#182b1f", "#22392a", "#14241a"], flower="#5a2620", stalk="#2b2a22",
             stem="#3d3b33", plume="#5f5b4e", moon="#e8eef0")

if __name__ == "__main__":
    for name, colours, is_night in [("coast-day.svg", day, False), ("coast-night.svg", night, True)]:
        with open(os.path.join(OUT, name), "w", newline="\n") as f:
            f.write(scene(colours, is_night))
