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


# Wildlife. Each appearance is one short SMIL animation that restarts itself
# after a long pause (begin="<first>s; <id>.end+<gap>s"), and everything else
# in it follows that animation's begin. Between appearances nothing animates,
# so the iPad has nothing to redraw. The gaps are unequal, so the visits don't
# fall into a pattern.

def every(aid, first, gap):
    return f"{first}s; {aid}.end+{gap}s"


def timer(aid, dur, first, gap):
    """An invisible animation that sets the rhythm the others follow."""
    return (f'<rect width="0" height="0"><animate id="{aid}" attributeName="x" from="0" to="0" '
            f'dur="{dur}s" begin="{every(aid, first, gap)}"/></rect>')


def splash(x, y, begin, size, foam):
    return (f'<ellipse cx="{x}" cy="{y}" rx="0" ry="0" fill="none" stroke="{foam}" stroke-width="1.5" opacity="0">'
            f'<animate attributeName="rx" values="2;{size}" dur="0.7s" begin="{begin}"/>'
            f'<animate attributeName="ry" values="1;{size / 3:.1f}" dur="0.7s" begin="{begin}"/>'
            f'<animate attributeName="opacity" values="0.9;0" dur="0.7s" begin="{begin}"/></ellipse>')


DOLPHIN = ("M-22,3 C-14,-5 4,-9 15,-3 C18,-2 21,-1 24,0 C21,1 18,1.5 16,2 C9,6 -6,7 -15,4 "
           "L-21,9 L-19,3.5 Z M-3,-6 C-1,-11 1,-13 4,-13 C3,-10 3,-8 5,-5 Z M2,3 L-2,8 L5,4 Z")


def dolphins(aid, x, water, first, gap, colour, foam, pod=3, scale=1.1):
    """A pod leaping out of the water one after the other, left to right."""
    leap, lag = 1.5, 0.45
    out = [f'<clipPath id="{aid}-sea"><rect x="{x - 60}" y="{water - 90}" width="{120 + 40 * pod + 80}" height="90"/></clipPath>',
           timer(aid, leap + lag * (pod - 1), first, gap)]
    for k in range(pod):
        b = f"{aid}.begin+{lag * k:.2f}s"
        x0 = x + 40 * k
        out.append(f'<g clip-path="url(#{aid}-sea)"><path d="{DOLPHIN}" fill="{colour}" opacity="0" transform="scale({scale})">'
                   f'<animateMotion dur="{leap}s" begin="{b}" rotate="auto" fill="freeze" '
                   f'path="M{x0},{water + 12} Q{x0 + 42},{water - 46} {x0 + 84},{water + 12}"/>'
                   f'<set attributeName="opacity" to="1" dur="{leap}s" begin="{b}"/></path></g>')
        out.append(splash(x0 + 6, water, b, 9, foam))
        out.append(splash(x0 + 78, water, f"{aid}.begin+{lag * k + leap - 0.3:.2f}s", 11, foam))
    return "\n".join(out)


FLUKE = ("M0,0 C-1,-6 -2,-10 -3,-13 C-8,-14 -13,-13 -16,-15 C-11,-18 -5,-17 0,-15 "
         "C5,-17 11,-18 16,-15 C13,-13 8,-14 3,-13 C2,-10 1,-6 0,0 Z")
WHALE = ("M-34,2 C-26,-7 10,-10 28,-4 C32,-3 35,-1 35,1 C26,5 0,7 -24,5 L-34,10 L-37,3 Z "
         "M2,2 L-9,15 L9,4 Z")


