"""Render the profile artwork, and the banners for the featured repos, from the data below.

The profile reads like a paper: a title page, numbered figures with captions, plates of
photographs, and a timeline. Serif type, one cobalt accent, hairline rules, light and dark.
GitHub shows SVGs as images, so only system fonts render, motion is CSS inside the file,
and photographs are embedded as data URIs (sources in assets/src/).

    python3 scripts/build.py      # writes assets/*.svg and dist/repos/<repo>/.github/*.svg
Needs ffmpeg for resizing the embedded photographs.
"""

import base64
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

THEMES = {
    "light": {"paper": "#faf8f3", "ink": "#16181d", "dim": "#16181d99", "rule": "#16181d33", "accent": "#2547d0", "panel": "#f0ede5"},
    "dark": {"paper": "#0d1117", "ink": "#ece8df", "dim": "#ece8df99", "rule": "#ece8df33", "accent": "#7c9bff", "panel": "#161b22"},
}
SERIF = "'Iowan Old Style', 'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

NAME = "Ki-Pung (Kip) Park"
SUBTITLE = "Fine-tuning, evaluating, and running language models locally."
ABSTRACT = [
    "CS student (ML & AI, ’27) at California Baptist University. I build",
    "source-verified fine-tuning pipelines, run controlled LLM experiments,",
    "and ship local-first AI tools that people actually use.",
]
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

# Large figure cards, in reading order. image = file in assets/src, or "draw:<name>".
FIGURES = [
    {"slug": "kanto", "title": "Living Kanto", "meta": "Simulation · local LLMs", "image": "kanto.jpg",
     "desc": "A persistent world where 100 residents, each run by a local language model, travel, work, talk and pursue their own ambitions.",
     "tags": "local LLMs · agents · persistent world state", "href": "https://github.com/kipung/living-kanto"},
    {"slug": "finetune", "title": "Domain Fine-Tuning Pipeline", "meta": "CAIMLL · lab backbone", "image": "finetune.jpg",
     "desc": "Reference documents become source-verified training data, checked for evidence coverage, answer quality and reproducibility.",
     "tags": "QLoRA · Unsloth · vLLM · GGUF · evaluation"},
    {"slug": "subliminal", "title": "Subliminal Learning in LLMs", "meta": "Study lead · under review", "image": "subliminal-teacher.jpg", "fit": "meet",
     "desc": "Can a hidden love of owls pass from teacher to student through number sequences? The teacher picked owls 53% of the time; students barely moved.",
     "tags": "Llama 3.2 3B · LoRA · system prompts", "href": "https://github.com/kipung/WeHateOwls"},
    {"slug": "geoai", "title": "GeoAI: Overdose Risk Mapping", "meta": "AMCIS 2025 · coauthor", "image": "geoai.jpg",
     "desc": "A deep model predicts areas of suspected drug-overdose risk from geolocated posts; Kepler.gl maps turn its output into regional insight.",
     "tags": "deep learning · GIS · Kepler.gl", "href": "https://aisel.aisnet.org/amcis2025/intelfuture/intelfuture/27/"},
]

# Smaller cards, two per row. The first four show; the rest sit behind "More projects".
MINIS = [
    {"slug": "degree", "title": "AI Degree Planning Companion", "meta": "Student Success", "image": "degree.jpg", "fit": "meet",
     "desc": "An agent that plans courses over a Neo4j prerequisite graph, on local models, streamed to a React chat UI.",
     "tags": "LangChain · Neo4j · FastAPI · Ollama · React", "href": "https://github.com/kipung/degree_planning_guide"},
    {"slug": "browser", "title": "Terminal Browser Split", "meta": "Dev tool", "image": "draw:terminal",
     "desc": "A live, clickable browser preview in a native terminal split, opened by you with a hotkey or by any coding agent with one command.",
     "tags": "Ghostty · kitty · WezTerm · tmux", "href": "https://github.com/kipung/terminal-browser"},
    {"slug": "hydro", "title": "Rainfall Transfer Between Gauges", "meta": "SCCUR 2026", "image": "hydro.jpg", "fit": "meet",
     "desc": "Hourly rainfall from one gauge estimated from another across 28 years of records; held-out event hours reach R² = 0.58.",
     "tags": "Python · time series · lagged OLS"},
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
     "desc": "3rd place in the online division of the Cactus × Google DeepMind FunctionGemma Hackathon."},
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

