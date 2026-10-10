#!/usr/bin/env python3
"""Build every SVG asset of the nualt organisation README, in the nualt palette.

    python3 scripts/build.py

Type system: Outfit 300 for titles (OFL, free to embed), close to the Yellix of the site,
Inter 400 for body, Geist Pixel for labels. Never bold. Blue on ivory, square corners, 1px lines.
Fonts are embedded per card, only the faces the card uses, files untouched.
Repo cards read their facts from GitHub (`gh` authenticated locally, or GH_TOKEN on CI) and npm.
"""
import datetime, html, json, re, subprocess, urllib.request

BLUE, IVORY, MUTED = "#0755B5", "#F4F2E8", "#326DAA"    # --foreground, --background, --foreground-muted
BG, FG, LINE = IVORY, BLUE, BLUE
W, HALF = 1000, 490                          # full README column, and a cell of a two column table

FONTS = json.load(open("scripts/fonts.json"))
FACES = {"outfit": ("Outfit", 300), "inter400": ("Inter", 400), "pixel": ("Geist Pixel", 400),
         "mono": ("Geist Mono", 400)}
TITLE = "Outfit,Helvetica,Arial,sans-serif"
BODY = "Inter,Helvetica,Arial,sans-serif"
PIXEL = "'Geist Pixel',ui-monospace,Menlo,monospace"
MONO = "'Geist Mono',ui-monospace,Menlo,monospace"
STYLE = {"title": (TITLE, 300, 0.52, "outfit"),     # family, weight, average advance (em), face key
         "body": (BODY, 400, 0.50, "inter400"),
         "label": (PIXEL, 400, 0.60, "pixel"),      # subheads, facts, dates
         "code": (MONO, 400, 0.60, "mono")}         # install commands
H1, H2, H3, TXT, LBL = 44, 32, 24, 16, 14            # the whole scale. Titles: Outfit. Text: Inter.

HEADLINE = ["Creative web development",
            "Open-source tools",
            "Small digital systems with a point of view"]
# Real width of each line at 44px, measured in Chrome with getComputedTextLength() on the
# embedded font. A line missing here falls back to the estimate and sits slightly off-centre.
HEADLINE_PX = {"Creative web development": 522,
               "Open-source tools": 359,
               "Small digital systems with a point of view": 783}

ABOUT = {
    "name": "nualt studio",
    "role": "A tiny creative web studio. Websites, storefronts, interfaces and open-source tools.",
    "body": [
        "We build websites, interfaces, plugins and web experiments for people who care about how "
        "things look, feel and work.",
        "",
        "Not “clean digital solutions”. Not “innovative ecosystems”. Just sharp websites, "
        "useful tools and code that does what it says.",
        "",
        "We like projects with a strong angle. The kind that need design, code, taste and a bit of "
        "stubbornness.",
    ],
    "list_title": "We work somewhere between",
    "list": ["web design and development",
             "creative direction and product thinking",
             "open-source tooling",
             "e-commerce infrastructure",
             "weirdly serious opinions about typography, hosting and the European web"],
}

BUILD = [
    ("Websites", "Fast, sharp, editorial websites for brands, studios, shops, artists and small teams."),
    ("E-commerce", "Custom storefronts, product experiences and commerce systems using modern tools "
                   "instead of bloated defaults."),
    ("Open-source plugins", "Small, useful packages for developers who would rather ship than spend "
                            "three days reading broken docs."),
    ("Creative systems", "Interfaces, visual languages, workflows and little digital machines that "
                         "make a project easier to run."),
]

FOCUS = ["Next.js applications",
         "Medusa plugins",
         "Better Auth integrations",
         "Payload CMS",
         "creative tooling for small businesses",
         "making web development feel less like filling a tax form underwater"]

