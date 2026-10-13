"""Static site builder for the portfolio.

Reads one JSON file per project from content/projects/, then regenerates:
  - the project cards on the home page (between the <!-- projects:start/end --> markers)
  - projects/index.html            (all projects)
  - projects/<slug>/index.html     (one case study per project)

Standard library only. Run:  python build.py
See README.md for how to add a project.
"""

from __future__ import annotations

import html
import json
import logging
import re
import struct
from dataclasses import dataclass
from datetime import date
from pathlib import Path

logger = logging.getLogger("portfolio.build")

ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content" / "projects"
ASSETS_DIR = ROOT / "assets" / "projects"
OUTPUT_DIR = ROOT / "projects"
HOME = ROOT / "index.html"

SITE_NAME = "Alen Frashnishta"
CSP = (
    "default-src 'none'; style-src 'self'; img-src 'self' data:; "
    "base-uri 'none'; form-action 'none'"
)
START_MARK = "<!-- projects:start -->"
END_MARK = "<!-- projects:end -->"


@dataclass(frozen=True)
class Screenshot:
    file: str
    alt: str
    caption: str
    width: int | None
    height: int | None


@dataclass(frozen=True)
class Link:
    label: str
    url: str


COVERAGE_STATUS = {
    "verified": "Verified on live traffic",
    "unverified": "Written, not yet verified",
    "unsupported": "Not supported yet",
}


@dataclass(frozen=True)
class CoverageRow:
    """One line of an honest 'what works' table (optional per project)."""

    service: str
    where: str
    status: str  # key of COVERAGE_STATUS
    note: str


@dataclass(frozen=True)
class Project:
    slug: str
    title: str
    tagline: str
    status: str
    year: str
    order: int
    summary: str
    problem: str
    approach: list[str]
    highlights: list[str]
    stack: list[str]
    next_steps: list[str]
    links: list[Link]
    screenshots: list[Screenshot]
    coverage: list[CoverageRow]


# ---------------------------------------------------------------- loading


def _png_size(path: Path) -> tuple[int, int] | None:
    """Return (width, height) for a PNG, or None if it isn't one."""
    with path.open("rb") as fh:
        header = fh.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def _load_screenshot(slug: str, raw: dict) -> Screenshot:
    path = ASSETS_DIR / slug / raw["file"]
    if not path.is_file():
        raise FileNotFoundError(f"[{slug}] screenshot not found: {path}")
    size = _png_size(path)
    width = size[0] if size else raw.get("width")
    height = size[1] if size else raw.get("height")
    return Screenshot(raw["file"], raw["alt"], raw["caption"], width, height)


def _load_link(slug: str, raw: dict) -> Link:
    if not raw["url"].startswith("https://"):
        raise ValueError(f"[{slug}] link must be https: {raw['url']}")
    return Link(raw["label"], raw["url"])


def _load_coverage(slug: str, raw: dict) -> CoverageRow:
    if raw["status"] not in COVERAGE_STATUS:
        raise ValueError(f"[{slug}] coverage status must be one of {sorted(COVERAGE_STATUS)}: {raw['status']}")
    return CoverageRow(raw["service"], raw["where"], raw["status"], raw["note"])


def load_projects() -> list[Project]:
    """Load and validate every project JSON file, sorted by its `order`."""
    projects: list[Project] = []
    for path in sorted(CONTENT_DIR.glob("*.json")):
        slug = path.stem
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            raise ValueError(f"Project file name must be lowercase-with-dashes: {path.name}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        projects.append(
            Project(
                slug=slug,
                title=raw["title"],
                tagline=raw["tagline"],
                status=raw["status"],
                year=str(raw["year"]),
                order=int(raw.get("order", 100)),
                summary=raw["summary"],
                problem=raw["problem"],
                approach=list(raw["approach"]),
                highlights=list(raw["highlights"]),
                stack=list(raw["stack"]),
                next_steps=list(raw["next"]),
                links=[_load_link(slug, link) for link in raw["links"]],
                screenshots=[_load_screenshot(slug, s) for s in raw["screenshots"]],
                coverage=[_load_coverage(slug, c) for c in raw.get("coverage", [])],
            )
        )
    projects.sort(key=lambda p: (p.order, p.title))
    logger.info("Loaded %d project(s)", len(projects))
    return projects


# -------------------------------------------------------------- rendering


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def asset_url(prefix: str, project: Project, shot: Screenshot) -> str:
    return f"{prefix}assets/projects/{project.slug}/{shot.file}"


def render_img(prefix: str, project: Project, shot: Screenshot, *, eager: bool = False) -> str:
    dims = f' width="{shot.width}" height="{shot.height}"' if shot.width and shot.height else ""
    loading = "" if eager else ' loading="lazy"'
    return f'<img src="{esc(asset_url(prefix, project, shot))}" alt="{esc(shot.alt)}"{dims}{loading}>'


def render_tags(items: list[str]) -> str:
    return '<p class="tags">' + "".join(f"<span>{esc(i)}</span>" for i in items) + "</p>"


def page(title: str, description: str, prefix: str, body: str) -> str:
    """Wrap page body in the shared head, nav and footer. `prefix` climbs back to the site root."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="{esc(CSP)}">
  <meta name="referrer" content="no-referrer">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{prefix}styles.css">
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <header class="top">
    <nav class="wrap nav" aria-label="Primary">
      <a class="brand" href="{prefix}index.html">AF</a>
      <ul>
        <li><a href="{prefix}index.html">Home</a></li>
        <li><a href="{prefix}projects/index.html">Projects</a></li>
        <li><a href="{prefix}index.html#contact">Contact</a></li>
      </ul>
    </nav>
  </header>
  <main id="main">
{body}
  </main>
  <footer class="wrap foot">
    <p>© {date.today().year} {esc(SITE_NAME)}</p>
  </footer>
</body>
</html>
"""