# Banners for the featured repos: written to dist/repos/<repo>/.github/banner-{light,dark}.svg
REPOS = [
    {"repo": "living-kanto", "fig": "kanto"},
    {"repo": "CSC422_Subliminal_Learning", "fig": "subliminal"},
    {"repo": "WeHateOwls", "fig": "subliminal"},
    {"repo": "BAY-min_personal_tutor", "mini": "baymin", "tags": "Reachy Mini · Gemini Live · OpenCV · Firestore · BLE"},
    {"repo": "degree_planning_guide", "fig": "degree"},
    {"repo": "terminal-browser", "fig": "browser"},
    {"repo": "SET_PROJECT_3", "fig": "acm"},
    {"repo": "tracr_to_transformer_lens_generalize", "mini": "tracr", "tags": "Tracr · JAX · TransformerLens · RASP"},
    {"repo": "ffn_relu_vs_geglu_mnist", "mini": "geglu", "tags": "PyTorch Lightning · MNIST · bootstrap CIs"},
    {"repo": "campusmate", "mini": "campusmate", "tags": "Flutter · Firebase · Dart"},
]


@lru_cache(maxsize=None)
def embed(name, width):
    """A source photo resized to `width` px and returned as a JPEG data URI."""
    jpg = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(SRC / name), "-vf", f"scale='min({width},iw)':-2",
         "-q:v", "6", "-f", "image2", "-c:v", "mjpeg", "pipe:1"],
        check=True, capture_output=True,
    ).stdout
    return "data:image/jpeg;base64," + base64.b64encode(jpg).decode()


def style(t):
    return f"""<style>
  .s {{ font-family: {SERIF}; }}
  .m {{ font-family: {MONO}; }}
  .ink {{ fill: {t['ink']}; }}
  .dim {{ fill: {t['dim']}; }}
  .acc {{ fill: {t['accent']}; }}
  .cap {{ font-size: 11px; letter-spacing: .14em; text-transform: uppercase; }}
</style>"""


def svg(w, h, label, t, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">\n{style(t)}\n'
            f'<rect width="{w}" height="{h}" fill="{t["paper"]}"/>\n{body}\n</svg>\n')


def lines(x, y, text, width_chars, size, cls, gap, italic=False):
    it = ' font-style="italic"' if italic else ""
    return "".join(
        f'<text x="{x}" y="{y + i * gap}" class="{cls}" font-size="{size}"{it}>{escape(l)}</text>'
        for i, l in enumerate(textwrap.wrap(text, width_chars))
    )


def draw_terminal(x, y, w, h, t):
    """A terminal split: an agent on the left, the live page it is showing on the right."""
    half = w * 0.46
    term = [("$ preview start", "#ece8df"), ("twin started · preview open", "#ece8df99"),
            ("› agent: spacing fixed", "#ece8dfcc"), ("› reload · 0 errors", "#ece8dfcc"), ("✓ looks right", t["accent"])]
    tl = "".join(f'<text x="{x + 14}" y="{y + 48 + i * 22}" class="m" font-size="11.5" fill="{c}">{escape(s)}</text>' for i, (s, c) in enumerate(term))
    bx = x + half + 1
    bw = w - half - 1
    page = (f'<rect x="{bx}" y="{y + 26}" width="{bw}" height="{h - 26}" fill="#faf8f3"/>'
            f'<rect x="{bx + 10}" y="{y + 34}" width="{bw - 20}" height="16" rx="8" fill="#e6e2d8"/>'
            f'<text x="{bx + 20}" y="{y + 46}" class="m" font-size="9" fill="#16181d99">localhost:4321</text>'
            f'<rect x="{bx + 16}" y="{y + 66}" width="{bw * .55:.0f}" height="12" fill="#16181d"/>'
            f'<rect x="{bx + 16}" y="{y + 86}" width="{bw * .75:.0f}" height="6" fill="#16181d55"/>'
            f'<rect x="{bx + 16}" y="{y + 98}" width="{bw * .68:.0f}" height="6" fill="#16181d55"/>'
            f'<rect x="{bx + 16}" y="{y + 118}" width="{(bw - 44) / 2:.0f}" height="{h - 140}" fill="{THEMES["light"]["accent"]}"/>'
            f'<rect x="{bx + 28 + (bw - 44) / 2:.0f}" y="{y + 118}" width="{(bw - 44) / 2:.0f}" height="{h - 140}" fill="#16181d22"/>')
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#0b0d12"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="26" fill="#1a1d24"/>'
            + "".join(f'<circle cx="{x + 14 + i * 14}" cy="{y + 13}" r="4" fill="{c}"/>' for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]))
            + f'<text x="{x + w / 2}" y="{y + 17}" class="m" font-size="10" fill="#ece8df88" text-anchor="middle">ghostty · agent │ preview</text>'
            + tl + page
            + f'<rect x="{x + half}" y="{y + 26}" width="1" height="{h - 26}" fill="#ece8df33"/>')


