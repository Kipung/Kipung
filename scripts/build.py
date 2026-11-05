"""Render the profile artwork, and the banners for the featured repos, from the data below.

The profile is a stack of dark product cards (near-black fill, hairline border, rounded
corners, accent chips) with the demo GIFs placed up front in the README. GitHub shows
SVGs as images, so only system fonts render, motion is CSS inside the file, and
photographs are embedded as data URIs (sources in assets/src/).

    python3 scripts/build.py      # writes assets/*.svg and dist/repos/<repo>/.github/*.svg
Needs ffmpeg for resizing the embedded photographs.
"""

import base64
import itertools
import subprocess
import textwrap
from datetime import date
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
SRC = OUT / "src"
REPO_OUT = ROOT / "dist" / "repos"

BG, BORDER, INK, DIM, ACCENT = "#0a0a0a", "#ffffff1a", "#ededed", "#a1a1a1", "#7c9bff"
PANEL, GRID, GREEN, GRAY = "#111111", "#ffffff12", "#3ddc84", "#6b6b6b"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

NAME = "Kip Park"
FULL_NAME = "Ki-Pung Park"
TAGLINE = "AI researcher and engineer, focused on language models."
ABOUT = ("CS (ML & AI, ’27) at California Baptist University. I build source-verified fine-tuning "
         "pipelines, run controlled LLM experiments, and ship local-first AI tools that people actually use.")
TODAY = date.today()
# The hero shows the first event that has not happened yet; past ones drop off on the
# monthly rebuild (.github/workflows/rebuild.yml). Add new ones here.
EVENTS = [
    (date(2026, 11, 21), "2 posters · SCCUR, Nov. 21"),
]
upcoming = [text for day, text in EVENTS if day >= TODAY]
FACTS = [
    ("Study", "B.S. CS, ML & AI · Apr. 2027"),
    ("Lab", "CBU AI & ML Lab (CAIMLL)"),
    ("Next", upcoming[0]) if upcoming else ("Focus", "LLM fine-tuning & evaluation"),
]

# Large project cards. image = file in assets/src, or "draw:<name>". readme False keeps
# the project for its repo banner only (Living Kanto is shown by its GIF instead).
FEATURED = [
    {"slug": "kanto", "title": "Living Kanto", "meta": "Simulation · local LLMs", "image": "kanto.jpg", "readme": False,
     "desc": "A persistent world where 100 residents, each run by a local language model, travel, work, talk and pursue their own ambitions.",
     "tags": "local LLMs · agents · persistent world state", "href": "https://github.com/kipung/living-kanto"},
    {"slug": "finetune", "title": "Domain Fine-Tuning Pipeline", "meta": "CAIMLL · lab backbone", "image": "draw:pipeline",
     "desc": "Reference documents become source-verified training data, checked for evidence coverage, answer quality and reproducibility.",
     "tags": "QLoRA · Unsloth · vLLM · GGUF · evaluation"},
    {"slug": "subliminal", "title": "Subliminal Learning in LLMs", "meta": "Study lead · under review", "image": "subliminal-teacher.jpg", "fit": "meet",
     "desc": "Can a hidden love of owls pass from teacher to student through number sequences? The teacher picked owls 53% of the time; a clean negative result: students barely moved.",
     "tags": "Llama 3.2 3B · LoRA · system prompts", "href": "https://github.com/kipung/WeHateOwls"},
    {"slug": "geoai", "title": "GeoAI: Overdose Risk Mapping", "meta": "AMCIS 2025 · coauthor", "image": "geoai.jpg",
     "desc": "A deep model predicts areas of suspected drug-overdose risk from geolocated posts; Kepler.gl maps turn its output into regional insight.",
     "tags": "deep learning · GIS · Kepler.gl", "href": "https://aisel.aisnet.org/amcis2025/intelfuture/intelfuture/27/"},
]