# The four repositories featured on nualt.fr, with their icons (featured-repositories.ts).
REPOS = [
    {"name": "medusa-plugin-better-auth", "url": "https://github.com/nualt/medusa-plugin-better-auth",
     "desc": "Better Auth wired into Medusa v2 for modern, flexible authentication. Published on npm.",
     "icon": "betterauth-inverse-isometrique", "npm": "@nualt/medusa-plugin-better-auth"},
    {"name": "agent-memory-starter", "url": "https://github.com/nualt/agent-memory-starter",
     "desc": "Templates and writing conventions for a company knowledge base that AI agents can "
             "actually retrieve. Works with Cognee or any memory engine.",
     "icon": "memoire-isometrique"},
    {"name": "responsive-motion", "url": "https://github.com/nualt/responsive-motion",
     "desc": "Claude Code skill: scroll choreographies that degrade cleanly on every device.",
     "icon": "appareils-isometriques"},
    {"name": "nextjs-theme-toggle", "url": "https://github.com/nualt/nextjs-theme-toggle",
     "desc": "Dev-only theme toggle for Next.js. Switch light and dark mode with one key while building.",
     "icon": "interrupteur-isometrique", "npm": "nualt-theme-toggle"},
]

OSS = ["We publish tools when they solve a real problem. Not everything needs to become a product. "
       "Sometimes the best thing you can do is release the annoying little piece of code you wish "
       "already existed.",
       "",
       "If one of our packages saves you time, rage or a small existential crisis, you can support "
       "the studio with a coffee."]

CLOSING = "Made by nualt. Small studio. Sharp web. No corporate fog machine."

SECTIONS = [("about", "About"), ("build", "What we build"), ("focus", "Current focus"),
            ("open-source", "Open source"), ("stack", "Stack"), ("contact", "Work with us")]

# (label, url, icon file in assets/icons, or None). A missing icon file renders the label alone.
LINKS = [("bonjour@nualt.fr", "mailto:bonjour@nualt.fr", "mail"),
         ("nualt.fr", "https://nualt.fr", "site"),
         ("Instagram", "https://www.instagram.com/nualtstudio/", "instagram"),
         ("Buy me a coffee", "https://www.buymeacoffee.com/nualt_studio", "coffee")]

ICONS = ["typescript (1)", "javascript", "python (1)", "html-light", "css-light", "tailwind",
         "nextjs-light (1)", "expo-dark", "medusa-light (1)", "payloadcms-dark (1)", "vercel-light",
         "digital-ocean (1)", "dify"]
ICONS_CREAM = {"medusa-light (1)", "dify"}   # drawn with no fill of their own: painted FG
ICONS_WHITE = {"expo-dark", "medusa-light (1)", "payloadcms-dark (1)", "vercel-light"}  # white logos: black on ivory

# --------------------------------------------------------------------------- helpers
def esc(s):
    return html.escape(str(s), quote=False)

def text(x, y, s, size, style="body", fill=FG, anchor="start"):
    fam, weight, _, _ = STYLE[style]
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-family="{fam}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{esc(s)}</text>')

def width(s, size, style="body"):
    return len(s) * size * STYLE[style][2]

def wrap(s, width_px, size, style="body"):
    n = max(1, int(width_px / (size * STYLE[style][2])))
    lines, cur = [], ""
    for word in s.split():
        if len(cur) + len(word) + (1 if cur else 0) <= n:
            cur = f"{cur} {word}".strip()
        else:
            lines.append(cur); cur = word
    return lines + ([cur] if cur else [])

def paragraphs(paras, width_px, size):
    out = []
    for p in paras:
        out += wrap(p, width_px, size) if p else [""]
    return out

def faces(*styles):
    """@font-face rules for the given styles only, so each card carries just what it uses."""
    keys = sorted({STYLE[s][3] for s in styles})
    rules = "".join(f"@font-face{{font-family:'{FACES[k][0]}';font-style:normal;font-weight:{FACES[k][1]};"
                    f"src:url(data:font/woff2;base64,{FONTS[k]['b64']}) format('woff2');}}" for k in keys)
    return f"<style>{rules}</style>"