def whale_dive(aid, x, water, first, gap, colour, foam):
    """A humpback blows, shows its back, then lifts its tail and dives."""
    out = [f'<clipPath id="{aid}-sea"><rect x="{x - 40}" y="{water - 60}" width="100" height="60"/></clipPath>',
           timer(aid, 8, first, gap)]
    # The blow: a puff of mist that rises and drifts away.
    out.append(f'<ellipse cx="{x}" cy="{water - 6}" rx="2.5" ry="2" fill="{foam}" opacity="0">'
               f'<animate attributeName="ry" values="2;9;11" dur="2.6s" begin="{aid}.begin"/>'
               f'<animate attributeName="cy" values="{water - 4};{water - 11};{water - 14}" dur="2.6s" begin="{aid}.begin"/>'
               f'<animate attributeName="opacity" values="0;0.85;0" dur="2.6s" begin="{aid}.begin"/></ellipse>')
    out.append(f'<g clip-path="url(#{aid}-sea)">'
               f'<ellipse cx="{x + 6}" cy="{water + 8}" rx="15" ry="5" fill="{colour}">'
               f'<animate attributeName="cy" values="{water + 8};{water};{water + 8}" dur="3s" begin="{aid}.begin+0.4s"/></ellipse>'
               f'<path d="{FLUKE}" fill="{colour}" transform="translate({x + 18},{water + 22}) scale(0.9)">'
               f'<animateTransform attributeName="transform" type="translate" values="{x + 18},{water + 22};{x + 18},{water + 1};{x + 18},{water + 1};{x + 18},{water + 24}" '
               f'keyTimes="0;0.4;0.6;1" dur="3.4s" begin="{aid}.begin+4.2s"/>'
               f'<animateTransform attributeName="transform" type="scale" values="0.9" additive="sum" dur="3.4s" begin="{aid}.begin+4.2s"/></path></g>')
    out.append(splash(x + 18, water, f"{aid}.begin+7.1s", 8, foam))
    return "\n".join(out)


def whale_breach(aid, x, water, first, gap, colour, foam):
    """Now and then a humpback breaches: up out of the water and back down on its side."""
    out = [f'<clipPath id="{aid}-sea"><rect x="{x - 80}" y="{water - 90}" width="200" height="90"/></clipPath>',
           timer(aid, 2.8, first, gap),
           f'<g clip-path="url(#{aid}-sea)"><path d="{WHALE}" fill="{colour}" opacity="0" transform="translate({x},{water + 40})">'
           f'<animateTransform attributeName="transform" type="translate" values="{x},{water + 40};{x + 10},{water - 26};{x + 22},{water + 40}" '
           f'keyTimes="0;0.45;1" calcMode="spline" keySplines="0.2 0.6 0.4 1;0.6 0 0.8 0.4" dur="2.8s" begin="{aid}.begin"/>'
           f'<animateTransform attributeName="transform" type="rotate" values="-75;-40;25" additive="sum" dur="2.8s" begin="{aid}.begin"/>'
           f'<set attributeName="opacity" to="1" dur="2.8s" begin="{aid}.begin"/></path></g>',
           splash(x, water, f"{aid}.begin+0.1s", 14, foam),
           splash(x + 22, water, f"{aid}.begin+2.3s", 24, foam),
           splash(x + 22, water, f"{aid}.begin+2.5s", 16, foam)]
    return "\n".join(out)


def legs(aid, run, colour, width, top, swing=28, step=0.36):
    reps = int(run / step)
    out = []
    for phase in (1, -1):
        out.append(f'<path d="M0,{top} L0,0 L-3,0" stroke="{colour}" stroke-width="{width}" fill="none" stroke-linecap="round">'
                   f'<animateTransform attributeName="transform" type="rotate" '
                   f'values="{swing * phase} 0 {top};{-swing * phase} 0 {top};{swing * phase} 0 {top}" '
                   f'dur="{step}s" repeatCount="{reps}" begin="{aid}.begin"/></path>')
    return "".join(out)


def pukeko(aid, y, first, gap):
    """A pukeko strutting along the beach, right to left, behind the flax."""
    run = 14
    return "\n".join([
        timer(aid, run, first, gap),
        f'<g transform="translate(1700,{y})">'
        f'<animateTransform attributeName="transform" type="translate" values="1700,{y};-60,{y}" dur="{run}s" begin="{aid}.begin" fill="freeze"/>'
        f'<g transform="scale(1.8)">'
        + legs(aid, run, "#d9502a", 1.6, -7) +
        '<ellipse cx="2" cy="-13" rx="9" ry="6.5" fill="#25367c"/>'
        '<path d="M8,-15 C12,-15 13,-12 11,-11 C9,-11 8,-12 7,-12 Z" fill="#f4f1ea"/>'
        f'<g><animateTransform attributeName="transform" type="translate" values="0,0;-2,1;0,0" dur="0.36s" repeatCount="{int(run / 0.36)}" begin="{aid}.begin"/>'
        '<path d="M-4,-16 C-7,-20 -8,-24 -6,-27 C-4,-29 -1,-28 -1,-25 C-1,-22 0,-19 0,-16 Z" fill="#25367c"/>'
        '<path d="M-6.5,-27 L-12,-24 L-6,-23.5 Z" fill="#d42a1d"/>'
        '<path d="M-6.5,-27 C-7.5,-30 -5.5,-31 -4.5,-29 Z" fill="#d42a1d"/>'
        '<circle cx="-4" cy="-26" r="0.7" fill="#111"/></g>'
        '</g></g>'])