# Smaller cards, two per row. The first four show; the rest sit behind "More projects".
PROJECTS = [
    {"slug": "degree", "title": "AI Degree Planning Companion", "meta": "Student Success", "image": "degree.jpg", "fit": "meet",
     "desc": "An agent that plans courses over a Neo4j prerequisite graph, on local models, streamed to a React chat UI.",
     "tags": "LangChain · Neo4j · FastAPI · Ollama · React", "href": "https://github.com/kipung/degree_planning_guide"},
    {"slug": "browser", "title": "Terminal Browser Split", "meta": "Dev tool", "image": "draw:terminal",
     "desc": "A live, clickable browser preview in a native terminal split, opened by you with a hotkey or by any coding agent with one command.",
     "tags": "Ghostty · kitty · WezTerm · tmux", "href": "https://github.com/kipung/terminal-browser"},
    {"slug": "hydro", "title": "Rainfall Transfer Between Gauges", "meta": "SCCUR 2026", "image": "hydro.jpg", "fit": "meet",
     "desc": "Hourly rainfall from one gauge estimated from another across 28 years of records; held-out event hours reach R² = 0.58.",
     "tags": "Python · time series · lagged OLS"},
    {"slug": "lensing", "title": "Gravitational Lensing", "meta": "Physics research", "image": "lensing.gif",
     "desc": "A simulation of light rays bending as they pass rows of masses."},
    {"slug": "acm", "title": "CBU ACM Website", "meta": "Team project", "image": "acm.jpg",
     "desc": "Built by the Software Engineering Team I founded, with Brandon Magana and the SET crew, using Scrum and GitHub flow.",
     "tags": "HTML · CSS · JavaScript · Scrum", "href": "https://github.com/kipung/SET_PROJECT_3"},
    {"slug": "tracr", "title": "Tracr → TransformerLens", "meta": "Algoverse · 2025", "image": "tracr.jpg", "fit": "meet",
     "desc": "Compile a RASP program with Tracr, convert it to TransformerLens, check both decode alike.",
     "href": "https://github.com/kipung/tracr_to_transformer_lens_generalize"},
    {"slug": "geglu", "title": "GeGLU vs ReLU", "meta": "Experiment · MNIST", "image": "geglu.jpg", "fit": "meet",
     "desc": "Feed-forward activations compared across widths, with bootstrap confidence intervals.",
     "href": "https://github.com/kipung/ffn_relu_vs_geglu_mnist"},
    {"slug": "voice", "title": "Local Voice Assistant", "meta": "Offline · Ollama", "image": "voice.jpg", "fit": "meet",
     "desc": "Speech in, local Llama 3.2 out, spoken back; nothing leaves the machine."},
    {"slug": "baymin", "title": "BAY-min", "meta": "Reachy Mini · Gemini Live", "image": "reachy.jpg",
     "desc": "A robot math tutor that talks, watches the student’s work, and nods along.",
     "href": "https://github.com/kipung/BAY-min_personal_tutor"},
    {"slug": "campusmate", "title": "CampusMate", "meta": "Flutter · Firebase", "image": "campusmate.jpg",
     "desc": "Study groups, real-time messaging, file sharing and a group calendar for students.",
     "href": "https://github.com/kipung/campusmate"},
    {"slug": "hackathon", "title": "FunctionGemma Hackathon", "meta": "3rd place · online", "image": "hackathon.jpg", "align": "xMidYMin",
     "desc": "3rd place in the online division of the Cactus × Google DeepMind FunctionGemma Hackathon.",
     "href": "https://github.com/kipung/functiongemma-hackathon"},
]

PLATES = [
    {"slug": "room", "title": "Conferences & competitions", "photos": [
        ("amcis.jpg", "AMCIS 2025, Montréal", "Presenting our GeoAI paper", "xMidYMid"),
        ("ksea.jpg", "KSEA SWRC, CSU Fullerton", "Two research posters, Jan. 2026", "xMidYMin"),
        ("icpc.jpg", "SoCal Regional ICPC", "With the CBU team, Nov. 2024", "xMidYMid"),
    ]},
    {"slug": "bench", "title": "Robots & hardware", "photos": [
        ("so101.jpg", "SO-101 arm", "Physical AI capstone: assembly and teleoperation", "xMidYMid"),
        ("reachy.jpg", "Reachy Mini", "Assembled and demoed for visiting students", "xMidYMid"),
        ("jetson.jpg", "Jetson Orin Nano Super", "A fully local AI assistant on the edge", "xMidYMid"),
    ]},
]

# Timeline rows: (lane, label, start, end); end None = ongoing. Months as (year, month).
NOW = (TODAY.year, TODAY.month)
TIMELINE = [
    ("research", "GeoAI for public health", (2024, 3), (2025, 9)),
    ("research", "Computational physics, lensing", (2024, 5), (2025, 8)),
    ("research", "Mechanistic interpretability, Algoverse", (2025, 7), (2025, 10)),
    ("research", "Subliminal learning study (lead)", (2025, 8), None),
    ("research", "Hydrology, rainfall estimation", (2026, 1), None),
    ("research", "CAIMLL fine-tuning & evaluation", (2026, 2), None),
    ("work", "AI Engineering Intern, Student Success", (2025, 1), None),
    ("work", "AI Evaluation Intern, Portfolio Elevation", (2026, 6), (2026, 9)),
    ("lead", "President, CBU ACM", (2024, 3), (2026, 4)),
    ("lead", "Software engineering tutor", (2024, 8), None),
]
MILESTONES = [
    ((2024, 11), "ICPC"), ((2025, 8), "AMCIS"), ((2026, 1), "KSEA"), ((2026, 2), "Hackathon"), ((2026, 11), "SCCUR"),
]
LANE_COLOR = {"research": ACCENT, "work": INK, "lead": GRAY}
LANE_NAME = {"research": "Research", "work": "Work", "lead": "Leadership & teaching"}

# Banners for the featured repos: written to dist/repos/<repo>/.github/banner{,-m}.svg
REPOS = [
    {"repo": "living-kanto", "slug": "kanto"},
    {"repo": "CSC422_Subliminal_Learning", "slug": "subliminal"},
    {"repo": "WeHateOwls", "slug": "subliminal"},
    {"repo": "BAY-min_personal_tutor", "slug": "baymin", "tags": "Reachy Mini · Gemini Live · OpenCV · Firestore · BLE"},
    {"repo": "degree_planning_guide", "slug": "degree"},
    {"repo": "terminal-browser", "slug": "browser"},
    {"repo": "SET_PROJECT_3", "slug": "acm"},
    {"repo": "tracr_to_transformer_lens_generalize", "slug": "tracr", "tags": "Tracr · JAX · TransformerLens · RASP"},
    {"repo": "ffn_relu_vs_geglu_mnist", "slug": "geglu", "tags": "PyTorch Lightning · MNIST · bootstrap CIs"},
    {"repo": "campusmate", "slug": "campusmate", "tags": "Flutter · Firebase · Dart"},
]