def render_card(project: Project, prefix: str) -> str:
    """Project card used on the home page and the projects index."""
    href = f"{prefix}projects/{project.slug}/index.html"
    thumb = ""
    if project.screenshots:
        thumb = (
            f'<a class="card-thumb" href="{href}" tabindex="-1" aria-hidden="true">'
            f"{render_img(prefix, project, project.screenshots[0])}</a>"
        )
    return f"""<article class="card">
          {thumb}
          <p class="status">{esc(project.status)} · {esc(project.year)}</p>
          <h3><a href="{href}">{esc(project.title)}</a></h3>
          <p>{esc(project.summary)}</p>
          {render_tags(project.stack)}
          <a class="more" href="{href}">Read the case study →</a>
        </article>"""


def render_gallery(project: Project, prefix: str) -> str:
    figures = []
    for shot in project.screenshots:
        wide = not (shot.width and shot.height and shot.height > shot.width)
        css = "shot wide" if wide else "shot"
        figures.append(
            f'<figure class="{css}">{render_img(prefix, project, shot)}'
            f"<figcaption>{esc(shot.caption)}</figcaption></figure>"
        )
    return '<div class="gallery">' + "".join(figures) + "</div>"


def render_coverage(project: Project) -> str:
    """Optional 'Coverage' section: an honest table of what is and isn't verified."""
    if not project.coverage:
        return ""
    rows = "".join(
        f"<tr><th scope=\"row\">{esc(c.service)}</th><td>{esc(c.where)}</td>"
        f"<td><span class=\"cov cov--{c.status}\">{esc(COVERAGE_STATUS[c.status])}</span></td>"
        f"<td>{esc(c.note)}</td></tr>"
        for c in project.coverage
    )
    return f"""      <section>
        <h2>Coverage</h2>
        <p>What has been tested against real traffic, and what hasn't.</p>
        <div class="table-scroll"><table class="coverage">
          <thead><tr><th scope="col">Service</th><th scope="col">Where</th><th scope="col">Status</th><th scope="col">Notes</th></tr></thead>
          <tbody>{rows}</tbody>
        </table></div>
      </section>
"""


def render_project_page(project: Project) -> str:
    prefix = "../../"
    links = "".join(
        f'<a class="btn primary" href="{esc(link.url)}" rel="noopener noreferrer">{esc(link.label)}</a>'
        for link in project.links
    )
    approach = "".join(f"<p>{esc(p)}</p>" for p in project.approach)
    highlights = "".join(f"<li>{esc(h)}</li>" for h in project.highlights)
    next_steps = "".join(f"<li>{esc(n)}</li>" for n in project.next_steps)
    body = f"""    <article class="wrap project">
      <p class="crumbs"><a href="{prefix}projects/index.html">Projects</a> / {esc(project.title)}</p>
      <header class="pagehead">
        <h1>{esc(project.title)}</h1>
        <p class="lead">{esc(project.tagline)}</p>
        <p class="status">{esc(project.status)} · {esc(project.year)}</p>
        {render_tags(project.stack)}
        <p class="cta">{links}</p>
      </header>
      <section>
        <h2>Overview</h2>
        <p>{esc(project.summary)}</p>
      </section>
      <section>
        <h2>Screenshots</h2>
        {render_gallery(project, prefix)}
      </section>
      <section>
        <h2>The problem</h2>
        <p>{esc(project.problem)}</p>
      </section>
      <section>
        <h2>How it works</h2>
        {approach}
      </section>
{render_coverage(project)}      <section>
        <h2>Highlights</h2>
        <ul class="bullets">{highlights}</ul>
      </section>
      <section>
        <h2>What's next</h2>
        <ul class="bullets">{next_steps}</ul>
      </section>
    </article>"""
    return page(f"{project.title} — {SITE_NAME}", project.tagline, prefix, body)


def render_projects_index(projects: list[Project]) -> str:
    prefix = "../"
    cards = "\n        ".join(render_card(p, prefix) for p in projects)
    body = f"""    <section class="wrap pagehead">
      <p class="eyebrow">Projects</p>
      <h1>Things I've built</h1>
      <p class="lead">Security tools and prototypes, with what they do, how they work and where they're headed.</p>
    </section>
    <section class="wrap">
      <div class="cards">
        {cards}
      </div>
    </section>"""
    return page(f"Projects — {SITE_NAME}", "Security tools and prototypes by Alen Frashnishta.", prefix, body)


# ----------------------------------------------------------------- output


def update_home(projects: list[Project]) -> None:
    """Replace the home-page project cards between the build markers."""
    text = HOME.read_text(encoding="utf-8")
    if START_MARK not in text or END_MARK not in text:
        raise RuntimeError("index.html is missing the projects:start / projects:end markers")
    cards = "\n        ".join(render_card(p, "") for p in projects)
    block = (
        f'{START_MARK}\n      <div class="cards">\n        {cards}\n      </div>\n'
        f'      <p class="all"><a href="projects/index.html">See all projects →</a></p>\n      {END_MARK}'
    )
    pattern = re.compile(re.escape(START_MARK) + r".*?" + re.escape(END_MARK), re.DOTALL)
    HOME.write_text(pattern.sub(lambda _m: block, text, count=1), encoding="utf-8", newline="\n")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    logger.info("Wrote %s", path.relative_to(ROOT))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    projects = load_projects()
    update_home(projects)
    write(OUTPUT_DIR / "index.html", render_projects_index(projects))
    for project in projects:
        write(OUTPUT_DIR / project.slug / "index.html", render_project_page(project))
    logger.info("Done.")


if __name__ == "__main__":
    main()