def card(w, h, label, styles=(), radius=0, fill=BG, stroke=None):
    s = f' stroke="{stroke}"' if stroke else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">'
            f'{faces(*styles) if styles else ""}'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{radius}" fill="{fill}"{s}/>')

def write(path, parts):
    open(path, "w").write("".join(parts) + "</svg>")

def inline_svg(path, i, cream=False, recolor=False):
    """(viewBox, inner markup, root fill) of an svg file, ids namespaced so several can share a document."""
    s = open(path).read()
    s = re.sub(r"<\?xml.*?\?>|<!DOCTYPE[^>]*>", "", s, flags=re.S)
    m = re.search(r"<svg([^>]*)>(.*)</svg>", s, re.S)
    attrs, inner = m.group(1), m.group(2)
    vb = re.search(r'viewBox="([^"]+)"', attrs)
    vb = vb.group(1) if vb else "0 0 %s %s" % (re.search(r'width="([\d.]+)"', attrs).group(1),
                                               re.search(r'height="([\d.]+)"', attrs).group(1))
    rf = re.search(r'fill="([^"]+)"', attrs)     # expo and payload carry their colour on the root tag
    fill = rf.group(1) if rf else (FG if cream else None)
    if recolor:                                  # monochrome icons drawn in black: paint them cream
        inner = re.sub(r'(fill|stroke)="(#000000|#000|black)"', lambda m: f'{m.group(1)}="{FG}"', inner)
    p = f"n{i}_"
    for pat, rep in ((r'id="([^"]+)"', lambda m: f'id="{p}{m.group(1)}"'),
                     (r"url\(#([^)]+)\)", lambda m: f"url(#{p}{m.group(1)})"),
                     (r'(xlink:href|href)="#([^"]+)"', lambda m: f'{m.group(1)}="#{p}{m.group(2)}"'),
                     (r"\.st(\d+)", lambda m: f".{p}st{m.group(1)}"),
                     (r'class="st(\d+)"', lambda m: f'class="{p}st{m.group(1)}"')):
        inner = re.sub(pat, rep, inner)
    return vb, inner, fill

def logo(x, y, w, color):
    """public/logo/nualt.svg (249 × 75) of the site, in one colour."""
    vb, inner, _ = inline_svg("assets/logo.svg", "logo")
    inner = inner.replace("fill:rgb(7,85,181)", f"fill:{color}")
    return f'<svg x="{x}" y="{y}" width="{w}" height="{w * 75 / 249:.1f}" viewBox="{vb}">{inner}</svg>'

# Block rows of the site footer (TetrisBorder): each block fills 95 % of its cell, ivory on blue.
BLOCKS = ["110001110011000111", "100111100010110001", "111001001110011100"]

def blocks(y, cols, cell, rows=BLOCKS):
    out = []
    for r, row in enumerate(rows):
        row = (row * 3)[:cols]
        for c, on in enumerate(row):
            if on == "1":
                out.append(f'<rect x="{c * cell + cell * 0.025:.1f}" y="{y + r * cell + cell * 0.025:.1f}" '
                           f'width="{cell * 0.95:.1f}" height="{cell * 0.95:.1f}" fill="{IVORY}"/>')
    return "".join(out)

def bullets(out, items, x, y, width_px, lead=26):
    """A list with a small cream square as marker. Returns the y after the last line."""
    for item in items:
        for j, line in enumerate(wrap(item, width_px - 22, TXT)):
            if j == 0:
                out.append(f'<rect x="{x}" y="{y - 9}" width="6" height="6" fill="{FG}"/>')
            out.append(text(x + 22, y, line, TXT, "body"))
            y += lead
    return y