@lru_cache(maxsize=None)
def embed(name, width):
    """A source photo resized to `width` px and returned as a JPEG data URI.

    GIFs come from assets/demos and are embedded untouched so they keep animating."""
    if name.endswith(".gif"):
        return "data:image/gif;base64," + base64.b64encode((OUT / "demos" / name).read_bytes()).decode()
    jpg = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(SRC / name), "-vf", f"scale='min({width},iw)':-2",
         "-q:v", "6", "-f", "image2", "-c:v", "mjpeg", "pipe:1"],
        check=True, capture_output=True,
    ).stdout
    return "data:image/jpeg;base64," + base64.b64encode(jpg).decode()


# ---- text and layout helpers -------------------------------------------------------

CSS = f"""<style>
  .s {{ font-family: {SANS}; }}
  .m {{ font-family: {MONO}; }}
  .ink {{ fill: {INK}; }}
  .dim {{ fill: {DIM}; }}
  .acc {{ fill: {ACCENT}; }}
  @keyframes pulse {{ 0%, 100% {{ opacity: 1 }} 50% {{ opacity: .3 }} }}
  @keyframes ping {{ 0% {{ transform: scale(1); opacity: .6 }} 100% {{ transform: scale(3); opacity: 0 }} }}
  @keyframes flow {{ to {{ stroke-dashoffset: -16 }} }}
  .ping {{ transform-box: fill-box; transform-origin: center; animation: ping 2.4s ease-out infinite; }}
  .flow {{ stroke-dasharray: 4 4; animation: flow 1s linear infinite; }}
</style>"""