def kiwi(aid, y, first, gap, colour):
    """A kiwi out foraging at night: it scurries in, stops to probe the sand, and goes."""
    run = 16
    return "\n".join([
        timer(aid, run, first, gap),
        f'<g transform="translate(-40,{y})">'
        f'<animateTransform attributeName="transform" type="translate" values="-40,{y};620,{y};620,{y};1680,{y}" '
        f'keyTimes="0;0.35;0.55;1" dur="{run}s" begin="{aid}.begin" fill="freeze"/>'
        + '<g transform="scale(1.7)">' + legs(aid, run, "#8a7a62", 2, -4, swing=22, step=0.22) +
        f'<g><animateTransform attributeName="transform" type="rotate" values="0 0 -6;0 0 -6;24 0 -6;4 0 -6;26 0 -6;0 0 -6;0 0 -6" '
        f'keyTimes="0;0.36;0.41;0.45;0.5;0.54;1" dur="{run}s" begin="{aid}.begin"/>'
        f'<ellipse cx="0" cy="-9" rx="9" ry="7" fill="{colour}"/>'
        f'<circle cx="7.5" cy="-12" r="3.6" fill="{colour}"/>'
        f'<path d="M10.5,-12.5 Q16,-10 20,-5" stroke="#9c8f74" stroke-width="1.3" fill="none" stroke-linecap="round"/>'
        '</g></g></g>'])


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
    # Dolphins every 1.5-2 minutes, a whale every 3-4, a breach every ~7, and
    # a pukeko (by day) or a kiwi (at night, as they are) every 2-3. Each
    # shows up once soon after the page loads, so a reload shows them off.
    sea_life = "\n".join([
        dolphins("pod1", 300, 164, 6, 97, c["dolphin"], c["foam"]),
        dolphins("pod2", 1060, 160, 52, 131, c["dolphin"], c["foam"], pod=2, scale=0.9),
        whale_dive("blow", 1395, 150, 24, 203, c["whale"], c["foam"]),
        whale_breach("breach", 520, 154, 75, 421, c["whale"], c["foam"]),
    ])
    land_life = kiwi("kiwi", 207, 14, 163, c["kiwi"]) if night else pukeko("pukeko", 207, 14, 151)
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
{sea_life}
<path d="{beach}" fill="url(#sand)"/>
<path d="{surf}" stroke="{c["foam"]}" stroke-width="3" fill="none" opacity="{c["foam_op"]}"/>
{rock_els}
<path d="{dune}" fill="{c["dune"]}"/>
{land_life}
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
           stem="#a89a78", plume="#efe6cf",
           dolphin="#4f646d", whale="#38464e")
night = dict(page="#0b1620", sky="#17304a", dune="#262723",
             sea_far="#17344a", sea_near="#0f2636", wave="#9fc3d4", wave_op=0.18,
             ranges="#1a3045", ranges2="#20384e", foam="#a9c7d3", foam_op=0.35,
             sand_top="#2b2b29", sand_bottom="#222321", rock="#171a1c",
             flax=["#1d3324", "#182b1f", "#22392a", "#14241a"], flower="#5a2620", stalk="#2b2a22",
             stem="#3d3b33", plume="#5f5b4e", moon="#e8eef0",
             dolphin="#3e5c72", whale="#2e475b", kiwi="#5a4b38")

if __name__ == "__main__":
    for name, colours, is_night in [("coast-day.svg", day, False), ("coast-night.svg", night, True)]:
        with open(os.path.join(OUT, name), "w", newline="\n") as f:
            f.write(scene(colours, is_night))