# ------------------------------------------------------------------ header / footer
def build_header(path="assets/header.svg", cell=40, PAD=48, LOGO=360):
    w = W + 200
    H = 3 * cell + 2 * PAD + LOGO * 75 / 249
    write(path, [card(w, H, "nualt", fill=BLUE),
                 blocks(0, w // cell, cell),
                 logo(PAD, H - PAD - LOGO * 75 / 249, LOGO, IVORY)])

def build_footer(path="assets/footer.svg", cell=40):
    write(path, [card(W + 200, 3 * cell, "", fill=BLUE),
                 blocks(0, (W + 200) // cell, cell, BLOCKS[::-1])])

# --------------------------------------------------------------------------- headline
def build_headline(path="assets/headline.svg", size=H1, slot=4000):
    """Typewriter, h1 of the page. A growing <path> that the text rides with <textPath>: the glyphs
    that fit on the path are drawn. Same mechanism as readme-typing-svg, it runs inside an <img>."""
    H = 120
    out = [card(W, H, HEADLINE[0], styles=("title",))]
    last = f"d{len(HEADLINE) - 1}"
    for i, line in enumerate(HEADLINE):
        real = HEADLINE_PX.get(line, width(line, size, "title") * 1.08) * size / 44
        tw = real * 1.04                                # a little slack so the last glyph always lands
        x0, y = (W - real) / 2, H / 2 + size * 0.34
        begin = f"0s;{last}.end" if i == 0 else f"d{i - 1}.end"
        out.append(f"<path id='p{i}'><animate id='d{i}' attributeName='d' begin='{begin}' dur='{slot}ms' "
                   f"fill='remove' keyTimes='0;0.45;0.85;1' values='m{x0:.1f},{y:.1f} h0 ; "
                   f"m{x0:.1f},{y:.1f} h{tw:.1f} ; m{x0:.1f},{y:.1f} h{tw:.1f} ; m{x0:.1f},{y:.1f} h0'/></path>"
                   f"<text font-family=\"{TITLE}\" font-weight='300' font-size='{size}' fill='{FG}'>"
                   f"<textPath xlink:href='#p{i}'>{esc(line)}</textPath></text>")
    write(path, out)

# ------------------------------------------------------------------- section titles
def build_titles(H=72, PAD=24):
    for slug, label in SECTIONS:
        write(f"assets/title-{slug}.svg",
              [card(W, H, label, styles=("title",)),
               text(PAD, H - 24, label, H2, "title"),
               f'<rect x="0" y="{H - 1}" width="{W}" height="1" fill="{LINE}"/>'])

# ------------------------------------------------------------------------------ about
def build_about(path="assets/about.svg", PAD=30):
    lead = 26
    body = paragraphs(ABOUT["body"], W - 2 * PAD - 60, TXT)
    top = PAD + 18
    y0 = top + 60
    rule = y0 + len(body) * lead - 8
    out = [card(W, 10, "about", styles=("title", "body")),   # height patched below
           text(PAD, top, ABOUT["name"], H3, "title"),
           text(PAD, top + 26, ABOUT["role"], TXT, "body", MUTED)]
    y = y0
    for line in body:
        if line:
            out.append(text(PAD, y, line, TXT, "body"))
        y += lead
    out.append(f'<rect x="{PAD}" y="{rule}" width="{W - 2 * PAD}" height="1" fill="{LINE}"/>')
    out.append(text(PAD, rule + 34, ABOUT["list_title"], TXT, "body", MUTED))
    y = bullets(out, ABOUT["list"], PAD, rule + 64, W - 2 * PAD - 60)
    H = y - lead + PAD + 4
    out[0] = card(W, H, "about", styles=("title", "body"))
    write(path, out)

# ------------------------------------------------------------------- what we build
def build_build_cards(PAD=24):
    lines = [wrap(desc, HALF - 2 * PAD, TXT) for _, desc in BUILD]
    n = max(len(l) for l in lines)                       # same height across the grid
    H = PAD + 16 + 34 + n * 24 + PAD - 6
    for i, ((title, _), ls) in enumerate(zip(BUILD, lines)):
        out = [card(HALF, H, title, styles=("title", "body"), stroke=LINE),
               text(PAD, PAD + 16, title, H3, "title")]
        y = PAD + 50
        for line in ls:
            out.append(text(PAD, y, line, TXT, "body", MUTED)); y += 24
        write(f"assets/build-{i}.svg", out)

# ------------------------------------------------------------------------------ focus
def build_focus(path="assets/focus.svg", PAD=30):
    out = [card(W, 10, "current focus", styles=("body",))]
    y = bullets(out, FOCUS, PAD, PAD + 20, W - 2 * PAD - 60, lead=28)
    H = y - 28 + PAD + 6
    out[0] = card(W, H, "current focus", styles=("body",))
    write(path, out)

# ------------------------------------------------------------------------ open source
def repo_facts(r):
    """Topics, install command and facts (npm version, last push, licence), as nualt.fr/open-source shows them."""
    slug = r["url"].split("github.com/")[1]
    g = json.loads(subprocess.run(["gh", "api", f"repos/{slug}"], capture_output=True, text=True, check=True).stdout)
    version = None
    if r.get("npm"):
        with urllib.request.urlopen(f"https://registry.npmjs.org/{r['npm']}/latest") as res:
            version = json.load(res).get("version")
    topics = g.get("topics", [])
    if r.get("npm"):
        command = f"npm i {r['npm']}"
    elif {"claude-code-plugin", "agent-skills"} & set(topics):
        command = f"npx skills add {slug}"
    else:
        command = f"gh repo clone {slug}"
    pushed = datetime.date.fromisoformat(g["pushed_at"][:10])
    licence = (g.get("license") or {}).get("spdx_id")
    facts = [f"v{version}" if version else None, f"{pushed:%b} {pushed.day}, {pushed.year}",
             licence if licence != "NOASSERTION" else None]
    return topics, command, [f for f in facts if f]

def iso_icon(name, x, y, size):
    """Isometric icon of the site, original variant: ivory faces, blue lines and hatching."""
    vb, inner, _ = inline_svg(f"assets/iso/nualt-{name}.svg", name)
    inner = inner.replace("var(--blue)", IVORY).replace("currentColor", BLUE)
    hatch = 0.25 if "betterauth" in name else 0.5
    return (f'<style>pattern path{{stroke-width:{hatch}}}</style>'
            f'<svg x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" viewBox="{vb}" fill="none" '
            f'stroke-linejoin="round" stroke-linecap="round" overflow="visible">{inner}</svg>')

def build_repo_cards(PAD=24, THUMB=128, ICON=88, CMD=48, DESC=15, LEAD=22):
    """Card of the open-source catalogue: icon cell on the left, topics, name, description, facts,
    then the install command in its own cell across the card."""
    x0 = THUMB + PAD
    tw = HALF - x0 - PAD
    rows = max(len(wrap(r["desc"], tw, DESC)) for r in REPOS)   # same height across the grid
    name_y = PAD + 50
    desc_y = name_y + 34
    facts_y = desc_y + (rows - 1) * LEAD + 40
    box = facts_y + PAD
    H = box + CMD
    for r in REPOS:
        topics, command, facts = repo_facts(r)
        shown = []
        for t in topics:                                         # as many topics as fit on one line
            if width(" · ".join(shown + [t]), LBL, "label") > tw:
                break
            shown.append(t)
        out = [card(HALF, H, r["name"], styles=("title", "body", "label", "code"), stroke=LINE),
               f'<rect x="{THUMB}" y="0" width="1" height="{box}" fill="{LINE}"/>',
               f'<rect x="0" y="{box}" width="{HALF}" height="1" fill="{LINE}"/>',
               iso_icon(r["icon"], (THUMB - ICON) / 2, (box - ICON) / 2, ICON),
               text(x0, PAD + 14, " · ".join(shown), LBL, "label"),
               text(x0, name_y, r["name"], H3, "title")]
        y = desc_y
        for line in wrap(r["desc"], tw, DESC):
            out.append(text(x0, y, line, DESC, "body")); y += LEAD
        x = x0
        for f in facts:
            out.append(text(x, facts_y, f, LBL, "label", MUTED))
            x += width(f, LBL, "label") + 16
        out.append(text(16, box + CMD / 2 + 5, command, LBL, "code"))
        write(f"assets/repo-{r['name']}.svg", out)

def build_oss(path="assets/oss.svg", PAD=30):
    lines = paragraphs(OSS, W - 2 * PAD - 60, TXT)
    H = PAD + 20 + len(lines) * 26 + PAD - 12
    out = [card(W, H, "open source", styles=("body",))]
    y = PAD + 20
    for line in lines:
        if line:
            out.append(text(PAD, y, line, TXT, "body"))
        y += 26
    write(path, out)

def build_closing(path="assets/closing.svg", H=68):
    write(path, [card(W, H, CLOSING, styles=("body",)),
                 text(W / 2, H / 2 + 6, CLOSING, TXT, "body", MUTED, "middle")])

# ------------------------------------------------------------------------------ links
def build_links(H=68, gap=14, icon=20):
    import os
    w = (W - (len(LINKS) - 1) * gap) / len(LINKS)
    for i, (label, url, name) in enumerate(LINKS):
        path = f"assets/icons/{name}.svg"
        out = [card(round(w), H, label, styles=("body",), stroke=LINE)]
        if name and os.path.exists(path):
            vb, inner, fill = inline_svg(path, 50 + i, cream=True, recolor=True)
            tw = width(label, TXT)
            x0 = (w - tw - icon - 12) / 2                # icon + gap + label, centred as a group
            out += [f'<svg x="{x0:.1f}" y="{(H - icon) / 2:.1f}" width="{icon}" height="{icon}" viewBox="{vb}" '
                    f'preserveAspectRatio="xMidYMid meet" fill="{fill or FG}" overflow="visible">{inner}</svg>',
                    text(x0 + icon + 12, H / 2 + 6, label, TXT, "body", FG)]
        else:
            out.append(text(w / 2, H / 2 + 6, label, TXT, "body", FG, "middle"))
        write(f"assets/link-{i}.svg", out)

# ------------------------------------------------------------------------------ stack
def build_stack(path="assets/stack.svg", tile=64, gap=14):
    n = len(ICONS)
    size = round(tile * 0.62)
    x0 = (W - (n * tile + (n - 1) * gap)) / 2
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{W}" height="{tile}" viewBox="0 0 {W} {tile}" role="img" aria-label="stack">']
    for i, name in enumerate(ICONS):
        vb, inner, fill = inline_svg(f"assets/icons/{name}.svg", i, name in ICONS_CREAM)
        if name in ICONS_WHITE:
            inner = re.sub(r"#fff(fff)?\b", "#000000", inner, flags=re.I)
            fill = "#000000" if fill and fill.lower() in ("#fff", "#ffffff") else fill
        x = x0 + i * (tile + gap)
        f = f' fill="{fill}"' if fill else ""
        out.append(f'<rect x="{x:.1f}" y="0" width="{tile}" height="{tile}" fill="{BG}" stroke="{LINE}"/>'
                   f'<svg x="{x + (tile - size) / 2:.1f}" y="{(tile - size) / 2:.1f}" width="{size}" '
                   f'height="{size}" viewBox="{vb}" preserveAspectRatio="xMidYMid meet"{f} '
                   f'overflow="visible">{inner}</svg>')
    write(path, out)

if __name__ == "__main__":
    build_header(); build_footer(); build_headline(); build_titles(); build_about()
    build_build_cards(); build_focus(); build_repo_cards(); build_oss(); build_closing()
    build_links(); build_stack()
    print("assets built")