def svg(w, h, label, body, css=""):
    """A self-contained card: the whole canvas is the card, so nothing can touch its edge."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label, {chr(34): "&quot;"})}">\n{CSS}{css}\n'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="{BG}" stroke="{BORDER}"/>\n{body}\n</svg>\n')


def char_w(size, kind):
    """Average glyph width in px, rounded up so wrapped lines stay inside their column."""
    return size * {"s": 0.52, "b": 0.57, "m": 0.62}[kind]


def text(x, y, s, size, cls="s ink", weight=None, extra=""):
    wt = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{x}" y="{y:.1f}" class="{cls}" font-size="{size}"{wt}{extra}>{escape(s)}</text>'


def para(x, y, s, size, maxw, lh, cls="s ink", weight=None):
    """Wrapped text. Returns (svg, y below the last line)."""
    kind = "b" if weight else ("m" if "m" in cls.split() else "s")
    # textwrap breaks on no-break spaces too, so hide them while wrapping.
    rows = [r.replace("\x00", "\u00a0") for r in textwrap.wrap(s.replace("\u00a0", "\x00"), max(1, int(maxw / char_w(size, kind))))]
    out = "".join(text(x, y + size * 0.95 + i * lh, row, size, cls, weight) for i, row in enumerate(rows))
    return out, y + len(rows) * lh


def chips(x, y, items, maxw, size):
    """Pill chips flowed left to right. items: lists of (text, class) segments, or a
    (segments, dot) pair. Returns (svg, height)."""
    h, pad, gap = round(size * 2.3), round(size * 0.9), round(size * 0.6)
    out, cx, cy = [], 0, 0
    for item in items:
        segs, dot = item if isinstance(item, tuple) else (item, False)
        wid = 2 * pad + (size + 2 if dot else 0) + sum(len(t) * char_w(size, "m" if "m" in c.split() else "s") for t, c in segs) \
            + gap * (len(segs) - 1)
        if cx and cx + wid > maxw:
            cx, cy = 0, cy + h + gap
        px, tx = x + cx, x + cx + pad
        out.append(f'<rect x="{px}" y="{y + cy}" width="{wid:.0f}" height="{h}" rx="{h / 2:.0f}" fill="#ffffff0a" stroke="{BORDER}"/>')
        if dot:
            out.append(f'<circle cx="{tx + 3}" cy="{y + cy + h / 2}" r="3" fill="{GREEN}"/>'
                       f'<circle cx="{tx + 3}" cy="{y + cy + h / 2}" r="3" fill="{GREEN}" class="ping"/>')
            tx += size + 2
        for t, c in segs:
            kind = "m" if "m" in c.split() else "s"
            out.append(text(f"{tx:.0f}", y + cy + h / 2 + size * 0.36, t, size, c))
            tx += len(t) * char_w(size, kind) + gap
        cx += wid + gap
    return "".join(out), cy + h


def tag_chips(tags, x, y, maxw, size):
    return chips(x, y, [[(t, "m dim")] for t in tags.split(" · ")], maxw, size)


def link_label(p):
    href = p["href"]
    return href.replace("https://github.com/", "github.com/") if "github.com" in href else "read the paper"


# ---- pictures ----------------------------------------------------------------------

_clip_ids = itertools.count()


def draw_terminal(x, y, w, h):
    """A terminal split: an agent on the left, the live page it is showing on the right."""
    half = w * 0.46
    term = [("$ preview", INK), ("› fixed spacing", "#edededcc"), ("› reload", "#edededcc"), ("› 0 errors", "#edededcc"), ("✓ looks right", ACCENT)]
    fs = min(11.5, (half - 22) / 9.3)
    tl = "".join(f'<text x="{x + 14}" y="{y + 50 + i * 22}" class="m" font-size="{fs:.1f}" fill="{c}">{escape(s)}</text>' for i, (s, c) in enumerate(term))
    bx, bw = x + half + 1, w - half - 1
    page = (f'<rect x="{bx + 10}" y="{y + 36}" width="{bw - 20}" height="16" rx="8" fill="#ffffff12"/>'
            f'<text x="{bx + 20}" y="{y + 47.5}" class="m" font-size="9" fill="{DIM}">localhost:4321</text>'
            f'<rect x="{bx + 16}" y="{y + 68}" width="{bw * .55:.0f}" height="12" rx="3" fill="{INK}"/>'
            f'<rect x="{bx + 16}" y="{y + 88}" width="{bw * .75:.0f}" height="6" rx="3" fill="#ffffff40"/>'
            f'<rect x="{bx + 16}" y="{y + 100}" width="{bw * .68:.0f}" height="6" rx="3" fill="#ffffff40"/>'
            f'<rect x="{bx + 16}" y="{y + 120}" width="{(bw - 44) / 2:.0f}" height="{h - 142}" rx="6" fill="{ACCENT}"/>'
            f'<rect x="{bx + 28 + (bw - 44) / 2:.0f}" y="{y + 120}" width="{(bw - 44) / 2:.0f}" height="{h - 142}" rx="6" fill="#ffffff1a"/>')
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{PANEL}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="26" fill="#1c1c1c"/>'
            + "".join(f'<circle cx="{x + 14 + i * 14}" cy="{y + 13}" r="4" fill="{c}"/>' for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]))
            + f'<text x="{x + w / 2}" y="{y + 17}" class="m" font-size="10" fill="{DIM}" text-anchor="middle">ghostty · agent │ preview</text>'
            + tl + page + f'<rect x="{x + half}" y="{y + 26}" width="1" height="{h - 26}" fill="#ffffff26"/>')


def draw_pipeline(x, y, w, h):
    """The fine-tuning pipeline: four stages joined by arrows whose dashes flow."""
    stages = [("docs", "PDFs, notes"), ("verified", "Q&A pairs"), ("QLoRA", "fine-tune"), ("evals", "coverage")]
    pad, gap = 18, 30
    nw = (w - 2 * pad - 3 * gap) / 4
    nh, ny = 96, y + h / 2 - 28
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{PANEL}"/>']
    for i, (a, b) in enumerate(stages):
        nx = x + pad + i * (nw + gap)
        last = i == len(stages) - 1
        out.append(f'<text x="{nx + nw / 2:.1f}" y="{ny - 12}" class="m dim" font-size="11" text-anchor="middle">0{i + 1}</text>'
                   f'<rect x="{nx:.1f}" y="{ny}" width="{nw:.1f}" height="{nh}" rx="10" fill="{"#7c9bff1f" if last else BG}" '
                   f'stroke="{ACCENT if last else "#ffffff2e"}"/>'
                   f'<text x="{nx + nw / 2:.1f}" y="{ny + 44}" class="s ink" font-size="14" font-weight="600" text-anchor="middle">{escape(a)}</text>'
                   f'<text x="{nx + nw / 2:.1f}" y="{ny + 64}" class="m dim" font-size="10" text-anchor="middle">{escape(b)}</text>')
        if not last:
            ax0, ax1, ay = nx + nw + 4, nx + nw + gap - 5, ny + nh / 2
            out.append(f'<line x1="{ax0:.1f}" y1="{ay}" x2="{ax1:.1f}" y2="{ay}" stroke="{ACCENT}" stroke-width="1.6" class="flow"/>'
                       f'<path d="M{ax1 - 5:.1f},{ay - 4} L{ax1 + 1:.1f},{ay} L{ax1 - 5:.1f},{ay + 4}" fill="none" stroke="{ACCENT}" stroke-width="1.6"/>')
    out.append(f'<text x="{x + w / 2:.0f}" y="{y + h - 22}" class="m dim" font-size="11" text-anchor="middle">every answer traced to its source</text>')
    return "".join(out)


def picture(p, x, y, w, h, align="xMidYMid", r=10):
    """A project image with rounded corners and a hairline border."""
    cid = f"c{next(_clip_ids)}"
    clip = f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/></clipPath>'
    if p["image"] == "draw:terminal":
        inner = draw_terminal(x, y, w, h)
    elif p["image"] == "draw:pipeline":
        inner = draw_pipeline(x, y, w, h)
    else:
        fit = p.get("fit", "slice")
        back = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff"/>' if fit == "meet" else ""
        uri = embed(p["image"], int(w * 1.6))
        inner = f'{back}<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="{align} {fit}" href="{uri}" xlink:href="{uri}"/>'
    return (f'{clip}<g clip-path="url(#{cid})">{inner}</g>'
            f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="{r}" fill="none" stroke="{BORDER}"/>')


# ---- project cards -----------------------------------------------------------------

def info(p, w, k, banner=False, link=None, tags=True):
    """The text block of a project card at width w. k holds the type sizes. Returns (svg, height)."""
    out, y = [], 0
    if not banner:
        out.append(text(0, y + k["meta"] * 0.95, p["meta"], k["meta"], "m dim"))
        y += k["meta"] + 12
    s, y = para(0, y, p["title"], k["title"], w, round(k["title"] * 1.22), "s ink", 600)
    y += 10
    s2, y = para(0, y, p["desc"], k["desc"], w, round(k["desc"] * 1.55), "s dim")
    out += [s, s2]
    if tags and p.get("tags"):
        c, ch = tag_chips(p["tags"], 0, y + 14, w, k["chip"])
        out.append(c)
        y += 14 + ch
    if p.get("href") and not banner:
        out.append(text(0, y + 20 + k["link"] * 0.95, f"{link or link_label(p)} →", k["link"], "m acc"))
        y += 20 + k["link"] + 4
    return "".join(out), y


def banner_head(w, repo, meta, size):
    """Repo name on the left, meta on the right (phones put meta in the text block instead)."""
    pad = 28 if w > 600 else 24
    return (text(pad, 34, f"kipung / {repo}", size, "m ink", 600)
            + (text(w - pad, 34, meta, size, "m dim", extra=' text-anchor="end"') if meta else "")
            + f'<rect x="0" y="52" width="{w}" height="1" fill="{BORDER}"/>')


FEATURE_K = {"meta": 12, "title": 28, "desc": 16, "chip": 12, "link": 13}
FEATURE_K_M = {"meta": 14, "title": 28, "desc": 18, "chip": 14, "link": 15}


def feature(p, flip=False, header=None):
    """Large card: image on one side, text on the other. header = (repo, meta) makes a repo banner."""
    W, pad, iw, gap = 1000, 28, 440, 36
    top = 52 if header else 0
    tw = W - 2 * pad - iw - gap
    block, bh = info(p, tw, FEATURE_K, banner=bool(header))
    ih = max(250, round(bh))
    H = top + 2 * pad + ih
    ix, tx = (W - pad - iw, pad) if flip else (pad, pad + iw + gap)
    body = ((banner_head(W, *header, 14) if header else "") + picture(p, ix, top + pad, iw, ih, p.get("align", "xMidYMid"))
            + f'<g transform="translate({tx} {top + pad + (ih - bh) / 2:.1f})">{block}</g>')
    return svg(W, H, f'{p["title"]}: {p["desc"]}', body)


MW = 480  # phone width; GitHub shows these at roughly 0.8x on a phone


def feature_m(p, header=None):
    """Phone version of feature(): image on top, text below."""
    W, pad = MW, 24
    top = 52 if header else 0
    iw, ih = W - 2 * pad, 250
    block, bh = info(dict(p, href=None) if header else p, iw, FEATURE_K_M)
    H = top + pad + ih + 24 + bh + pad
    body = ((banner_head(W, header[0], None, 15) if header else "") + picture(p, pad, top + pad, iw, ih, p.get("align", "xMidYMid"))
            + f'<g transform="translate({pad} {top + pad + ih + 24})">{block}</g>')
    return svg(W, H, f'{p["title"]}: {p["desc"]}', body)


MINI_K = {"meta": 11.5, "title": 20, "desc": 14.5, "chip": 11, "link": 12}
MINI_K_M = {"meta": 13, "title": 22, "desc": 17, "chip": 12, "link": 15}


def mini_height(p, phone):
    if phone:
        return 24 + 150 + 20 + info(p, 252, MINI_K_M, tags=False, link="on GitHub")[1] + 24
    return 28 + 170 + 22 + info(p, 434, MINI_K)[1] + 28


def row_height(p, phone):
    """Cards share a row two at a time, so each takes the height of the taller one in its row."""
    i = PROJECTS.index(p) // 2 * 2
    return max(mini_height(q, phone) for q in PROJECTS[i:i + 2])


def mini(p):
    W, pad = 490, 28
    block, _ = info(p, W - 2 * pad, MINI_K)
    body = (picture(p, pad, pad, W - 2 * pad, 170, p.get("align", "xMidYMid"))
            + f'<g transform="translate({pad} {pad + 170 + 22})">{block}</g>')
    return svg(W, row_height(p, False), f'{p["title"]}: {p["desc"]}', body)


def mini_m(p):
    """Phone version of mini(): shown at half the screen width, so the type is large."""
    W, pad = 300, 24
    block, _ = info(p, W - 2 * pad, MINI_K_M, tags=False, link="on GitHub")
    body = (picture(p, pad, pad, W - 2 * pad, 150, p.get("align", "xMidYMid"))
            + f'<g transform="translate({pad} {pad + 150 + 20})">{block}</g>')
    return svg(W, row_height(p, True), f'{p["title"]}: {p["desc"]}', body)


# ---- photos ------------------------------------------------------------------------

def caption(x, y, title, note, w, ts, ns):
    a, y1 = para(x, y, title, ts, w, round(ts * 1.4), "s ink", 600)
    b, y2 = para(x, y1 + 2, note, ns, w, round(ns * 1.5), "s dim")
    return a + b, y2


def plate(pl):
    W, pad, gap, ph = 1000, 28, 16, 380
    cw = (W - 2 * pad - 2 * gap) // 3
    cells, bottom = "", 0
    for i, (img, title, note, align) in enumerate(pl["photos"]):
        x = pad + i * (cw + gap)
        cap, end = caption(x, pad + 40 + ph + 16, title, note, cw, 15, 13)
        cells += picture({"image": img}, x, pad + 40, cw, ph, align) + cap
        bottom = max(bottom, end)
    body = text(pad, pad + 16, pl["title"], 18, "s ink", 600) + cells
    return svg(W, round(bottom + pad), _plate_label(pl), body)


def plate_m(pl):
    """Phone version of plate(): one wide photo, then two side by side."""
    W, pad = MW, 24
    iw = W - 2 * pad
    (a, *rest) = pl["photos"]
    out = [text(pad, pad + 18, pl["title"], 22, "s ink", 600)]
    y = pad + 40
    out.append(picture({"image": a[0]}, pad, y, iw, 300, a[3]))
    cap, y = caption(pad, y + 316, a[1], a[2], iw, 19, 17)
    out.append(cap)
    y += 22
    cw, deepest = (iw - 16) // 2, 0
    for i, (img, title, note, align) in enumerate(rest):
        x = pad + i * (cw + 16)
        out.append(picture({"image": img}, x, y, cw, 260, align))
        cap, end = caption(x, y + 276, title, note, cw, 17, 15)
        out.append(cap)
        deepest = max(deepest, end)
    return svg(W, round(deepest + pad), _plate_label(pl), "".join(out))


def _plate_label(pl):
    return f'{pl["title"]}: ' + "; ".join(f"{a}, {b}" for _, a, b, _ in pl["photos"])


# ---- experience timeline -----------------------------------------------------------

def _timeline_span():
    start = (2024, 1)
    end = max((2027, 6), (NOW[0] + (NOW[1] + 6 - 1) // 12, (NOW[1] + 6 - 1) % 12 + 1))
    mi = lambda ym: (ym[0] - start[0]) * 12 + ym[1] - 1
    return end, mi, mi(end)


def _timeline_label():
    return "Experience: research, work and leadership from 2024 to now. " + "; ".join(l for _, l, _, _ in TIMELINE)


def timeline():
    W, pad = 1000, 28
    lx, rx = 330, W - pad
    end, mi, span = _timeline_span()
    X = lambda ym: lx + (rx - lx) * mi(ym) / span
    row_h, top = 30, 96
    bottom = top + len(TIMELINE) * row_h
    H = bottom + 120
    out = [text(pad, pad + 16, "research, work and leadership", 12, "m dim")]
    for yr in range(2024, end[0] + 1):
        x = X((yr, 1))
        out.append(f'<rect x="{x:.1f}" y="{top - 14}" width="1" height="{bottom - top + 14}" fill="{GRID}"/>'
                   f'<text x="{x + 5:.1f}" y="{top - 4}" class="m dim" font-size="11">{yr}</text>')
    nx = X(NOW)
    out.append(f'<rect x="{nx:.1f}" y="{top - 14}" width="1.5" height="{bottom - top + 28}" fill="{ACCENT}"/>'
               f'<text x="{nx - 5:.1f}" y="{top - 4}" class="m acc" font-size="11" text-anchor="end">now</text>')
    gx = X((2027, 4))
    out.append(f'<text x="{gx:.1f}" y="{bottom + 8}" class="m dim" font-size="10.5" text-anchor="middle">grad ’27</text>'
               f'<circle cx="{gx:.1f}" cy="{bottom - 8}" r="3.5" fill="none" stroke="{INK}"/>')
    for i, (lane, label, a, b) in enumerate(TIMELINE):
        y = top + i * row_h
        x0, x1 = X(a), X(b or NOW)
        c = LANE_COLOR[lane]
        out.append(text(pad, y + 13, label, 14, "s ink")
                   + f'<rect x="{x0:.1f}" y="{y + 3}" width="{max(x1 - x0, 5):.1f}" height="10" rx="5" fill="{c}"/>')
        if b is None:
            out.append(f'<circle cx="{x1:.1f}" cy="{y + 8}" r="4" fill="{c}" style="animation: pulse 2.4s ease-in-out infinite"/>')
    my = bottom + 52
    out.append(f'<rect x="{lx}" y="{my - 8}" width="{rx - lx}" height="1" fill="{BORDER}"/>')
    for j, (ym, label) in enumerate(MILESTONES):
        x = X(ym)
        out.append(f'<circle cx="{x:.1f}" cy="{my - 8}" r="4.5" fill="{BG}" stroke="{ACCENT}" stroke-width="1.6"/>'
                   f'<text x="{x:.1f}" y="{my + 12 + (j % 2) * 14}" class="m dim" font-size="10.5" text-anchor="middle">{escape(label)}</text>')
    for i, lane in enumerate(LANE_COLOR):
        out.append(f'<rect x="{pad}" y="{my - 30 + i * 18}" width="10" height="10" rx="3" fill="{LANE_COLOR[lane]}"/>'
                   f'<text x="{pad + 16}" y="{my - 21 + i * 18}" class="m dim" font-size="11">{escape(LANE_NAME[lane])}</text>')
    out.append(f'<text x="{lx - 12}" y="{my - 4}" class="m dim" font-size="10.5" text-anchor="end">talks, papers, awards</text>')
    return svg(W, H, _timeline_label(), "".join(out))


def timeline_m():
    """Phone version of timeline(): each label sits on its own line above its bar."""
    W, pad = MW, 24
    end, mi, span = _timeline_span()
    X = lambda ym: pad + (W - 2 * pad) * mi(ym) / span
    row_h, top = 50, 100
    bottom = top + len(TIMELINE) * row_h
    out = [text(pad, pad + 18, "research, work and leadership", 13, "m dim")]
    for yr in range(2024, end[0] + 1):
        x = X((yr, 1))
        out.append(f'<rect x="{x:.1f}" y="{top - 12}" width="1" height="{bottom - top + 12}" fill="{GRID}"/>'
                   f'<text x="{x + 5:.1f}" y="{top - 2}" class="m dim" font-size="14">{yr}</text>')
    nx = X(NOW)
    out.append(f'<rect x="{nx:.1f}" y="{top - 12}" width="2" height="{bottom - top + 20}" fill="{ACCENT}"/>'
               f'<text x="{nx - 5:.1f}" y="{top - 2}" class="m acc" font-size="14" text-anchor="end">now</text>')
    for i, (lane, label, a, b) in enumerate(TIMELINE):
        y = top + 26 + i * row_h
        x0, x1 = X(a), X(b or NOW)
        c = LANE_COLOR[lane]
        out.append(text(pad, y, label, 17, "s ink")
                   + f'<rect x="{x0:.1f}" y="{y + 7}" width="{max(x1 - x0, 6):.1f}" height="10" rx="5" fill="{c}"/>')
        if b is None:
            out.append(f'<circle cx="{x1:.1f}" cy="{y + 12}" r="5" fill="{c}" style="animation: pulse 2.4s ease-in-out infinite"/>')
    my = bottom + 30
    out.append(f'<rect x="{pad}" y="{my}" width="{W - 2 * pad}" height="1" fill="{BORDER}"/>')
    for j, (ym, label) in enumerate(MILESTONES):
        x = X(ym)
        anchor = "start" if x < pad + 24 else ("end" if x > W - pad - 40 else "middle")
        out.append(f'<circle cx="{x:.1f}" cy="{my}" r="5" fill="{BG}" stroke="{ACCENT}" stroke-width="1.8"/>'
                   f'<text x="{x:.1f}" y="{my + 26 + (j % 3) * 20}" class="m dim" font-size="14" text-anchor="{anchor}">{escape(label)}</text>')
    ky = my + 26 + 3 * 20 + 18
    kx = pad
    for lane in LANE_COLOR:
        out.append(f'<rect x="{kx}" y="{ky - 11}" width="12" height="12" rx="3" fill="{LANE_COLOR[lane]}"/>'
                   f'<text x="{kx + 18}" y="{ky}" class="m dim" font-size="13">{escape(LANE_NAME[lane])}</text>')
        kx += 18 + len(LANE_NAME[lane]) * 8.2 + 16
    out.append(f'<text x="{pad}" y="{ky + 28}" class="m dim" font-size="13">○ talks, papers, awards</text>')
    return svg(W, ky + 28 + pad, _timeline_label(), "".join(out))


# ---- hero --------------------------------------------------------------------------

HERO_CSS = """<style>
  @keyframes draw { 0% { stroke-dashoffset: 1 } 55%, 92% { stroke-dashoffset: 0; opacity: 1 } 100% { stroke-dashoffset: 0; opacity: 0 } }
  @keyframes pop { 0%, 1% { opacity: 0 } 2%, 92% { opacity: 1 } 100% { opacity: 0 } }
  @keyframes rise { from { opacity: 0; transform: translateY(10px) } to { opacity: 1; transform: none } }
  .r1 { animation: rise .8s cubic-bezier(.2,.7,.2,1) both; }
  .r2 { animation: rise .8s .15s cubic-bezier(.2,.7,.2,1) both; }
  .ln { fill: none; stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 9s .4s ease-out infinite; }