def picture(p, x, y, w, h, t, align="xMidYMid"):
    if p["image"].startswith("draw:"):
        return draw_terminal(x, y, w, h, t)
    fit = p.get("fit", "slice")
    back = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff"/>' if fit == "meet" else ""
    return (f'{back}<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="{align} {fit}" '
            f'href="{embed(p["image"], int(w * 1.6))}" xlink:href="{embed(p["image"], int(w * 1.6))}"/>'
            f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" fill="none" stroke="{t["rule"]}"/>')


def card(p, num, flip, t, header=None):
    """A large figure: picture on one side, numbered caption on the other."""
    W, top = 1000, (64 if header else 0)
    H = top + 300
    iw, ih = 452, 282
    ix = W - iw if flip else 0
    tx = 0 if flip else iw + 40
    tw_chars = 50
    head = ""
    if header:
        head = (f'<text x="0" y="22" class="m cap ink">{escape(header[0])}</text>'
                f'<text x="{W - 6}" y="22" class="m cap dim" text-anchor="end">{escape(header[1])}</text>'
                f'<rect x="0" y="34" width="{W}" height="1" fill="{t["ink"]}"/><rect x="0" y="38" width="{W}" height="1" fill="{t["ink"]}"/>')
    else:
        head = f'<rect x="0" y="0" width="{W}" height="1" fill="{t["rule"]}"/>'
    y0 = top + 9
    label = f"Fig. {num}" if num else "Repository"
    body = (head + picture(p, ix, y0, iw, ih, t)
            + f'<text x="{tx}" y="{y0 + 22}" class="m acc" font-size="12.5" font-weight="700">{label}</text>'
            + ("" if header else f'<text x="{(ix - 40) if flip else W - 6}" y="{y0 + 22}" class="m cap dim" text-anchor="end">{escape(p["meta"])}</text>')
            + f'<text x="{tx}" y="{y0 + 70}" class="s ink" font-size="{min(40 if header else 33, int(1000 / len(p["title"])))}">{escape(p["title"])}</text>'
            + lines(tx, y0 + 112, p["desc"], tw_chars, 18, "s ink", 27, italic=True)
            + f'<rect x="{tx}" y="{y0 + 222}" width="40" height="1" fill="{t["accent"]}"/>'
            + f'<text x="{tx}" y="{y0 + 248}" class="m dim" font-size="12.5" letter-spacing=".03em">{escape(p["tags"])}</text>'
            + (f'<text x="{tx}" y="{y0 + 272}" class="m acc" font-size="12.5">{escape(link_label(p))} →</text>' if p.get("href") and not header else ""))
    return svg(W, H, f'{label}. {p["title"]}: {p["desc"]}', t, body)


def link_label(p):
    href = p["href"]
    return href.replace("https://github.com/", "github.com/") if "github.com" in href else "read the paper"


def mini(p, t):
    W, H = 490, 330
    body = (f'<rect x="0" y="0" width="{W}" height="1" fill="{t["rule"]}"/>'
            + picture(p, 0, 12, W, 190, t, p.get("align", "xMidYMid"))
            + f'<text x="0" y="234" class="s ink" font-size="24">{escape(p["title"])}</text>'
            + f'<text x="{W - 6}" y="232" class="m cap dim" text-anchor="end">{escape(p["meta"])}</text>'
            + lines(0, 262, p["desc"], 56, 15, "s ink", 21, italic=True)
            + (f'<text x="0" y="318" class="m acc" font-size="11.5">{escape(link_label(p))} →</text>' if p.get("href") else ""))
    return svg(W, H, f'{p["title"]}: {p["desc"]}', t, body)


def plate(pl, t):
    W, H = 1000, 540
    cw, ch, gap = 320, 400, 20
    cells = ""
    for i, (img, title, note, align) in enumerate(pl["photos"]):
        x = i * (cw + gap)
        cells += (picture({"image": img}, x, 52, cw, ch, t, align)
                  + f'<text x="{x}" y="{52 + ch + 28}" class="s ink" font-size="17" font-weight="700">{escape(title)}</text>'
                  + f'<text x="{x}" y="{52 + ch + 50}" class="s dim" font-size="15" font-style="italic">{escape(note)}</text>')
    body = (f'<text x="0" y="24" class="s ink" font-size="20"><tspan font-weight="700">{escape(pl["title"])}</tspan></text>'
            f'<rect x="0" y="36" width="{W}" height="1" fill="{t["rule"]}"/>' + cells)
    return svg(W, H, f'{pl["title"]}: ' + "; ".join(f"{a}, {b}" for _, a, b, _ in pl["photos"]), t, body)


def timeline(t):
    W = 1000
    lx, rx = 300, W - 10
    start = (2024, 1)
    end = max((2027, 6), (NOW[0] + (NOW[1] + 6 - 1) // 12, (NOW[1] + 6 - 1) % 12 + 1))
    mi = lambda ym: (ym[0] - start[0]) * 12 + ym[1] - 1
    span = mi(end)
    X = lambda ym: lx + (rx - lx) * mi(ym) / span
    row_h, top = 30, 70
    H = top + len(TIMELINE) * row_h + 104
    lane_color = {"research": t["accent"], "work": t["ink"], "lead": t["dim"]}
    out = [f'<text x="0" y="24" class="s ink" font-size="20"><tspan class="acc" font-weight="700">Fig. 5.</tspan> <tspan font-style="italic">Research, work and leadership, 2024 to now.</tspan></text>',
           f'<rect x="0" y="36" width="{W}" height="1" fill="{t["rule"]}"/>']
    for yr in range(2024, end[0] + 1):
        x = X((yr, 1))
        out.append(f'<rect x="{x:.1f}" y="{top - 14}" width="1" height="{len(TIMELINE) * row_h + 14}" fill="{t["rule"]}"/>'
                   f'<text x="{x + 5:.1f}" y="{top - 4}" class="m dim" font-size="11">{yr}</text>')
    nx = X(NOW)
    out.append(f'<rect x="{nx:.1f}" y="{top - 14}" width="1.5" height="{len(TIMELINE) * row_h + 40}" fill="{t["accent"]}"/>'
               f'<text x="{nx - 5:.1f}" y="{top - 4}" class="m acc" font-size="11" text-anchor="end">now</text>')
    gx = X((2027, 4))
    out.append(f'<text x="{gx:.1f}" y="{top + len(TIMELINE) * row_h + 4}" class="m dim" font-size="10.5" text-anchor="middle">grad ’27</text>'
               f'<circle cx="{gx:.1f}" cy="{top + len(TIMELINE) * row_h - 10}" r="3.5" fill="none" stroke="{t["ink"]}"/>')
    for i, (lane, label, a, b) in enumerate(TIMELINE):
        y = top + i * row_h
        x0, x1 = X(a), X(b or NOW)
        c = lane_color[lane]
        out.append(f'<text x="0" y="{y + 12}" class="s ink" font-size="14.5">{escape(label)}</text>'
                   f'<rect x="{x0:.1f}" y="{y + 3}" width="{max(x1 - x0, 4):.1f}" height="11" fill="{c}"/>')
        if b is None:
            out.append(f'<path d="M{x1:.1f},{y + 3} l7,5.5 l-7,5.5 z" fill="{c}" style="animation: pulse 2.4s ease-in-out infinite"/>')
    my = top + len(TIMELINE) * row_h + 46
    out.append(f'<rect x="{lx}" y="{my - 8}" width="{rx - lx}" height="1" fill="{t["rule"]}"/>')
    for j, (ym, label) in enumerate(MILESTONES):
        x = X(ym)
        out.append(f'<circle cx="{x:.1f}" cy="{my - 8}" r="4" fill="{t["paper"]}" stroke="{t["accent"]}" stroke-width="1.6"/>'
                   f'<text x="{x:.1f}" y="{my + 12 + (j % 2) * 14}" class="m dim" font-size="10.5" text-anchor="middle">{escape(label)}</text>')
    key = [("research", "Research"), ("work", "Work"), ("lead", "Leadership & teaching")]
    for i, (lane, label) in enumerate(key):
        out.append(f'<rect x="0" y="{my - 30 + i * 18}" width="10" height="10" fill="{lane_color[lane]}"/>'
                   f'<text x="16" y="{my - 21 + i * 18}" class="m dim" font-size="11">{escape(label)}</text>')
    out.append(f'<text x="{lx - 12}" y="{my - 4}" class="m dim" font-size="10.5" text-anchor="end">talks, papers, awards</text>')
    out.insert(0, "<style>@keyframes pulse { 0%, 100% { opacity: 1 } 50% { opacity: .3 } }</style>")
    return svg(W, H, "Timeline of research, work and leadership from 2024 to now. " + "; ".join(l for _, l, _, _ in TIMELINE), t, "".join(out))


HERO_STYLE = """<style>
  @keyframes draw { 0% { stroke-dashoffset: 1 } 55%, 92% { stroke-dashoffset: 0; opacity: 1 } 100% { stroke-dashoffset: 0; opacity: 0 } }
  @keyframes pop { 0%, 1% { opacity: 0 } 2%, 92% { opacity: 1 } 100% { opacity: 0 } }
  @keyframes rise { from { opacity: 0; transform: translateY(10px) } to { opacity: 1; transform: none } }
  .r1 { animation: rise .8s cubic-bezier(.2,.7,.2,1) both; }
  .r2 { animation: rise .8s .15s cubic-bezier(.2,.7,.2,1) both; }
  .ln { fill: none; stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 9s .4s ease-out infinite; }
</style>"""


def loss_chart(fx, fy, fw, fh, t, k=1.0):
    """Fig. 0: a schematic fine-tune settling. k scales the labels."""
    def curve(pts):
        return " ".join(f"{'M' if i == 0 else 'L'}{fx + px * fw:.1f},{fy + (1 - py) * fh:.1f}" for i, (px, py) in enumerate(pts))

    train = [(i / 24, 0.08 + 0.84 * (0.5 ** (i / 3.2)) + (0.03 if i % 3 == 1 else 0)) for i in range(25)]
    evals = [(i / 24, 0.2 + 0.72 * (0.5 ** (i / 3.6))) for i in range(0, 25, 3)]
    ticks = "".join(f'<rect x="{fx + fw * i / 4:.1f}" y="{fy + fh}" width="1" height="5" fill="{t["rule"]}"/>' for i in range(5))
    dots = "".join(
        f'<circle cx="{fx + px * fw:.1f}" cy="{fy + (1 - py) * fh:.1f}" r="{3 * k:.1f}" fill="{t["paper"]}" stroke="{t["ink"]}" stroke-width="1.4" '
        f'style="animation: pop 9s {0.8 + px * 4.2:.2f}s linear infinite both"/>' for px, py in evals)
    return f"""<rect x="{fx}" y="{fy}" width="1" height="{fh}" fill="{t['rule']}"/><rect x="{fx}" y="{fy + fh}" width="{fw}" height="1" fill="{t['rule']}"/>
{ticks}
<path d="{curve(train)}" class="ln" pathLength="1" stroke="{t['accent']}" stroke-width="{2.2 * k:.1f}" stroke-linejoin="round"/>
{dots}
<path d="{curve(evals)}" fill="none" stroke="{t['ink']}" stroke-width="1" stroke-dasharray="3 4" opacity=".55"/>
<text x="{fx + fw}" y="{fy + 6 * k:.0f}" class="m" font-size="{11 * k:.1f}" fill="{t['accent']}" text-anchor="end">— train loss</text>
<text x="{fx + fw}" y="{fy + 22 * k:.0f}" class="m dim" font-size="{11 * k:.1f}" text-anchor="end">○ eval loss</text>
<text x="{fx}" y="{fy + fh + 26 * k:.0f}" class="m dim" font-size="{11 * k:.1f}">steps →</text>
<text x="{fx}" y="{fy + fh + 50 * k:.0f}" class="s ink" font-size="{14 * k:.1f}"><tspan font-weight="700">Fig. 0.</tspan> <tspan font-style="italic">A fine-tune settling (schematic).</tspan></text>"""


def hero(t):
    W, H = 1000, 470
    facts = "".join(
        f'<text x="{48 + i * 318}" y="{H - 50}" class="m cap acc">{escape(k)}</text>'
        f'<text x="{48 + i * 318}" y="{H - 26}" class="s ink" font-size="17">{escape(v)}</text>' for i, (k, v) in enumerate(FACTS))
    abstract = "".join(f'<text x="48" y="{300 + i * 25}" class="s ink" font-size="17">{escape(l)}</text>' for i, l in enumerate(ABSTRACT))
    body = f"""{HERO_STYLE}
<text x="48" y="40" class="m cap ink">Park, K.-P. · California Baptist University</text>
<text x="{W - 48}" y="40" class="m cap dim" text-anchor="end">Riverside, CA · {TODAY.year}</text>
<rect x="48" y="54" width="{W - 96}" height="1" fill="{t['ink']}"/><rect x="48" y="58" width="{W - 96}" height="1" fill="{t['ink']}"/>
<text x="46" y="158" class="s ink r1" font-size="64" letter-spacing="-1">{escape(NAME)}</text>
<text x="48" y="204" class="s acc r2" font-size="22" font-style="italic">{escape(SUBTITLE)}</text>
<text x="48" y="266" class="s ink" font-size="15" font-weight="700" letter-spacing=".04em">Abstract</text>
{abstract}
{loss_chart(640, 104, 312, 210, t)}
<rect x="48" y="{H - 84}" width="{W - 96}" height="1" fill="{t['rule']}"/>
{facts}"""
    return svg(W, H, f"{NAME}. {SUBTITLE}", t, body)


# Phone versions: one column, about twice the type size. GitHub shows them when the
# screen is 640px wide or less (see picture_md). W = 480 shows at roughly 0.75x on a phone.
MW = 480


def hero_m(t):
    W = MW
    abstract = lines(0, 280, " ".join(ABSTRACT), 42, 19, "s ink", 28)
    n_abs = len(textwrap.wrap(" ".join(ABSTRACT), 42))
    fy = 280 + n_abs * 28 + 40
    fh = 190
    y = fy + fh + 100
    facts = "".join(
        f'<text x="0" y="{y + 34 + i * 64}" class="m acc" font-size="14" letter-spacing=".14em">{escape(k.upper())}</text>'
        f'<text x="0" y="{y + 60 + i * 64}" class="s ink" font-size="21">{escape(v)}</text>' for i, (k, v) in enumerate(FACTS))
    H = y + 34 + len(FACTS) * 64
    body = f"""{HERO_STYLE}
<text x="0" y="26" class="m ink" font-size="14" letter-spacing=".14em">PARK, K.-P. · CBU</text>
<text x="{W - 2}" y="26" class="m dim" font-size="14" letter-spacing=".14em" text-anchor="end">RIVERSIDE · {TODAY.year}</text>
<rect x="0" y="40" width="{W}" height="1" fill="{t['ink']}"/><rect x="0" y="44" width="{W}" height="1" fill="{t['ink']}"/>
<text x="-2" y="118" class="s ink r1" font-size="47" letter-spacing="-1">{escape(NAME)}</text>
{lines(0, 164, SUBTITLE, 36, 23, "s acc r2", 31, italic=True)}
<text x="0" y="250" class="s ink" font-size="18" font-weight="700" letter-spacing=".04em">Abstract</text>
{abstract}
{loss_chart(6, fy, W - 10, fh, t, 1.35)}
<rect x="0" y="{y}" width="{W}" height="1" fill="{t['rule']}"/>
{facts}"""
    return svg(W, H, f"{NAME}. {SUBTITLE}", t, body)


def card_m(p, num, t, header=None):
    """Phone version of card(): picture on top, caption below."""
    W = MW
    out, y = [], 0
    if header:
        out.append(f'<text x="0" y="22" class="m ink" font-size="15" letter-spacing=".08em">{escape(header[0])}</text>'
                   f'<text x="0" y="46" class="m dim" font-size="14" letter-spacing=".1em">{escape(header[1].upper())}</text>'
                   f'<rect x="0" y="60" width="{W}" height="1" fill="{t["ink"]}"/><rect x="0" y="64" width="{W}" height="1" fill="{t["ink"]}"/>')
        y = 78
    else:
        out.append(f'<rect x="0" y="0" width="{W}" height="1" fill="{t["rule"]}"/>')
        y = 12
    ih = 300
    out.append(picture(p, 0, y, W, ih, t))
    y += ih + 36
    label = f"Fig. {num}" if num else "Repository"
    if not header:
        out.append(f'<text x="0" y="{y}" class="m acc" font-size="16" font-weight="700">{label}</text>'
                   f'<text x="{W - 2}" y="{y}" class="m dim" font-size="13" letter-spacing=".1em" text-anchor="end">{escape(p["meta"].upper())}</text>')
        y += 46
    else:
        y += 4
    tl = textwrap.wrap(p["title"], 24)
    out.append(lines(0, y, p["title"], 24, 34, "s ink", 40))
    y += (len(tl) - 1) * 40 + 44
    dl = textwrap.wrap(p["desc"], 43)
    out.append(lines(0, y, p["desc"], 43, 21, "s ink", 30, italic=True))
    y += (len(dl) - 1) * 30 + 34
    out.append(f'<rect x="0" y="{y}" width="48" height="1.5" fill="{t["accent"]}"/>')
    y += 30
    gl = textwrap.wrap(p["tags"], 46)
    out.append(lines(0, y, p["tags"], 46, 16, "m dim", 24))
    y += (len(gl) - 1) * 24
    if p.get("href") and not header:
        y += 34
        out.append(f'<text x="0" y="{y}" class="m acc" font-size="16">{escape(link_label(p))} →</text>')
    return svg(W, y + 16, f'{label}. {p["title"]}: {p["desc"]}', t, "".join(out))


def mini_m_height(p):
    """Cards share a row two at a time, so each takes the height of the taller one in its row."""
    i = MINIS.index(p) // 2 * 2
    return max(mini_m_layout(q)[1] for q in MINIS[i:i + 2])


def mini_m_layout(p):
    tl, dl = textwrap.wrap(p["title"], 15), textwrap.wrap(p["desc"], 22)
    y_title = 190 + 12 + 42
    y_meta = y_title + (len(tl) - 1) * 34 + 32
    y_desc = y_meta + 40
    y_link = y_desc + (len(dl) - 1) * 30 + 44
    return (y_title, y_meta, y_desc, y_link), y_link + 14


def mini_m(p, t):
    """Phone version of mini(): shown at half the screen width, so the type is large."""
    W, H = 300, mini_m_height(p)
    (y_title, y_meta, y_desc, y_link), _ = mini_m_layout(p)
    body = (f'<rect x="0" y="0" width="{W}" height="1" fill="{t["rule"]}"/>'
            + picture(p, 0, 12, W, 190, t, p.get("align", "xMidYMid"))
            + lines(0, y_title, p["title"], 15, 30, "s ink", 34)
            + f'<text x="0" y="{y_meta}" class="m dim" font-size="17" letter-spacing=".06em">{escape(p["meta"])}</text>'
            + lines(0, y_desc, p["desc"], 22, 21, "s ink", 30, italic=True)
            + (f'<text x="0" y="{y_link}" class="m acc" font-size="18">on GitHub →</text>' if p.get("href") else ""))
    return svg(W, H, f'{p["title"]}: {p["desc"]}', t, body)


def plate_m(pl, t):
    """Phone version of plate(): one wide photo, then two side by side."""
    W = MW
    (a, *rest) = pl["photos"]
    out = [f'<text x="0" y="28" class="s ink" font-size="25" font-weight="700">{escape(pl["title"])}</text>',
           f'<rect x="0" y="42" width="{W}" height="1" fill="{t["rule"]}"/>']
    out.append(picture({"image": a[0]}, 0, 56, W, 320, t, a[3])
               + f'<text x="0" y="{56 + 320 + 32}" class="s ink" font-size="21" font-weight="700">{escape(a[1])}</text>'
               + f'<text x="0" y="{56 + 320 + 60}" class="s dim" font-size="19" font-style="italic">{escape(a[2])}</text>')
    y0, cw, ch = 56 + 320 + 92, (W - 20) // 2, 290
    deepest = 0
    for i, (img, title, note, align) in enumerate(rest):
        x = i * (cw + 20)
        tl, nl = textwrap.wrap(title, 19), textwrap.wrap(note, 22)
        out.append(picture({"image": img}, x, y0, cw, ch, t, align)
                   + lines(x, y0 + ch + 32, title, 19, 20, "s ink", 26).replace('class="s ink"', 'class="s ink" font-weight="700"')
                   + lines(x, y0 + ch + 32 + len(tl) * 26 + 4, note, 22, 18, "s dim", 25, italic=True))
        deepest = max(deepest, ch + 32 + len(tl) * 26 + 4 + (len(nl) - 1) * 25)
    return svg(W, y0 + deepest + 16, f'{pl["title"]}: ' + "; ".join(f"{a}, {b}" for _, a, b, _ in pl["photos"]), t, "".join(out))


def timeline_m(t):
    """Phone version of timeline(): each label sits on its own line above its bar."""
    W = MW
    start = (2024, 1)
    end = max((2027, 6), (NOW[0] + (NOW[1] + 6 - 1) // 12, (NOW[1] + 6 - 1) % 12 + 1))
    mi = lambda ym: (ym[0] - start[0]) * 12 + ym[1] - 1
    X = lambda ym: (W - 12) * mi(ym) / mi(end)
    row_h, top = 50, 104
    lane_color = {"research": t["accent"], "work": t["ink"], "lead": t["dim"]}
    bottom = top + len(TIMELINE) * row_h
    out = ["<style>@keyframes pulse { 0%, 100% { opacity: 1 } 50% { opacity: .3 } }</style>",
           f'<text x="0" y="28" class="s ink" font-size="23"><tspan class="acc" font-weight="700">Fig. 5.</tspan> <tspan font-style="italic">Research, work and leadership,</tspan></text>',
           f'<text x="0" y="56" class="s ink" font-size="23" font-style="italic">2024 to now.</text>',
           f'<rect x="0" y="70" width="{W}" height="1" fill="{t["rule"]}"/>']
    for yr in range(2024, end[0] + 1):
        x = X((yr, 1))
        out.append(f'<rect x="{x:.1f}" y="{top - 12}" width="1" height="{bottom - top + 12}" fill="{t["rule"]}"/>'
                   f'<text x="{x + 5:.1f}" y="{top - 2}" class="m dim" font-size="14">{yr}</text>')
    nx = X(NOW)
    out.append(f'<rect x="{nx:.1f}" y="{top - 12}" width="2" height="{bottom - top + 20}" fill="{t["accent"]}"/>'
               f'<text x="{nx - 5:.1f}" y="{top - 2}" class="m acc" font-size="14" text-anchor="end">now</text>')
    for i, (lane, label, a, b) in enumerate(TIMELINE):
        y = top + 26 + i * row_h
        x0, x1 = X(a), X(b or NOW)
        c = lane_color[lane]
        out.append(f'<text x="0" y="{y}" class="s ink" font-size="18">{escape(label)}</text>'
                   f'<rect x="{x0:.1f}" y="{y + 7}" width="{max(x1 - x0, 5):.1f}" height="11" fill="{c}"/>')
        if b is None:
            out.append(f'<path d="M{x1:.1f},{y + 7} l8,5.5 l-8,5.5 z" fill="{c}" style="animation: pulse 2.4s ease-in-out infinite"/>')
    my = bottom + 30
    out.append(f'<rect x="0" y="{my}" width="{W - 12}" height="1" fill="{t["rule"]}"/>')
    for j, (ym, label) in enumerate(MILESTONES):
        x = X(ym)
        anchor = "start" if x < 40 else ("end" if x > W - 60 else "middle")
        out.append(f'<circle cx="{x:.1f}" cy="{my}" r="5" fill="{t["paper"]}" stroke="{t["accent"]}" stroke-width="1.8"/>'
                   f'<text x="{x:.1f}" y="{my + 26 + (j % 3) * 20}" class="m dim" font-size="14" text-anchor="{anchor}">{escape(label)}</text>')
    ky = my + 26 + 3 * 20 + 18
    key = [("research", "Research"), ("work", "Work"), ("lead", "Leadership & teaching")]
    kx = 0
    for lane, label in key:
        out.append(f'<rect x="{kx}" y="{ky - 11}" width="12" height="12" fill="{lane_color[lane]}"/>'
                   f'<text x="{kx + 18}" y="{ky}" class="m dim" font-size="14">{escape(label)}</text>')
        kx += 18 + len(label) * 8.6 + 22
    out.append(f'<text x="0" y="{ky + 28}" class="m dim" font-size="14">○ talks, papers, awards</text>')
    return svg(W, ky + 40, "Timeline of research, work and leadership from 2024 to now. " + "; ".join(l for _, l, _, _ in TIMELINE), t, "".join(out))


PHONE = "(max-width: 640px)"


def picture_md(stem, alt, width="100%", base="assets/"):
    """Light and dark artwork, each with a phone version for narrow screens."""
    return (f'<picture><source media="{PHONE} and (prefers-color-scheme: dark)" srcset="{base}{stem}-m-dark.svg">'
            f'<source media="{PHONE}" srcset="{base}{stem}-m-light.svg">'
            f'<source media="(prefers-color-scheme: dark)" srcset="{base}{stem}-dark.svg">'
            f'<img src="{base}{stem}-light.svg" width="{width}" alt="{escape(alt, {chr(34): "&quot;"})}"></picture>')


def readme():
    link = lambda href, inner: f'<a href="{href}">{inner}</a>' if href else inner
    figs = "\n".join(link(p.get("href"), picture_md(f"fig-{p['slug']}", f"Fig. {i}. {p['title']}: {p['desc']}"))
                     for i, p in enumerate(FIGURES, 1))
    minis = [link(p.get("href"), picture_md(f"mini-{p['slug']}", f"{p['title']}: {p['desc']}", "49%")) for p in MINIS]
    rows = lambda ms: "\n\n".join("<p>\n" + "\n".join(ms[i:i + 2]) + "\n</p>" for i in range(0, len(ms), 2))
    mini_rows = (rows(minis[:4]) + f"\n\n<details>\n<summary><b>{len(minis) - 4} more projects</b></summary>\n\n"
                 + rows(minis[4:]) + "\n\n</details>")
    plates = "\n\n".join(picture_md(f"plate-{pl['slug']}", f"{pl['title']}: " + "; ".join(f"{a}, {c}" for _, a, c, _ in pl["photos"]))
                          for pl in PLATES)
    return (ROOT / "scripts" / "README.template.md").read_text(encoding="utf-8").format(
        hero=picture_md("hero", f"{NAME}. {SUBTITLE}"), figures=figs, minis=mini_rows, plates=plates,
        timeline=picture_md("timeline", "Fig. 5. Timeline of research, work and leadership from 2024 to now."))


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    by_slug = {p["slug"]: p for p in FIGURES + MINIS}
    for name, t in THEMES.items():
        write(OUT / f"hero-{name}.svg", hero(t))
        write(OUT / f"hero-m-{name}.svg", hero_m(t))
        write(OUT / f"timeline-{name}.svg", timeline(t))
        write(OUT / f"timeline-m-{name}.svg", timeline_m(t))
        for i, p in enumerate(FIGURES, 1):
            write(OUT / f"fig-{p['slug']}-{name}.svg", card(p, i, i % 2 == 0, t))
            write(OUT / f"fig-{p['slug']}-m-{name}.svg", card_m(p, i, t))
        for p in MINIS:
            write(OUT / f"mini-{p['slug']}-{name}.svg", mini(p, t))
            write(OUT / f"mini-{p['slug']}-m-{name}.svg", mini_m(p, t))
        for pl in PLATES:
            write(OUT / f"plate-{pl['slug']}-{name}.svg", plate(pl, t))
            write(OUT / f"plate-{pl['slug']}-m-{name}.svg", plate_m(pl, t))
        for r in REPOS:
            p = dict(by_slug[r.get("fig") or r["mini"]])
            p["tags"] = r.get("tags") or p["tags"]
            header = (f"kipung / {r['repo']}", p["meta"])
            write(REPO_OUT / r["repo"] / ".github" / f"banner-{name}.svg", card(p, None, False, t, header=header))
            write(REPO_OUT / r["repo"] / ".github" / f"banner-m-{name}.svg", card_m(p, None, t, header=header))
    write(ROOT / "README.md", readme())
    print("wrote", len(list(OUT.glob("*.svg"))), "profile SVGs and", len(REPOS) * 2, "repo banners")