</style>
<defs><filter id="glow" x="-10%" y="-20%" width="120%" height="140%"><feGaussianBlur stdDeviation="4"/></filter></defs>"""


def loss_chart(px, py, pw, ph, k=1.0):
    """A fine-tune settling, drawn in a panel. k scales the labels."""
    fx, fy, fw, fh = px + 20 * k, py + 48 * k, pw - 40 * k, ph - 48 * k - 24 * k
    curve = lambda pts: " ".join(f"{'M' if i == 0 else 'L'}{fx + a * fw:.1f},{fy + (1 - b) * fh:.1f}" for i, (a, b) in enumerate(pts))
    train = [(i / 24, 0.08 + 0.84 * (0.5 ** (i / 3.2)) + (0.03 if i % 3 == 1 else 0)) for i in range(25)]
    evals = [(i / 24, 0.2 + 0.72 * (0.5 ** (i / 3.6))) for i in range(0, 25, 3)]
    grid = "".join(f'<rect x="{fx}" y="{fy + fh * i / 4:.1f}" width="{fw}" height="1" fill="{GRID}"/>' for i in range(5))
    dots = "".join(
        f'<circle cx="{fx + a * fw:.1f}" cy="{fy + (1 - b) * fh:.1f}" r="{3 * k:.1f}" fill="{BG}" stroke="{INK}" stroke-width="1.4" '
        f'style="animation: pop 9s {0.8 + a * 4.2:.2f}s linear infinite both"/>' for a, b in evals)
    ly, fs = py + 26 * k, 11 * k
    line = curve(train)
    return f"""<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="12" fill="{PANEL}" stroke="{BORDER}"/>
{grid}
<path d="{line}" class="ln" pathLength="1" stroke="{ACCENT}" stroke-width="{6 * k:.1f}" stroke-opacity=".55" filter="url(#glow)" stroke-linejoin="round"/>
<path d="{line}" class="ln" pathLength="1" stroke="{ACCENT}" stroke-width="{2.2 * k:.1f}" stroke-linejoin="round" stroke-linecap="round"/>
<path d="{curve(evals)}" fill="none" stroke="{INK}" stroke-width="1" stroke-dasharray="3 4" opacity=".45"/>
{dots}
<rect x="{px + 20 * k}" y="{ly - 4 * k:.1f}" width="{14 * k:.0f}" height="2.5" rx="1" fill="{ACCENT}"/>
<text x="{px + 40 * k}" y="{ly}" class="m dim" font-size="{fs:.1f}">train loss</text>
<circle cx="{px + 122 * k:.1f}" cy="{ly - 3 * k:.1f}" r="{3 * k:.1f}" fill="{BG}" stroke="{INK}" stroke-width="1.2"/>
<text x="{px + 132 * k:.1f}" y="{ly}" class="m dim" font-size="{fs:.1f}">eval loss</text>
<text x="{px + pw - 20 * k}" y="{ly}" class="m dim" font-size="{fs:.1f}" text-anchor="end">steps →</text>"""


def fact_chips(x, y, maxw, size):
    return chips(x, y, [([(k.upper(), "m acc"), (v, "s ink")], k == "Lab") for k, v in FACTS], maxw, size)


def hero():
    W, pad, lw = 1000, 40, 530
    y = pad
    sub = text(pad, y + 12, f"{FULL_NAME} · Riverside, CA", 13, "m dim")
    name = text(pad - 2, y + 92, NAME, 68, "s ink r1", 700, ' letter-spacing="-2"')
    tag, y1 = para(pad, y + 118, TAGLINE, 25, lw, 33, "s ink r2", 500)
    about, y2 = para(pad, y1 + 14, ABOUT, 15.5, lw, 24, "s dim")
    ph = 270
    panel = loss_chart(W - pad - 340, pad, 340, ph)
    cy = max(y2, pad + ph) + 30
    c, ch = fact_chips(pad, cy, W - 2 * pad, 13)
    return svg(W, round(cy + ch + pad), f"{NAME}. {TAGLINE}", sub + name + tag + about + panel + c, HERO_CSS)


def hero_m():
    W, pad = MW, 24
    iw = W - 2 * pad
    sub = text(pad, pad + 12, f"{FULL_NAME} · Riverside, CA", 13, "m dim")
    name = text(pad - 2, pad + 78, NAME, 56, "s ink r1", 700, ' letter-spacing="-1.5"')
    tag, y1 = para(pad, pad + 104, TAGLINE, 23, iw, 31, "s ink r2", 500)
    about, y2 = para(pad, y1 + 12, ABOUT, 17, iw, 26, "s dim")
    ph = 240
    panel = loss_chart(pad, y2 + 24, iw, ph, 1.2)
    c, ch = fact_chips(pad, y2 + 24 + ph + 24, iw, 14)
    return svg(W, round(y2 + 24 + ph + 24 + ch + pad), f"{NAME}. {TAGLINE}", sub + name + tag + about + panel + c, HERO_CSS)


# ---- README ------------------------------------------------------------------------

PHONE = "(max-width: 640px)"


def picture_md(stem, alt, width="100%", base="assets/"):
    """A dark card with its phone version for narrow screens.

    GitHub shows a phone only one variant of a themed <picture>, which is why the artwork
    has a single dark theme: nothing can pick the wrong one.
    """
    return (f'<picture><source media="{PHONE}" srcset="{base}{stem}-m.svg">'
            f'<img src="{base}{stem}.svg" width="{width}" alt="{escape(alt, {chr(34): "&quot;"})}"></picture>')


def readme():
    link = lambda href, inner: f'<a href="{href}">{inner}</a>' if href else inner
    featured = "\n".join(link(p.get("href"), picture_md(f"feat-{p['slug']}", f"{p['title']}: {p['desc']}"))
                         for p in FEATURED if p.get("readme", True))
    minis = [link(p.get("href"), picture_md(f"proj-{p['slug']}", f"{p['title']}: {p['desc']}", "49%")) for p in PROJECTS]
    rows = lambda ms: "\n\n".join("<p>\n" + "\n".join(ms[i:i + 2]) + "\n</p>" for i in range(0, len(ms), 2))
    more = (rows(minis[:4]) + f"\n\n<details>\n<summary><b>{len(minis) - 4} more projects</b></summary>\n\n"
            + rows(minis[4:]) + "\n\n</details>")
    photos = "\n\n".join(picture_md(f"photos-{pl['slug']}", _plate_label(pl)) for pl in PLATES)
    return (ROOT / "scripts" / "README.template.md").read_text(encoding="utf-8").format(
        hero=picture_md("hero", f"{NAME}. {TAGLINE}"), featured=featured, projects=more, photos=photos,
        timeline=picture_md("timeline", "Experience: research, work and leadership from 2024 to now."))


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    by_slug = {p["slug"]: p for p in FEATURED + PROJECTS}
    write(OUT / "hero.svg", hero())
    write(OUT / "hero-m.svg", hero_m())
    write(OUT / "timeline.svg", timeline())
    write(OUT / "timeline-m.svg", timeline_m())
    for i, p in enumerate(q for q in FEATURED if q.get("readme", True)):
        write(OUT / f"feat-{p['slug']}.svg", feature(p, flip=i % 2 == 1))
        write(OUT / f"feat-{p['slug']}-m.svg", feature_m(p))
    for p in PROJECTS:
        write(OUT / f"proj-{p['slug']}.svg", mini(p))
        write(OUT / f"proj-{p['slug']}-m.svg", mini_m(p))
    for pl in PLATES:
        write(OUT / f"photos-{pl['slug']}.svg", plate(pl))
        write(OUT / f"photos-{pl['slug']}-m.svg", plate_m(pl))
    for r in REPOS:
        p = dict(by_slug[r["slug"]])
        p["tags"] = r.get("tags") or p["tags"]
        header = (r["repo"], p["meta"])
        write(REPO_OUT / r["repo"] / ".github" / "banner.svg", feature(p, header=header))
        write(REPO_OUT / r["repo"] / ".github" / "banner-m.svg", feature_m(p, header=header))
    write(ROOT / "README.md", readme())
    print("wrote", len(list(OUT.glob("*.svg"))), "profile SVGs and", len(REPOS) * 2, "repo banners")
